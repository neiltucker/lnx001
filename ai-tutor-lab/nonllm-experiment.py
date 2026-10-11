#!/usr/bin/env python3
"""Build a model-free, algorithmic AI Tutor experiment from the LNX-001 SCORM source."""
import hashlib
import importlib.util
import json
import html
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
PACKAGE = ROOT / "LNX-001_EN_SCORM2004.zip"
GUIDE = ROOT / "LNX-001_EN_TrainerPreparationGuide.txt"
QRG = ROOT / "Day-01-QuickReference.html"
OUT = ROOT / "LNX-001_EN_SCORM2004_AI-TUTOR-LAB-NONLLM-V1.zip"
WORK = Path("/tmp/lnx001-ai-tutor-lab/nonllm")
LAB = ROOT / "ai-tutor-lab"

spec = importlib.util.spec_from_file_location("cs_knowledge_builder", LAB / "build_experiment.py")
builder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = builder
spec.loader.exec_module(builder)

QUIZ_HINT = re.compile(r"quiz|knowledge check|check your understanding|test your understanding|test your knowledge|select the best answer|end.of.module|module assessment|review questions|multiple.choice|question\s+\d+\s+of\s+\d+", re.I)
QUESTION_START = re.compile(r"^(?:question\s*\d{1,2}\s*[:.)-]?\s*)?(?:what|why|how|which|where|when|who|whom|whose|select|choose|identify|name|list|compare|explain|true or false|is it true|does|do|can|should|would|will|in which|under what)\b", re.I)
EXPLICIT_ANSWER = re.compile(r"(?i)\b(?:correct answer|correct option|the answer is|answer key)\s*[:\-]\s*([^.;\r\n]{2,240})")
EXPLICIT_EXPLANATION = re.compile(r"(?i)\b(?:explanation|feedback|why this is correct)\s*[:\-]\s*([^.\r\n]{15,400})")

def read_html_blocks(raw):
    parser = builder.Visible()
    parser.feed(raw)
    parser.close()
    text = " ".join(t for _, t in parser.blocks)
    return parser, re.sub(r"\s+", " ", text).strip()

def infer_intent(question):
    q = question.lower().strip()
    if re.search(r"\b(compare|comparison|difference|different from|versus|vs\.?)\b", q): return "compare"
    if re.match(r"^(why|what is the reason|for what reason)\b", q): return "why"
    if re.match(r"^(how|what steps|what is the process)\b", q): return "how"
    if re.search(r"\b(troubleshoot|fix|resolve|debug|error|not working)\b", q): return "troubleshoot"
    if re.search(r"\b(example|sample|demonstrate)\b", q): return "example"
    if re.search(r"\b(command|configuration file|config file|file path|directive|ip address|which file|which setting|which option|which port)\b", q): return "identify"
    if re.match(r"^where\b", q): return "where"
    if re.match(r"^when\b", q): return "when"
    if re.match(r"^(list|name)\b", q) or "what fields" in q: return "list"
    if re.match(r"^(what|which|who|define|identify)\b", q): return "explain"
    if re.match(r"^(select|choose|true or false)\b", q): return "identify"
    return "explain"

def make_question_rules(questions):
    counts = Counter()
    stems = {}
    for question in questions:
        q = re.sub(r"\s+", " ", str(question)).strip()
        if not q: continue
        intent = infer_intent(q)
        counts[intent] += 1
        words = q.lower().split()
        # Keep question-type forms such as "which command" or "choose the correct";
        # omit longer wording that would overfit a single assessment item.
        prefix = " ".join(words[:min(3, len(words))])
        if len(prefix) > 4:
            key = (intent, prefix)
            stems[key] = stems.get(key, 0) + 1
    return {
        "question_counts_by_intent": dict(sorted(counts.items())),
        "question_stems": [
            {"intent": k[0], "prefix": k[1], "count": n}
            for k, n in sorted(stems.items(), key=lambda x: (-x[1], x[0][0], x[0][1]))
        ][:160],
        "intent_templates": {
            "why": "State the course-supported reason, then the result or risk it explains.",
            "how": "Give a concise action-oriented explanation; retain source order and exact commands.",
            "compare": "State only distinctions explicitly supported by indexed evidence.",
            "identify": "Return the exact name, path, setting, value, or command when available.",
            "troubleshoot": "Present the relevant validation/check first, then the supported correction.",
            "explain": "Give the key fact first, followed by one supporting detail if useful."
        }
    }

def extract_quiz_prompts(raw, path):
    parser, visible = read_html_blocks(raw)
    if not visible:
        return {"is_quiz": False, "items": [], "title": ""}

    # The packaged learner quiz exposes the correct option and explanation after
    # submission. Extract only that answer and explanation; never index distractors.
    def json_array_after(var_name):
        m = re.search(r'window\.' + re.escape(var_name) + r'\s*=\s*(\[.*?\])\s*;', raw, re.S)
        if not m:
            return []
        try:
            value = json.loads(m.group(1))
            return value if isinstance(value, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    answer_letters = json_array_after("__quizAnswers")
    explanations = json_array_after("__quizExplanations")
    candidates = []
    fieldset_pattern = re.compile(
        r'<fieldset\b(?=[^>]*\bclass\s*=\s*"[^"]*\bquiz-question\b[^"]*")[^>]*>(.*?)</fieldset>',
        re.I | re.S
    )
    for idx, fm in enumerate(fieldset_pattern.finditer(raw)):
        block = fm.group(1)
        qm = re.search(r'<span\b(?=[^>]*\bclass\s*=\s*"[^"]*\bquestion-text\b[^"]*")[^>]*>(.*?)</span>', block, re.I | re.S)
        if not qm:
            continue
        question = html.unescape(re.sub(r"<[^>]+>", " ", qm.group(1)))
        question = re.sub(r"\s+", " ", question).strip()
        if len(question) < 14 or len(question) > 320 or not QUESTION_START.search(question):
            continue
        option_map = {}
        for om in re.finditer(r'<span\b(?=[^>]*\bclass\s*=\s*"[^"]*\boption-text\b[^"]*")[^>]*>(.*?)</span>', block, re.I | re.S):
            option = html.unescape(re.sub(r"<[^>]+>", " ", om.group(1))).strip()
            option = re.sub(r"\s+", " ", option)
            option_match = re.match(r"([A-D])\s*[).]\s*(.*)", option)
            if option_match:
                option_map[option_match.group(1).upper()] = option_match.group(2).strip()
        answer_letter = str(answer_letters[idx]).strip().upper() if idx < len(answer_letters) else ""
        correct_option = option_map.get(answer_letter, "")
        explanation = html.unescape(str(explanations[idx])).strip() if idx < len(explanations) else ""
        if correct_option and answer_letter in "ABCD":
            # The learner gets this feedback from the quiz after submitting an answer.
            answer = "Correct answer: " + answer_letter + ") " + correct_option
            if explanation:
                answer += ". Explanation: " + explanation
        else:
            answer = ""
        key = re.sub(r"[^a-z0-9]+", " ", question.lower()).strip()
        if key and key not in {x["key"] for x in candidates}:
            candidates.append({
                "question": question, "key": key,
                "block_index": idx, "answer": answer
            })

    # Fallback: keep question wording if the source uses a different quiz markup.
    if not candidates:
        for bi, (tag, text) in enumerate(parser.blocks):
            parts = re.split(r"(?<=[?])\s+(?=[A-Z0-9])|(?<=[.!])\s+(?=(?:What|Why|How|Which|Where|When|Who|Select|Choose|Identify|Compare|Explain)\b)", text)
            for part in parts:
                question = re.sub(r"^\s*(?:Question\s*\d{1,2}\s*[:.)-]?\s*)", "", part, flags=re.I).strip()
                question = re.sub(r"\s+", " ", question).strip(" \t\r\n•-")
                if len(question) < 14 or len(question) > 320 or "?" not in question or not QUESTION_START.search(question):
                    continue
                key = re.sub(r"[^a-z0-9]+", " ", question.lower()).strip()
                if key and key not in {x["key"] for x in candidates}:
                    candidates.append({"question": question, "key": key, "block_index": bi, "answer": ""})

    hinted = bool(QUIZ_HINT.search(path + " " + parser.title + " " + visible))
    if not candidates or not (hinted or len(candidates) >= 3):
        return {"is_quiz": False, "items": [], "title": parser.title}
    for item in candidates:
        item.pop("key", None)
    return {
        "is_quiz": True, "items": candidates, "title": parser.title,
        "visible_chars": len(visible),
        "question_count": len(candidates),
        "answer_count": sum(1 for item in candidates if item.get("answer"))
    }


def remove_div_with_class(raw, class_name):
    """Remove one matching DIV and nested DIVs, keeping lesson material intact."""
    pattern = re.compile(
        r'<div\b(?=[^>]*\bclass\s*=\s*"[^"]*\b' + re.escape(class_name) + r'\b[^"]*")[^>]*>',
        re.I
    )
    out = []
    cursor = 0
    token_re = re.compile(r'</?div\b[^>]*>', re.I)
    while True:
        match = pattern.search(raw, cursor)
        if not match:
            out.append(raw[cursor:])
            break
        out.append(raw[cursor:match.start()])
        depth = 1
        end_at = None
        for token in token_re.finditer(raw, match.end()):
            if token.group(0).startswith("</"):
                depth -= 1
                if depth == 0:
                    end_at = token.end()
                    break
            elif not token.group(0).rstrip().endswith("/>"):
                depth += 1
        if end_at is None:
            out.append(raw[match.start():])
            break
        cursor = end_at
    return "".join(out)

def attach_question_anchor(concepts, question, citation, threshold=0.16):
    qterms = builder.toks(question)
    if not qterms:
        return None, 0
    best, best_score = None, 0.0
    for rec in concepts:
        text = " ".join([
            str(rec.get("title", "")), str(rec.get("section_title", "")), str(rec.get("direct_answer", "")),
            " ".join(rec.get("keywords") or []), " ".join(rec.get("query_anchors") or [])
        ])
        terms = builder.toks(text)
        score = len(qterms & terms) / max(1, len(qterms))
        # Slight preference for a record already scoped to a module and lesson.
        if rec.get("lesson_title"): score += 0.015
        if score > best_score:
            best, best_score = rec, score
    if best and best_score >= threshold:
        anchors = best.setdefault("query_anchors", [])
        if question not in anchors:
            anchors.append(question)
        refs = best.setdefault("source_references", [])
        if citation not in refs:
            refs.append(citation)
        kws = best.setdefault("keywords", [])
        for term in qterms:
            if term not in [str(x).lower() for x in kws] and len(kws) < 120:
                kws.append(term)
        return best, best_score
    return None, best_score

def assessment_to_record(q, bundle, seq):
    mod = builder.module_guess(q["question"] + " " + q["answer"], q["kind"], bundle)
    titles = bundle.get("module_titles") or {}
    mtitle = str(titles.get(str(mod), titles.get(mod, "Module " + str(mod))))
    return builder.make_record(
        "lab_assessment_" + q["kind"] + "_" + str(q["n"]).zfill(2) + "_" + str(seq),
        q["question"], q["answer"], mod, mtitle, q["citation"], "assessment"
    )

def main():
    for file in (PACKAGE, GUIDE, QRG, LAB / "nonllm-tutor.js", LAB / "nonllm-demo.html"):
        if not file.exists():
            raise FileNotFoundError("Required source file not found: " + str(file))
    source_sha = hashlib.sha256(PACKAGE.read_bytes()).hexdigest()
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "baseline").mkdir(exist_ok=True)

    guide = GUIDE.read_text(encoding="utf-8", errors="replace")
    assessment_qas = builder.assessment_records(guide)
    quiz_items, quiz_sources, skipped_quiz_sources = [], [], []
    with zipfile.ZipFile(PACKAGE, "r") as zin:
        bad = zin.testzip()
        if bad: raise ValueError("Source SCORM ZIP integrity failure: " + bad)
        names = zin.namelist()
        tutor_path = next((n for n in names if n.lower().endswith("ai-tutor/tutor.js")), None)
        data_path = next((n for n in names if n.lower().endswith("ai-tutor/tutor-data.js")), None)
        if not tutor_path or not data_path:
            raise ValueError("Source SCORM missing ai-tutor/tutor.js or tutor-data.js")
        tutor_js = zin.read(tutor_path).decode("utf-8", errors="replace")
        old_data_js = zin.read(data_path).decode("utf-8", errors="replace")
        bundle = builder.parse_bundle(old_data_js)
        concepts = bundle.get("concepts") if isinstance(bundle.get("concepts"), list) else []
        if not concepts:
            for i, pair in enumerate(bundle.get("pairs") or [], 1):
                concepts.append(builder.make_record(
                    "base_pair_" + str(i), pair.get("question", "Question " + str(i)), pair.get("answer", ""),
                    int(pair.get("module_number", 1)),
                    str((bundle.get("module_titles") or {}).get(str(pair.get("module_number", 1)), "Module")),
                    pair.get("source_lesson", "Existing tutor Q&A"), "base"
                ))
        if not concepts:
            raise ValueError("Source tutor data contains no concepts")
        base_count = len(concepts)
        bundle["concepts"] = concepts
        title_map = bundle.get("module_titles") or {}
        seen_titles = {builder.norm(str(x.get("title", ""))) for x in concepts}
        assessment_added, assessment_enriched = 0, 0

        for q in assessment_qas:
            best, best_score = attach_question_anchor(concepts, q["question"], q["citation"], threshold=0.55)
            if best and best_score >= 0.55:
                old = str(best.get("direct_answer", "")).strip()
                if builder.norm(q["answer"]) not in builder.norm(old):
                    best["direct_answer"] = (old + "\n\nAssessment explanation: " + q["answer"]).strip()[:4200]
                source_refs = best.setdefault("source_references", [])
                if q["citation"] not in source_refs: source_refs.append(q["citation"])
                assessment_enriched += 1
            elif builder.norm(q["question"]) not in seen_titles:
                concepts.append(assessment_to_record(q, bundle, len(concepts) + 1))
                seen_titles.add(builder.norm(q["question"]))
                assessment_added += 1

        qrg_added, course_added = [], []
        qrg_parser, qrg_visible = read_html_blocks(QRG.read_text(encoding="utf-8", errors="replace"))
        for heading, body in builder.html_sections(QRG.read_text(encoding="utf-8", errors="replace"), QRG.name)[0]:
            key = builder.norm(heading + " " + body)
            if len(key) < 100 or key in seen_titles: continue
            mod = builder.module_guess(heading + " " + body[:300], QRG.name, bundle)
            mtitle = str(title_map.get(str(mod), title_map.get(mod, "Module " + str(mod))))
            rec = builder.make_record("lab_qrg_" + str(len(qrg_added) + 1).zfill(4), heading, body, mod, mtitle, "Quick Reference Guide — " + QRG.name + " — " + heading, "qrg")
            rec["knowledge_source_type"] = "quick_reference"
            concepts.append(rec); qrg_added.append(rec); seen_titles.add(key)

        html_sources, processed_paths, course_added_count = [], [], 0
        for name in names:
            low = name.lower()
            if low.startswith("ai-tutor/") or "/ai-tutor/" in low or not low.endswith((".html", ".htm", ".xhtml")):
                continue
            raw = zin.read(name).decode("utf-8", errors="replace")
            parser, visible = read_html_blocks(raw)
            if len(visible) < 160: continue
            html_sources.append({"path": name, "visible_chars": len(visible), "title": parser.title or Path(name).name})
            quiz = extract_quiz_prompts(raw, name + " " + parser.title)
            content_raw = raw
            if quiz["is_quiz"]:
                quiz_sources.append({"path": name, "title": quiz.get("title", ""), "question_count": len(quiz["items"]), "visible_chars": quiz.get("visible_chars", len(visible))})
                for qi, item in enumerate(quiz["items"], 1):
                    citation = "SCORM end-of-module quiz — " + name + ((" — " + quiz["title"]) if quiz.get("title") else "") + " — question " + str(qi)
                    quiz_item = {"question": item["question"], "answer": item["answer"], "citation": citation, "source": name, "number": qi}
                    quiz_items.append(quiz_item)
                # Keep the lesson content in the module HTML, but strip only its quiz UI
                # so choices/distractors cannot leak into content records.
                content_raw = remove_div_with_class(raw, "screen-quiz")
                skipped_quiz_sources.append(name + " (quiz panel only)")
            for heading, body in builder.html_sections(content_raw, name)[0]:
                key = builder.norm(heading + " " + body)
                if len(key) < 100 or key in seen_titles: continue
                mod = builder.module_guess(heading + " " + body[:300], name, bundle)
                mtitle = str(title_map.get(str(mod), title_map.get(mod, "Module " + str(mod))))
                rec = builder.make_record("lab_course_" + str(course_added_count + 1).zfill(4), heading, body, mod, mtitle, "SCORM course content — " + name + " — " + heading, "course")
                rec["knowledge_source_type"] = "course_content"
                concepts.append(rec); course_added.append(rec); seen_titles.add(key); course_added_count += 1
            processed_paths.append(name)

        quiz_answer_records = 0
        quiz_questions_anchored = 0
        quiz_unlinked = 0
        for item in quiz_items:
            if item["answer"]:
                mod = builder.module_guess(item["question"] + " " + item["answer"], item["source"], bundle)
                mtitle = str(title_map.get(str(mod), title_map.get(mod, "Module " + str(mod))))
                rec = builder.make_record(
                    "lab_module_quiz_" + str(quiz_answer_records + 1).zfill(3), item["question"],
                    item["answer"], mod, mtitle, item["citation"], "assessment"
                )
                rec["knowledge_source_type"] = "learner_quiz_answer"
                concepts.append(rec)
                quiz_answer_records += 1
            else:
                rec, score = attach_question_anchor(concepts, item["question"], item["citation"])
                if rec: quiz_questions_anchored += 1
                else: quiz_unlinked += 1

        # Retain all pre/post assessment question wording as retrieval anchors and use
        # their answer keys/explanations as trusted evidence; do not index other trainer-guide sections.
        all_question_texts = [x["question"] for x in assessment_qas] + [x["question"] for x in quiz_items]
        rules = make_question_rules(all_question_texts)
        rules.update({
            "version": "non-llm-generation-rules-v1",
            "training_sources": {
                "pre_assessment_answer_key_questions": sum(x["kind"] == "pre" for x in assessment_qas),
                "post_assessment_answer_key_questions": sum(x["kind"] == "post" for x in assessment_qas),
                "learner_end_module_quiz_questions": len(quiz_items),
                "quiz_items_with_explicit_answer_or_feedback": quiz_answer_records
            },
            "runtime_policy": "No model, no hosted service, no network dependency. Retrieval uses BM25-style weighted lexical scores, exact-term boosts, course-specific aliases and question anchors. Answer generation uses intent rules, targeted fact extraction, sentence selection and deterministic templates.",
            "source_policy": "Learner-facing SCORM lesson HTML and Quick Reference Guide HTML; only pre/post instructor answer-key Q&A from the Trainer Preparation Guide; plus module quiz questions and the single correct option/explanation shown as learner feedback after submission. Quiz distractors and unrelated instructor-only material are excluded."
        })
        bundle["concepts"] = concepts
        bundle["non_llm_generation_rules"] = rules
        bundle["ai_tutor_lab_experiment"] = {
            "version": "non-llm-algorithmic-poc-v1",
            "knowledge_sources": ["existing tutor Q&A", "learner-facing SCORM course HTML", "Quick Reference Guide HTML", "pre/post instructor answer-key Q&A", "learner-facing end-of-module quiz question forms, correct options, and explanations shown as feedback"],
            "runtime": "pure JavaScript algorithms; no LLM, no embeddings model, no WebAssembly, no runtime network calls",
            "primary_tutor_ui_modified": False,
            "separate_demo": "ai-tutor/nonllm-demo.html"
        }
        new_data_js = "window.__CS_AI_TUTOR_DATA__ = " + json.dumps(bundle, ensure_ascii=False, separators=(",", ":")) + ";\n"
        # Store baseline assets for a same-run comparator; source ZIP itself is never modified.
        (WORK / "baseline" / "tutor.js").write_text(tutor_js, encoding="utf-8")
        (WORK / "baseline" / "tutor-data.js").write_text(old_data_js, encoding="utf-8")
        (LAB / "nonllm-index.json").write_text(json.dumps({"concepts": concepts, "generation_rules": rules}, ensure_ascii=False), encoding="utf-8")

        tutor_dir = data_path.rsplit("/", 1)[0] + "/"
        demo_source = (LAB / "nonllm-demo.html").read_text(encoding="utf-8")
        engine_source = (LAB / "nonllm-tutor.js").read_text(encoding="utf-8")
        with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zout:
            for entry in zin.infolist():
                if entry.filename == data_path:
                    payload = new_data_js.encode("utf-8")
                else:
                    payload = zin.read(entry.filename)
                zout.writestr(entry, payload)
            for name, payload in [
                (tutor_dir + "nonllm-tutor.js", engine_source.encode("utf-8")),
                (tutor_dir + "nonllm-demo.html", demo_source.encode("utf-8"))
            ]:
                info = zipfile.ZipInfo(name)
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(info, payload)

        with zipfile.ZipFile(OUT, "r") as check:
            bad = check.testzip()
            if bad: raise ValueError("Candidate SCORM ZIP integrity failure: " + bad)
            output_names = check.namelist()
            if tutor_dir + "nonllm-tutor.js" not in output_names or tutor_dir + "nonllm-demo.html" not in output_names:
                raise ValueError("Candidate SCORM missing non-LLM demo assets")

    if hashlib.sha256(PACKAGE.read_bytes()).hexdigest() != source_sha:
        raise ValueError("Original source package hash changed unexpectedly")

    summary = {
        "experiment": "non-llm-algorithmic-poc-v1",
        "source_package": PACKAGE.name,
        "source_package_sha256": source_sha,
        "source_package_bytes": PACKAGE.stat().st_size,
        "candidate_package": OUT.name,
        "candidate_package_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "candidate_package_bytes": OUT.stat().st_size,
        "extra_model_bytes": 0,
        "runtime_model_count": 0,
        "webassembly_added": False,
        "runtime_network_calls_added": False,
        "primary_tutor_ui_changed": False,
        "candidate_has_separate_model_free_demo": True,
        "base_concept_count": base_count,
        "candidate_concept_count": len(concepts),
        "assessment_qas": {"pre": sum(x["kind"] == "pre" for x in assessment_qas), "post": sum(x["kind"] == "post" for x in assessment_qas)},
        "assessment_concepts_added": assessment_added,
        "existing_concepts_enriched_from_assessments": assessment_enriched,
        "quick_reference_concepts_added": len(qrg_added),
        "course_html_concepts_added": course_added_count,
        "learner_html_sources_indexed": len(processed_paths),
        "learner_html_sources_seen": len(html_sources),
        "module_quiz_sources_detected": len(quiz_sources),
        "module_quiz_questions_detected": len(quiz_items),
        "module_quiz_questions_with_explicit_answers": quiz_answer_records,
        "module_quiz_questions_linked_as_query_anchors": quiz_questions_anchored,
        "module_quiz_questions_not_linked": quiz_unlinked,
        "quiz_pages_excluded_from_raw_content_to_avoid_distractor_leakage": skipped_quiz_sources,
        "generation_rule_question_counts_by_intent": rules["question_counts_by_intent"],
        "question_stem_rules": len(rules["question_stems"]),
        "quiz_sources": quiz_sources,
        "index_bytes": len(json.dumps({"concepts": concepts, "generation_rules": rules}, ensure_ascii=False).encode("utf-8")),
        "source_policy": rules["source_policy"],
        "candidate_demo_path_in_zip": tutor_dir + "nonllm-demo.html"
    }
    (LAB / "nonllm-build-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
