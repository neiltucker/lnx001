#!/usr/bin/env python3
"""Enrich the LNX-001 no-LLM candidate with complete block coverage and a curriculum graph."""
import hashlib, html, importlib.util, json, math, os, re, shutil, subprocess, sys, tempfile, zipfile
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path.cwd()
LAB = ROOT / "ai-tutor-lab"
PACKAGE = ROOT / "LNX-001_EN_SCORM2004.zip"
CANDIDATE_V1 = ROOT / "LNX-001_EN_SCORM2004_AI-TUTOR-LAB-NONLLM-V1.zip"
CANDIDATE_V2 = ROOT / "LNX-001_EN_SCORM2004_AI-TUTOR-LAB-NONLLM-V2-CURRICULUM.zip"
GUIDE = ROOT / "LNX-001_EN_TrainerPreparationGuide.txt"
GUIDE_PDF = ROOT / "LNX-001_EN_TrainerPreparationGuide.pdf"
QRG = ROOT / "Day-01-QuickReference.html"
QRG_PDF = ROOT / "Day-01-QuickReference.pdf"
QRG_ZIP = ROOT / "LNX-001_EN_QuickReference.zip"
IMG_DATA = LAB / "curriculum-image-content.json"
IDX = LAB / "nonllm-index.json"
SUMMARY = LAB / "curriculum-build-summary.json"
AUDIT = LAB / "source-coverage-audit.json"
WORK = Path("/tmp/lnx001-ai-tutor-lab/nonllm")
spec = importlib.util.spec_from_file_location("nonllm_experiment", LAB / "nonllm-experiment.py")
exp = importlib.util.module_from_spec(spec); sys.modules[spec.name] = exp; spec.loader.exec_module(exp)
builder = exp.builder
MODULE_TITLES = {
    0: "Course Orientation: Welcome & Overview",
    1: "Linux CLI Foundations and Filesystem Navigation",
    2: "User, Group, and Permission Administration",
    3: "Hardware Detection, Storage, and Process Management",
    4: "Host Networking and Baseline System Security"
}
META_HEADINGS = re.compile(r"^(?:learning objectives(?:\s*[—–-]\s*review)?|course learning objectives|module summary|module complete!?|knowledge check|curriculum roadmap|key takeaways|procedures|troubleshooting|orientation complete|ready to begin|course complete!?|course vision\s*&\s*structure|target audience|intended audience|prerequisites|environment\s*&\s*tooling readiness|hands-on environment\s*&\s*tooling|learning strategies|best practices|readiness checklist)$", re.I)
UI_ONLY = re.compile(r"^(?:skip to course content|course home|click next(?:\s*[→›>])?|previous|next|module complete!?|you have completed all sections of this module\.?|return to course directory|course complete!?|[\d.]+\s*%\s*complete|resume course|back to top)$", re.I)

def norm(s):
    return builder.norm(str(s or ""))

def terms(s):
    return set(builder.toks(str(s or "")))

def similarity(a, b):
    aa, bb = terms(a), terms(b)
    if not aa or not bb: return 0.0
    return len(aa & bb) / math.sqrt(len(aa) * len(bb))

def sparse_vector(s):
    ts = builder.toks(str(s or ""))
    if not ts: return {}
    weight = 1.0 / math.sqrt(len(ts))
    return {t: round(weight, 5) for t in sorted(ts)}

class CurriculumHTML(HTMLParser):
    """Keep inline code within surrounding sentences and retain block-level boundaries."""
    skip = {"script", "style", "noscript", "svg", "nav", "footer", "button", "head", "template"}
    heads = {"h1", "h2", "h3", "h4", "h5", "h6"}
    block_tags = {"p", "li", "pre", "blockquote", "figcaption", "summary", "dt", "dd", "tr"}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skipped = []
        self.current_tag = None
        self.buffer = []
        self.blocks_out = []
        self.title = ""
        self.image_alts = []
    def flush(self):
        value = re.sub(r"\s+", " ", html.unescape(" ".join(self.buffer))).strip()
        if value:
            if self.current_tag == "title": self.title = value
            else: self.blocks_out.append((self.current_tag or "p", value))
        self.buffer = []
        self.current_tag = None
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs = dict(attrs)
        if self.skipped:
            if tag in self.skip: self.skipped.append(tag)
            return
        if tag in self.skip:
            self.flush()
            self.skipped.append(tag)
            return
        if tag in self.heads or tag in self.block_tags or tag == "title":
            self.flush()
            self.current_tag = tag
        elif tag == "br":
            self.buffer.append(" ")
        elif tag == "img":
            alt = str(attrs.get("alt") or "").strip()
            src = str(attrs.get("src") or "").split("?")[0]
            if alt:
                self.image_alts.append({"file": Path(src).name, "alt": html.unescape(alt)})
                self.buffer.append(" [Image: " + alt + "] ")
    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.skipped:
            if tag == self.skipped[-1]: self.skipped.pop()
            return
        if tag in self.heads or tag in self.block_tags or tag == "title":
            self.flush()
    def handle_data(self, data):
        if not self.skipped and data.strip():
            if self.current_tag is None: self.current_tag = "p"
            self.buffer.append(data.strip())
    @property
    def blocks(self):
        return self.blocks_out

def parse_html(raw):
    p = CurriculumHTML()
    p.feed(raw); p.close(); p.flush()
    return p

def module_from_path(path):
    m = re.search(r"module[_-]?0?([0-4])\.html", str(path), re.I)
    if m: return int(m.group(1))
    m = re.search(r"m0?([1-4])_", str(path), re.I)
    return int(m.group(1)) if m else None

def module_title(module):
    return MODULE_TITLES.get(module, "Course-wide content" if module is None else "Course Orientation")

def stable_id(prefix, source, idx, text):
    digest = hashlib.sha1((str(source) + "|" + str(idx) + "|" + norm(text)).encode("utf-8")).hexdigest()[:12]
    return prefix + "_" + digest

def title_from_module_blocks(blocks, module):
    if module == 0:
        for tag, text in blocks:
            if tag in ("h1", "h2") and "course orientation" in text.lower():
                return text.strip()
    for tag, text in blocks:
        if tag == "h2" and text.strip().lower() == module_title(module).lower():
            return text.strip()
    return module_title(module)

def extract_explicit_objectives(page_blocks, path, module):
    course_objs, module_objs = [], []
    for i, (tag, text) in enumerate(page_blocks):
        low = norm(text)
        if tag.startswith("h") and re.fullmatch(r"h[1-6]", tag):
            if module == 0 and "course learning objectives" in low:
                for j in range(i + 1, len(page_blocks)):
                    t, v = page_blocks[j]
                    if t.startswith("h") and re.fullmatch(r"h[1-6]", t): break
                    if t == "li" and len(norm(v)) > 8: course_objs.append(v.strip())
            elif module and "learning objectives" in low and "review" not in low:
                found = []
                for j in range(i + 1, len(page_blocks)):
                    t, v = page_blocks[j]
                    if t.startswith("h") and re.fullmatch(r"h[1-6]", t): break
                    if t == "li" and len(norm(v)) > 8: found.append(v.strip())
                if found and not module_objs: module_objs = found
    return course_objs, module_objs

def extract_topics(page_blocks, path, module, cobj_nodes, mobj_nodes, existing_title=None):
    module_topic_nodes, lesson_nodes = [], []
    heading_stack = []
    current_h2 = None
    seen_mod, seen_lesson = set(), set()
    block_context = []
    for idx, (tag, text) in enumerate(page_blocks):
        if not re.fullmatch(r"h[1-6]", tag): continue
        level = int(tag[1])
        while heading_stack and heading_stack[-1]["level"] >= level: heading_stack.pop()
        heading_stack.append({"level": level, "title": text.strip()})
        low = norm(text)
        if level == 2:
            current_h2 = None
            if (META_HEADINGS.match(text.strip()) or low in {"module " + str(module), norm(existing_title or ""), norm(module_title(module))}
                    or re.fullmatch(r"module \d+", low)):
                continue
            key = (module, low)
            if key not in seen_mod:
                n = {"id": stable_id("mt", path, idx, text), "node_type": "module_topic", "title": text.strip(),
                     "statement": text.strip(), "module_number": module, "source_file": path, "heading_level": level,
                     "parent_ids": ["module_" + str(module)], "importance_weight": 0.66, "term_vector": sparse_vector(text)}
                module_topic_nodes.append(n); seen_mod.add(key); current_h2 = n["id"]
            else:
                current_h2 = next((x["id"] for x in module_topic_nodes if (module, norm(x["title"])) == key), None)
        elif level in (3, 4):
            if META_HEADINGS.match(text.strip()) or "learning objectives" in low or "key takeaways" in low or low.startswith("module complete"):
                continue
            key = (module, low)
            if key not in seen_lesson:
                n = {"id": stable_id("lt", path, idx, text), "node_type": "lesson_topic", "title": text.strip(),
                     "statement": text.strip(), "module_number": module, "source_file": path, "heading_level": level,
                     "parent_ids": [current_h2] if current_h2 else ["module_" + str(module)],
                     "importance_weight": 0.48, "term_vector": sparse_vector(text)}
                lesson_nodes.append(n); seen_lesson.add(key)
        block_context.append({"index": idx, "tag": tag, "text": text, "heading_path": [x["title"] for x in heading_stack]})
    return module_topic_nodes, lesson_nodes

def parse_prepost_assessments(guide):
    # Same source-section boundaries as the approved answer-key extraction; the Module Q&A Reference
    # and other instructor-only sections remain excluded under the current source policy.
    text = guide.replace(chr(160), " ").replace("—", "-").replace("–", "-").replace("−", "-").replace(chr(65533), "-")
    a = re.search(r"Pre-Assessment +- +Instructor Answer Key", text, re.I)
    b = re.search(r"Post-Assessment +- +Student Handout", text, re.I)
    c = re.search(r"Post-Assessment +- +Instructor Answer Key", text, re.I)
    if not (a and b and c): raise ValueError("Cannot locate approved pre/post assessment answer-key sections")
    out = []
    for kind, section in (("pre", text[a.end():b.start()]), ("post", text[c.end():])):
        matches = list(re.finditer(r"(?m)^\s*(\d{1,2})\.\s+", section))
        for i, m in enumerate(matches):
            block = section[m.end():matches[i+1].start() if i+1 < len(matches) else len(section)]
            oa = re.search(r"(?m)^\s*A[.)]\s+", block)
            am = re.search(r"(?im)^\s*Answer:\s*([A-D])\s*$", block)
            if not oa or not am or am.start() < oa.start(): continue
            question = re.sub(r"\s+", " ", block[:oa.start()]).strip()
            choice_text = block[oa.start():am.start()]
            choice_matches = list(re.finditer(r"(?m)^\s*([A-D])[.)]\s+", choice_text))
            choices = []
            for j, cm in enumerate(choice_matches):
                end = choice_matches[j+1].start() if j+1 < len(choice_matches) else len(choice_text)
                value = re.sub(r"\s+", " ", choice_text[cm.end():end]).strip(" .\r\n\t")
                if value: choices.append({"key": cm.group(1), "text": value})
            letter = am.group(1).upper()
            correct = next((x["text"] for x in choices if x["key"] == letter), "")
            rationale = re.sub(r"\s+", " ", block[am.end():]).strip()
            if not question or not correct: continue
            citation = "Trainer Preparation Guide — " + ("Pre-Assessment" if kind == "pre" else "Post-Assessment") + " Instructor Answer Key, question " + m.group(1)
            out.append({"id": "assessment_" + kind + "_" + str(int(m.group(1))).zfill(2), "kind": kind, "number": int(m.group(1)),
                        "question": question, "choices": [{"key": x["key"], "text": x["text"], "role": "correct" if x["key"] == letter else "distractor", "is_correct": x["key"] == letter} for x in choices],
                        "correct_option": letter, "correct_answer": correct, "rationale": rationale, "citation": citation,
                        "source_file": GUIDE.name, "module_number": None, "availability": "answer-key content used for tutor knowledge and offline validation"})
    counts = Counter(x["kind"] for x in out)
    if counts != {"pre": 10, "post": 20}: raise ValueError("Expected all 10 pre and 20 post answer-key items; got " + str(dict(counts)))
    return out

def parse_quiz_items(raw, path, module):
    def json_array_after(var_name):
        m = re.search(r"window\." + re.escape(var_name) + r"\s*=\s*(\[.*?\])\s*;", raw, re.S)
        if not m: return []
        try:
            value = json.loads(m.group(1))
            return value if isinstance(value, list) else []
        except (json.JSONDecodeError, TypeError): return []
    letters = json_array_after("__quizAnswers")
    explanations = json_array_after("__quizExplanations")
    pattern = re.compile(r'<fieldset\b(?=[^>]*\bclass\s*=\s*"[^"]*\bquiz-question\b[^"]*")[^>]*>(.*?)</fieldset>', re.I | re.S)
    results = []
    for idx, match in enumerate(pattern.finditer(raw)):
        block = match.group(1)
        qm = re.search(r'<span\b(?=[^>]*\bclass\s*=\s*"[^"]*\bquestion-text\b[^"]*")[^>]*>(.*?)</span>', block, re.I | re.S)
        if not qm: continue
        question = html.unescape(re.sub(r"<[^>]+>", " ", qm.group(1)))
        question = re.sub(r"\s+", " ", question).strip()
        if len(question) < 8: continue
        options = []
        for om in re.finditer(r'<span\b(?=[^>]*\bclass\s*=\s*"[^"]*\boption-text\b[^"]*")[^>]*>(.*?)</span>', block, re.I | re.S):
            val = html.unescape(re.sub(r"<[^>]+>", " ", om.group(1)))
            val = re.sub(r"\s+", " ", val).strip()
            mm = re.match(r"([A-D])\s*[).]\s*(.*)", val)
            if mm: options.append({"key": mm.group(1).upper(), "text": mm.group(2).strip()})
        answer = str(letters[idx]).strip().upper() if idx < len(letters) else ""
        correct = next((x["text"] for x in options if x["key"] == answer), "")
        rationale = html.unescape(str(explanations[idx])).strip() if idx < len(explanations) and explanations[idx] else ""
        if not options: continue
        item_id = "quiz_m" + str(module).zfill(2) + "_" + str(len(results)+1).zfill(2)
        results.append({"id": item_id, "kind": "module_quiz", "number": len(results)+1, "question": question,
                        "choices": [{"key": x["key"], "text": x["text"],
                            "role": ("correct" if x["key"] == answer else "distractor") if answer in "ABCD" else "unknown",
                            "is_correct": (x["key"] == answer) if answer in "ABCD" else None} for x in options],
                        "correct_option": answer if correct else None, "correct_answer": correct, "rationale": rationale,
                        "citation": "SCORM module quiz — " + path + " — question " + str(len(results)+1),
                        "source_file": path, "module_number": module, "availability": "learner-visible question; use answer only where correct option/feedback is explicit"})
    return results

def extract_pdf_text_bytes(data, label):
    if not data: return "", "empty"
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data); temp_path = tmp.name
    try:
        if shutil.which("pdftotext"):
            p = subprocess.run(["pdftotext", "-layout", temp_path, "-"], capture_output=True, text=True, timeout=60)
            if p.returncode == 0 and p.stdout.strip(): return p.stdout, "pdftotext"
        try:
            from pypdf import PdfReader
            reader = PdfReader(temp_path)
            return "\n\n".join((page.extract_text() or "") for page in reader.pages), "pypdf"
        except Exception:
            return "", "no_pdf_text_extractor"
    finally:
        try: os.unlink(temp_path)
        except OSError: pass

def make_source_record(concepts, text, title, source_file, module, module_name, heading_path, index_no, source_kind, authority=0.9, extra_keywords=None):
    txt = re.sub(r"\s+", " ", str(text or "")).strip()
    n = norm(txt)
    technical_fragment = bool(re.fullmatch(r"(?:>{1,2}|\d>|-[A-Za-z0-9]+|/[A-Za-z0-9_./-]+|\w[+#.:-]*)", txt))
    if not n and not technical_fragment: return None, "short_nonsearchable"
    if len(n) < 3 and not technical_fragment: return None, "short_nonsearchable"
    if UI_ONLY.match(txt): return None, "noninstructional_ui"
    known_parts = []
    for c in concepts:
        for key in ("title", "section_title", "lesson_title", "direct_answer"):
            v = norm(c.get(key, ""))
            if len(v) >= 3: known_parts.append(v)
    # A block already present in a larger, existing lesson/QRG record is represented there; do
    # not add a duplicate searchable record merely to inflate the count.
    if any(n == v or (len(n) >= 18 and (" " + n + " ") in (" " + v + " ")) for v in known_parts if n):
        return None, "covered_by_existing_record"
    new_id = stable_id("src", source_file, index_no, txt)
    search_title = (title or (heading_path[-1] if heading_path else Path(source_file).name)).strip()
    keywords = list(dict.fromkeys([module_name] + list(heading_path or []) + list(extra_keywords or [])))
    record = {
        "id": new_id, "module_number": module, "module_title": module_name,
        "lesson_title": " / ".join((heading_path or [])[-3:]) or Path(source_file).name,
        "section_title": search_title, "title": search_title, "concept_type": "source_content",
        "direct_answer": txt, "structured_points": [], "citation": source_file + ((" — " + " / ".join(heading_path)) if heading_path else ""),
        "keywords": [x for x in keywords if x], "query_anchors": [],
        "knowledge_source_type": source_kind, "record_type": "source_block",
        "source_file": source_file, "source_location": {"block_index": index_no, "heading_path": heading_path or []},
        "source_authority_score": authority, "search_prior": 0.74 if source_kind == "learner_course_html" else 0.68
    }
    concepts.append(record)
    return record, "indexed_new"

def build_curriculum_pages(page_rows, bundle):
    course_objectives, module_objectives, module_topics, lesson_topics, page_audit = [], [], [], [], []
    module_titles = (bundle.get("module_titles") or {})
    for source_path, raw in page_rows:
        module = module_from_path(source_path)
        parser = parse_html(raw)
        blocks = parser.blocks
        course_raw, module_raw = extract_explicit_objectives(blocks, source_path, module)
        if course_raw:
            for i, text in enumerate(course_raw, 1):
                course_objectives.append({"id": "co_" + str(i).zfill(2), "node_type": "course_objective", "title": text,
                    "statement": text, "module_number": None, "source_file": source_path, "parent_ids": ["course"], "importance_weight": 1.0,
                    "term_vector": sparse_vector(text), "source_authority_score": 1.0})
        if module and module_raw:
            for i, text in enumerate(module_raw, 1):
                module_objectives.append({"id": "mo_" + str(module).zfill(2) + "_" + str(i).zfill(2), "node_type": "module_objective",
                    "title": text, "statement": text, "module_number": module, "source_file": source_path, "parent_ids": ["module_" + str(module)],
                    "importance_weight": 0.84, "term_vector": sparse_vector(text), "source_authority_score": 1.0})
        actual_title = str(module_titles.get(str(module), module_titles.get(module, MODULE_TITLES.get(module, title_from_module_blocks(blocks, module)))))
        mt, lt = extract_topics(blocks, source_path, module, course_objectives, module_objectives, actual_title)
        module_topics.extend(mt); lesson_topics.extend(lt)
        page_audit.append({"path": source_path, "module_number": module, "module_title": actual_title, "visible_blocks": len(blocks),
                           "visible_chars": sum(len(x[1]) for x in blocks), "course_objectives_extracted": len(course_raw),
                           "module_objectives_extracted": len(module_raw), "module_topics_extracted": len(mt), "lesson_topics_extracted": len(lt)})
    if len(course_objectives) < 1: raise ValueError("No explicit course objectives extracted")
    # Link course objectives to the best-aligned module objectives; use explicit term vectors, not a model.
    edges = []
    module_objective_to_course = defaultdict(list)
    for co in course_objectives:
        candidates = sorted(((similarity(co["statement"], mo["statement"]), mo) for mo in module_objectives), key=lambda x: x[0], reverse=True)
        selected = [x for x in candidates if x[0] >= 0.075][:5]
        if not selected and candidates and candidates[0][0] >= 0.04: selected = candidates[:1]
        co["related_module_objective_ids"] = [mo["id"] for score, mo in selected]
        co["objective_alignment_confidence"] = round(max([score for score, _ in selected] or [0.0]), 3)
        for score, mo in selected:
            module_objective_to_course[mo["id"]].append(co["id"])
            edges.append({"from": co["id"], "relation": "aligned_to", "to": mo["id"], "confidence": round(score, 3)})
    for mo in module_objectives:
        mo["related_course_objective_ids"] = list(dict.fromkeys(module_objective_to_course.get(mo["id"], [])))
    for topic in module_topics + lesson_topics:
        relevant_objs = [x for x in module_objectives if x["module_number"] == topic["module_number"]]
        candidates = sorted(((similarity(topic["statement"], mo["statement"]), mo) for mo in relevant_objs), key=lambda x: x[0], reverse=True)
        selected = [x for x in candidates if x[0] >= 0.11][:3]
        if not selected and candidates and candidates[0][0] >= 0.06: selected = candidates[:1]
        topic["related_module_objective_ids"] = [mo["id"] for score, mo in selected]
        topic["related_course_objective_ids"] = list(dict.fromkeys(coid for score, mo in selected for coid in module_objective_to_course.get(mo["id"], [])))
        topic["term_vector"] = sparse_vector(topic["title"] + " " + topic["statement"])
        for score, mo in selected:
            edges.append({"from": topic["id"], "relation": "supports_objective", "to": mo["id"], "confidence": round(score, 3)})
        for coid in topic["related_course_objective_ids"]:
            edges.append({"from": topic["id"], "relation": "supports_course_objective", "to": coid, "confidence": 0.5})
    for topic in lesson_topics:
        parent = topic["parent_ids"][0] if topic.get("parent_ids") else None
        if parent: edges.append({"from": topic["id"], "relation": "part_of", "to": parent, "confidence": 1.0})
    return course_objectives, module_objectives, module_topics, lesson_topics, edges, page_audit

def add_visual_records(concepts, bundle, image_rows, image_metadata, image_alt_map):
    added, missing, image_records = 0, [], []
    for row in image_rows:
        name = row.split("/")[-1]
        meta = next((x for x in image_metadata.get("images", []) if x["file"] == name), None)
        if not meta:
            missing.append(name); continue
        module = int(meta["module_number"])
        # Preserve alt text parsed from the HTML alongside reviewed diagram transcription.
        alt = str(image_alt_map.get(name, "") or "")
        content = meta["title"] + ". "
        if alt: content += "Image alternative description: " + alt + ". "
        content += "Transcribed diagram content: " + meta["transcript"]
        if meta.get("scope"): content += " Scope note: " + meta["scope"]
        rec_id = "visual_" + name.rsplit(".", 1)[0]
        record = {
            "id": rec_id, "module_number": module, "module_title": MODULE_TITLES[module],
            "lesson_title": meta["title"], "section_title": meta["title"], "title": meta["title"],
            "concept_type": "visual_explanation", "direct_answer": content, "structured_points": [meta["transcript"]],
            "citation": "SCORM instructional illustration — images/" + name, "keywords": list(meta.get("keywords", [])),
            "query_anchors": ["What does the " + meta["title"].lower() + " diagram explain?"],
            "knowledge_source_type": "instructional_illustration", "record_type": "visual_content",
            "source_file": "images/" + name, "source_location": {"image_file": name, "alt_text": alt},
            "diagram_scope": meta.get("scope", "Instructional illustration"), "source_authority_score": 0.80,
            "search_prior": 0.76
        }
        concepts.append(record); image_records.append(rec_id); added += 1
    return added, missing, image_records

def attach_curriculum_links(concepts, course_objectives, module_objectives, module_topics, lesson_topics, assessment_items):
    edges = []
    module_objective_to_course = defaultdict(list)
    for co in course_objectives:
        for moid in co.get("related_module_objective_ids", []):
            module_objective_to_course[moid].append(co["id"])
    nodes = course_objectives + module_objectives + module_topics + lesson_topics
    node_by_id = {x["id"]: x for x in nodes}
    mod_obj_by_id = {x["id"]: x for x in module_objectives}
    co_by_id = {x["id"]: x for x in course_objectives}
    topics_by_module = defaultdict(list)
    for x in module_topics + lesson_topics: topics_by_module[x["module_number"]].append(x)
    # First link assessment question forms to the most relevant objective/topic records.
    for item in assessment_items:
        module = item.get("module_number")
        query = item["question"] + " " + str(item.get("correct_answer") or "") + " " + str(item.get("rationale") or "")
        topic_candidates = [x for x in topics_by_module.get(module, [])] if module is not None else (module_topics + lesson_topics)
        ranked = sorted(((similarity(query, x["title"] + " " + x["statement"]), x) for x in topic_candidates), key=lambda x: x[0], reverse=True)
        chosen = [x for x in ranked if x[0] >= 0.10][:3]
        if not chosen and ranked and ranked[0][0] >= 0.04: chosen = ranked[:1]
        item["lesson_topic_ids"] = [x["id"] for score, x in chosen if x["node_type"] == "lesson_topic"]
        item["module_topic_ids"] = [x["id"] for score, x in chosen if x["node_type"] == "module_topic"]
        related_mod_obj_ids = list(dict.fromkeys(moid for score, x in chosen for moid in x.get("related_module_objective_ids", [])))
        if not related_mod_obj_ids and module is not None:
            all_mo = [x for x in module_objectives if x["module_number"] == module]
            direct = sorted(((similarity(query, x["statement"]), x) for x in all_mo), key=lambda x: x[0], reverse=True)
            if direct and direct[0][0] > 0.04: related_mod_obj_ids = [direct[0][1]["id"]]
        item["module_objective_ids"] = related_mod_obj_ids
        item["course_objective_ids"] = list(dict.fromkeys(coid for moid in related_mod_obj_ids for coid in module_objective_to_course.get(moid, [])))
        item["relevance_confidence"] = round(max([score for score, _ in ranked[:1]] or [0.0]), 3)
    # Map each searchable record to its source/closest topic and objective context.
    text_corpus = []
    for c in concepts:
        module = c.get("module_number")
        source = str(c.get("source_file") or c.get("citation") or "")
        base_text = " ".join(str(c.get(k, "")) for k in ("title", "section_title", "lesson_title", "module_title"))
        answer_text = str(c.get("direct_answer") or "")
        module_topic_ids = list(c.get("module_topic_ids") or [])
        lesson_topic_ids = list(c.get("lesson_topic_ids") or [])
        current_node_ids = list(c.get("curriculum_node_ids") or [])
        current_node_ids = [x for x in current_node_ids if x in node_by_id]
        # Existing tutor records lack source file paths; infer their closest topics from explicit titles and
        # lesson metadata, then use answer text as a secondary signal.
        if not current_node_ids:
            candidates = topics_by_module.get(module, []) if module is not None else (module_topics + lesson_topics)
            candidate_scores = []
            for topic in candidates:
                title_score = similarity(base_text, topic["title"])
                body_score = similarity(answer_text[:1200], topic["title"])
                sc = max(title_score, body_score * 0.68)
                if sc > 0: candidate_scores.append((sc, topic))
            candidate_scores.sort(key=lambda x: x[0], reverse=True)
            for sc, topic in candidate_scores[:3]:
                if sc >= 0.09: current_node_ids.append(topic["id"])
        for node_id in current_node_ids:
            node = node_by_id[node_id]
            if node["node_type"] == "module_topic": module_topic_ids.append(node_id)
            elif node["node_type"] == "lesson_topic": lesson_topic_ids.append(node_id)
        module_topic_ids = list(dict.fromkeys(x for x in module_topic_ids if x in node_by_id))
        lesson_topic_ids = list(dict.fromkeys(x for x in lesson_topic_ids if x in node_by_id))
        chosen_topic_ids = list(dict.fromkeys(module_topic_ids + lesson_topic_ids))
        module_obj_ids = list(dict.fromkeys(moid for tid in chosen_topic_ids for moid in node_by_id[tid].get("related_module_objective_ids", [])))
        if not module_obj_ids and module is not None:
            objective_candidates = [x for x in module_objectives if x["module_number"] == module]
            scored_objs = sorted(((max(similarity(base_text, x["statement"]), similarity(answer_text[:1600], x["statement"]) * 0.65), x) for x in objective_candidates), key=lambda x: x[0], reverse=True)
            module_obj_ids = [x["id"] for sc, x in scored_objs[:2] if sc >= 0.10]
        course_obj_ids = list(dict.fromkeys(coid for moid in module_obj_ids for coid in module_objective_to_course.get(moid, [])))
        if not course_obj_ids:
            scored_course = sorted(((similarity(base_text + " " + answer_text[:1000], x["statement"]), x) for x in course_objectives), key=lambda x: x[0], reverse=True)
            course_obj_ids = [x["id"] for sc, x in scored_course[:2] if sc >= 0.12]
        c["course_objective_ids"] = course_obj_ids
        c["module_objective_ids"] = module_obj_ids
        c["module_topic_ids"] = module_topic_ids
        c["lesson_topic_ids"] = lesson_topic_ids
        c["curriculum_node_ids"] = list(dict.fromkeys(course_obj_ids + module_obj_ids + module_topic_ids + lesson_topic_ids))
        c["curriculum_search_text"] = " ".join([node_by_id[x]["title"] for x in c["curriculum_node_ids"] if x in node_by_id])
        c["objective_alignment_score"] = round(min(1.0, 0.6 * bool(course_obj_ids) + 0.4 * bool(module_obj_ids) + min(0.2, 0.05 * (len(lesson_topic_ids)+len(module_topic_ids)))), 3)
        t = str(c.get("record_type") or c.get("knowledge_source_type") or "existing_knowledge")
        base = {"course_objective": 1.0, "module_objective": 0.86, "assessment_answer": 0.80, "assessment": 0.78,
                "learner_quiz_answer": 0.77, "course_content": 0.66, "quick_reference": 0.70,
                "instructional_illustration": 0.47, "source_block": 0.42, "existing_knowledge": 0.63}.get(t, 0.60)
        importance = base + (0.12 if course_obj_ids else 0) + (0.09 if module_obj_ids else 0) + min(0.10, 0.025*len(set(c.get("assessment_item_ids") or [])))
        if re.search(r"\b(?:WARNING|DANGER|CRITICAL|do not|last resort|lock out|data loss|syntax error|unauthorized)\b", answer_text, re.I): importance += 0.04
        c["importance_score"] = round(min(1.0, importance), 3)
        c["importance_tier"] = "core" if importance >= 0.76 else ("supporting" if importance >= 0.61 else "reference")
        c["source_authority_score"] = float(c.get("source_authority_score", 0.88))
        c["curriculum_search_prior"] = float(c.get("search_prior", 1.0))
        c["assessment_item_ids"] = list(dict.fromkeys(c.get("assessment_item_ids") or []))
    # Attach question IDs to relevant knowledge records without allowing distractors into searchable text.
    for item in assessment_items:
        candidate_records = []
        words = item["question"] + " " + str(item.get("correct_answer") or "") + " " + str(item.get("rationale") or "")
        for c in concepts:
            if c.get("module_number") is not None and item.get("module_number") is not None and c.get("module_number") != item.get("module_number"): continue
            sc = max(similarity(words, str(c.get("title","")) + " " + str(c.get("section_title","")) + " " + str(c.get("lesson_title",""))),
                     similarity(words, str(c.get("direct_answer",""))[:1000]) * 0.7)
            if sc > 0: candidate_records.append((sc, c))
        candidate_records.sort(key=lambda x: x[0], reverse=True)
        item["related_record_ids"] = [c["id"] for sc, c in candidate_records[:3] if sc >= 0.10]
        for sc, c in candidate_records[:3]:
            if sc >= 0.10:
                c["assessment_item_ids"].append(item["id"])
                c["importance_score"] = round(min(1.0, float(c["importance_score"]) + 0.025), 3)
                if c["importance_score"] >= 0.76: c["importance_tier"] = "core"
    for item in assessment_items:
        for node_id in item.get("module_objective_ids", []) + item.get("course_objective_ids", []) + item.get("module_topic_ids", []) + item.get("lesson_topic_ids", []):
            if node_id in node_by_id:
                edges.append({"from": node_id, "relation": "assessed_by", "to": item["id"], "confidence": item.get("relevance_confidence", 0.0)})
    return nodes, edges

def main():
    for f in (PACKAGE, CANDIDATE_V1, GUIDE, QRG, IMG_DATA, LAB / "nonllm-tutor.js"):
        if not f.exists(): raise FileNotFoundError("Required file missing: " + str(f))
    source_hash = hashlib.sha256(PACKAGE.read_bytes()).hexdigest()
    guide = GUIDE.read_text(encoding="utf-8", errors="replace")
    prepost = parse_prepost_assessments(guide)
    image_metadata = json.loads(IMG_DATA.read_text(encoding="utf-8"))
    coverage = {"source_package": PACKAGE.name, "source_package_sha256": source_hash, "scorm_files": [], "supplementary_files": [],
                "html_pages": [], "design_objectives": [], "extraction_methods": {}, "image_transcriptions": {"expected": len(image_metadata.get("images", [])), "added": 0, "missing": []}}
    concepts = []
    with zipfile.ZipFile(CANDIDATE_V1, "r") as zin:
        bad = zin.testzip()
        if bad: raise ValueError("Candidate V1 package is corrupt: " + bad)
        names = zin.namelist()
        dpath = next((n for n in names if n.lower().endswith("ai-tutor/tutor-data.js")), None)
        if not dpath: raise ValueError("Missing ai-tutor/tutor-data.js in V1 package")
        bundle = builder.parse_bundle(zin.read(dpath).decode("utf-8", errors="replace"))
        concepts = bundle.get("concepts") or []
        if not concepts: raise ValueError("V1 package has no concepts")

        # Full learner-facing HTML text is retained as block records. Quiz UI is parsed into
        # structured assessment items separately to prevent distractor choices being treated as facts.
        page_rows, quiz_items, image_rows = [], [], []
        image_alt_map = {}
        html_source_names = []
        block_dispositions = {}
        new_block_count = duplicate_block_count = excluded_ui_count = structural_heading_count = 0
        page_blocks_eligible = page_blocks_covered = 0
        page_characters_visible = 0
        for name in names:
            low = name.lower()
            if low.endswith((".html", ".htm", ".xhtml")) and not low.startswith("ai-tutor/") and "/ai-tutor/" not in low:
                raw = zin.read(name).decode("utf-8", errors="replace")
                parsed = parse_html(raw)
                for image_ref in parsed.image_alts:
                    if image_ref.get("file") and image_ref.get("alt"):
                        image_alt_map[image_ref["file"]] = image_ref["alt"]
                visible = " ".join(x[1] for x in parsed.blocks)
                if len(visible) < 40:
                    coverage["scorm_files"].append({"path": name, "bytes": zin.getinfo(name).file_size, "kind": "html_runtime_shell",
                        "disposition": "audited as wrapper/UI; no substantial instructional text to index", "indexed": False})
                    continue
                module = module_from_path(name)
                content_raw = exp.remove_div_with_class(raw, "screen-quiz")
                page_rows.append((name, content_raw)); html_source_names.append(name)
                page_audit = parse_html(content_raw)
                blocks = page_audit.blocks
                qitems = parse_quiz_items(raw, name, module)
                quiz_items.extend(qitems)
                page_characters_visible += sum(len(t) for _, t in parsed.blocks)
                p_new = p_duplicate = p_ui = p_heading = 0
                topic_map = {}
                heading_stack = []
                current_module_topic_id = None
                current_lesson_topic_id = None
                # A heading is represented structurally; substantive body blocks are either linked to
                # existing knowledge or added as exact block records.
                for bi, (tag, text) in enumerate(blocks):
                    text = re.sub(r"\s+", " ", text).strip()
                    if re.fullmatch(r"h[1-6]", tag):
                        level = int(tag[1])
                        while heading_stack and heading_stack[-1]["level"] >= level: heading_stack.pop()
                        heading_stack.append({"level": level, "title": text})
                        p_heading += 1
                        p_heading_path = [x["title"] for x in heading_stack]
                        if level == 2:
                            current_module_topic_id = None
                            current_lesson_topic_id = None
                        elif level in (3,4):
                            current_lesson_topic_id = None
                        continue
                    if UI_ONLY.match(text):
                        p_ui += 1; continue
                    technical_fragment = bool(re.fullmatch(r"(?:>{1,2}|\d>|-[A-Za-z0-9]+|/[A-Za-z0-9_./-]+|\w[+#.:-]*)", text))
                    if len(norm(text)) < 3 and not technical_fragment:
                        p_ui += 1; continue
                    p_new_before = len(concepts)
                    text_norm = norm(text)
                    known_parts = [norm(str(c.get(k,""))) for c in concepts for k in ("title","section_title","lesson_title","direct_answer")]
                    if text_norm and any(text_norm == v or (len(text_norm) >= 18 and (" " + text_norm + " ") in (" " + v + " ")) for v in known_parts if v):
                        p_duplicate += 1; page_blocks_covered += 1
                        continue
                    # Select the active topical node by the matching current heading labels.
                    path_titles = [x["title"] for x in heading_stack]
                    rec, status = make_source_record(concepts, text, path_titles[-1] if path_titles else Path(name).name, name, module,
                            module_title(module), path_titles, bi, "learner_course_html", 1.0)
                    if rec:
                        rec["heading_tag"] = tag
                        # Map current heading labels to curriculum topic nodes after extraction below.
                        rec["source_location"]["heading_path"] = path_titles
                        p_new += 1; new_block_count += 1; page_blocks_covered += 1
                    elif status == "covered_by_existing_record":
                        p_duplicate += 1; page_blocks_covered += 1
                    elif status == "noninstructional_ui":
                        p_ui += 1
                    else:
                        p_ui += 1
                page_blocks_eligible += max(0, len(blocks) - p_heading - p_ui)
                duplicate_block_count += p_duplicate
                structural_heading_count += p_heading
                block_dispositions[name] = {"total_visible_blocks": len(parsed.blocks), "content_blocks_after_quiz_separation": len(blocks),
                    "heading_blocks_mapped_to_curriculum": p_heading, "new_searchable_records": p_new, "duplicate_or_already_covered_blocks": p_duplicate,
                    "intentionally_excluded_ui_or_short_fragments": p_ui, "visible_chars_including_quiz": sum(len(t) for _, t in parsed.blocks),
                    "quiz_items_extracted": len(qitems)}
                coverage["scorm_files"].append({"path": name, "bytes": zin.getinfo(name).file_size, "kind": "learner_facing_html",
                    "disposition": "course text represented by source blocks and curriculum nodes; quiz panel represented as structured assessment items",
                    "indexed": True})
            elif low.startswith("images/") and low.endswith((".png", ".jpg", ".jpeg", ".webp", ".svg")):
                image_rows.append(name)
                coverage["scorm_files"].append({"path": name, "bytes": zin.getinfo(name).file_size, "kind": "instructional_image",
                    "disposition": "visual content indexed from reviewed text transcription plus HTML alt description", "indexed": False})
            elif name.lower().endswith("ai-tutor/tutor-data.js"):
                coverage["scorm_files"].append({"path": name, "bytes": zin.getinfo(name).file_size, "kind": "existing_tutor_knowledge",
                    "disposition": "baseline tutor corpus used as input; retained and enriched in candidate", "indexed": True})
            elif low.endswith("imsmanifest.xml"):
                coverage["scorm_files"].append({"path": name, "bytes": zin.getinfo(name).file_size, "kind": "scorm_manifest",
                    "disposition": "course title and SCO/resource inventory audited; packaging metadata not treated as lesson prose", "indexed": False})
            elif low.endswith((".xsd", ".dtd")) or low.startswith("ai-tutor/") or low.endswith((".css", ".js")):
                coverage["scorm_files"].append({"path": name, "bytes": zin.getinfo(name).file_size, "kind": "runtime_or_packaging_asset",
                    "disposition": "not learner instructional text; preserved as SCORM/runtime infrastructure", "indexed": False})
            elif name.endswith("/") or not name:
                coverage["scorm_files"].append({"path": name, "bytes": zin.getinfo(name).file_size, "kind": "directory_entry",
                    "disposition": "no content bytes", "indexed": False})
            else:
                coverage["scorm_files"].append({"path": name, "bytes": zin.getinfo(name).file_size, "kind": "other_asset",
                    "disposition": "audited; no instructional-text extractor declared for this asset", "indexed": False})
        course_obj, module_obj, module_topics, lesson_topics, edges, page_topic_audit = build_curriculum_pages(page_rows, bundle)
        topic_nodes = {x["id"]: x for x in module_topics + lesson_topics}
        # Link body records to the nearest extracted headings using saved heading paths.
        title_to_ids = defaultdict(list)
        for x in module_topics + lesson_topics: title_to_ids[norm(x["title"])].append(x["id"])
        for c in concepts:
            loc = c.get("source_location") or {}
            path_titles = loc.get("heading_path", [])
            if path_titles:
                for title in path_titles:
                    c.setdefault("curriculum_node_ids", []).extend(title_to_ids.get(norm(title), []))
            c["curriculum_node_ids"] = list(dict.fromkeys(c.get("curriculum_node_ids") or []))
        # Add a text record for each approved assessment answer and keep the full choices separately as typed data.
        assessment_items = prepost + quiz_items
        for item in assessment_items:
            # Keep question, every choice, correctness, answer and rationale as typed data.
            # Choices marked as distractors are not indexed as answer evidence.
            if item.get("kind") == "module_quiz":
                title_norm = norm(item["question"])
                rec = next((x for x in concepts if norm(x.get("title","")) == title_norm), None)
                if not rec:
                    answer_text = ("Correct answer: " + item["correct_answer"] +
                        (". Explanation: " + item["rationale"] if item.get("rationale") else "")) if item.get("correct_answer") else ""
                    rec = builder.make_record("lab_full_" + item["id"], item["question"], answer_text,
                        item.get("module_number") or 1, module_title(item.get("module_number")), item["citation"], "assessment")
                    rec["knowledge_source_type"] = "learner_quiz_answer" if item.get("correct_answer") else "assessment_question"
                    rec["record_type"] = "learner_quiz_answer" if item.get("correct_answer") else "assessment_question"
                    rec["source_file"] = item["source_file"]
                    rec["source_authority_score"] = 0.94 if item.get("correct_answer") else 0.40
                    rec["search_prior"] = 0.60 if item.get("correct_answer") else 0.36
                    rec["query_anchors"] = list(dict.fromkeys((rec.get("query_anchors") or []) + [item["question"]]))
                    concepts.append(rec)
                rec["assessment_item_ids"] = list(dict.fromkeys((rec.get("assessment_item_ids") or []) + [item["id"]]))
                rec["assessment_metadata"] = {"item_id": item["id"], "kind": item["kind"], "correct_option": item.get("correct_option"),
                    "correct_answer": item.get("correct_answer"), "rationale": item.get("rationale"), "choices": item.get("choices", [])}
                item["related_record_ids"] = [rec["id"]]
            else:
                rec = next((x for x in concepts if norm(x.get("title","")) == norm(item["question"])), None)
                correct_text = "Correct answer: " + item["correct_answer"] + (". Rationale: " + item["rationale"] if item.get("rationale") else "")
                if not rec:
                    rec = builder.make_record("lab_full_" + item["id"], item["question"], correct_text,
                        item.get("module_number") or 1, module_title(item.get("module_number")), item["citation"], "assessment")
                    rec["knowledge_source_type"] = "assessment_answer"
                    rec["record_type"] = "assessment_answer"
                    rec["source_file"] = GUIDE.name
                    if item.get("module_number") is None:
                        rec["module_number"] = None
                        rec["module_title"] = "Course-wide assessment evidence"
                    concepts.append(rec)
                elif correct_text and norm(item["correct_answer"]) not in norm(rec.get("direct_answer", "")):
                    rec["direct_answer"] = (str(rec.get("direct_answer", "")).strip() + "\\n\\n" + correct_text).strip()[:5000]
                rec["record_type"] = "assessment_answer"
                rec["knowledge_source_type"] = "assessment_answer"
                rec["source_file"] = GUIDE.name
                rec["source_authority_score"] = 1.0
                rec["assessment_item_ids"] = list(dict.fromkeys((rec.get("assessment_item_ids") or []) + [item["id"]]))
                rec["assessment_metadata"] = {"item_id": item["id"], "kind": item["kind"], "correct_option": item["correct_option"],
                    "correct_answer": item["correct_answer"], "rationale": item["rationale"], "choices": item["choices"]}
                item["related_record_ids"] = [rec["id"]]
        image_added, image_missing, image_ids = add_visual_records(concepts, bundle, image_rows, image_metadata, image_alt_map)
        coverage["image_transcriptions"] = {"expected": len(image_metadata.get("images", [])), "actual_scorm_images": len(image_rows),
            "added": image_added, "missing": image_missing, "all_scorm_images_covered": len(image_rows) == image_added and not image_missing}
        if image_missing: raise ValueError("No reviewed text transcription for SCORM images: " + ", ".join(image_missing))

        # Supplementary reference formats are extracted and de-duplicated against the already indexed HTML.
        # PDFs are extracted on CI for audit; unique Quick Reference material is indexed, the trainer-guide
        # PDF is restricted to the approved pre/post answer-key records.
        def add_plaintext_source(source_name, text_content, source_kind, module=None):
            count_new = count_dup = count_ui = 0
            for i, para in enumerate(re.split(r"\n\s*\n|\f", text_content or "")):
                para = re.sub(r"\s+", " ", para).strip()
                technical_fragment = bool(re.fullmatch(r"(?:>{1,2}|\d>|-[A-Za-z0-9]+|/[A-Za-z0-9_./-]+|\w[+#.:-]*)", para))
                if len(norm(para)) < 3 and not technical_fragment: continue
                known = " || ".join(norm(str(c.get(k,""))) for c in concepts for k in ("title","section_title","lesson_title","direct_answer"))
                if norm(para) in known:
                    count_dup += 1; continue
                rec, status = make_source_record(concepts, para, source_name, source_name, module, module_title(module), [], i,
                    source_kind, 0.94)
                if rec: count_new += 1
                elif status == "covered_by_existing_record": count_dup += 1
                else: count_ui += 1
            return {"source": source_name, "text_chars_extracted": len(text_content or ""), "unique_records_added": count_new,
                    "duplicate_blocks": count_dup, "other_excluded_blocks": count_ui}

        # Parse the Quick Reference PDF; its duplicate text is not added twice, unique text is preserved.
        pdf_audit = {}
        # The Quick Reference HTML is canonical, but the legacy section splitter can omit
        # short inline-code fragments. Add uncovered blocks using the inline-preserving parser.
        qrg_parser = parse_html(QRG.read_text(encoding="utf-8", errors="replace"))
        qrg_headings = []
        qrg_block_audit = {"source": QRG.name, "visible_blocks": len(qrg_parser.blocks), "new_records": 0,
            "duplicate_or_covered_blocks": 0, "excluded_noninstructional_blocks": 0}
        for qbi, (qtag, qtext) in enumerate(qrg_parser.blocks):
            qtext = re.sub(r"\s+", " ", qtext).strip()
            if re.fullmatch(r"h[1-6]", qtag):
                level = int(qtag[1])
                while qrg_headings and qrg_headings[-1][0] >= level: qrg_headings.pop()
                qrg_headings.append((level, qtext))
                continue
            if UI_ONLY.match(qtext) or not qtext.strip():
                qrg_block_audit["excluded_noninstructional_blocks"] += 1; continue
            current_path = [x[1] for x in qrg_headings]
            rec, status = make_source_record(concepts, qtext, current_path[-1] if current_path else QRG.name,
                QRG.name, None, "Quick Reference Guide", current_path, qbi, "quick_reference_html_block", 0.98)
            if rec:
                rec["record_type"] = "quick_reference"
                rec["knowledge_source_type"] = "quick_reference"
                qrg_block_audit["new_records"] += 1
            elif status == "covered_by_existing_record":
                qrg_block_audit["duplicate_or_covered_blocks"] += 1
            else:
                qrg_block_audit["excluded_noninstructional_blocks"] += 1
        coverage["quick_reference_html_block_coverage"] = qrg_block_audit
        for pdf_path, role in ((QRG_PDF, "learner_quick_reference_pdf"), (GUIDE_PDF, "instructor_prepost_assessment_pdf")):
            if not pdf_path.exists():
                pdf_audit[pdf_path.name] = {"status": "not_present", "extraction_method": None}; continue
            txt, method = extract_pdf_text_bytes(pdf_path.read_bytes(), pdf_path.name)
            pdf_audit[pdf_path.name] = {"status": "text_extracted" if txt.strip() else "text_extraction_unavailable",
                                       "extraction_method": method, "extracted_chars": len(txt),
                                       "policy": "index/deduplicate learner reference" if role == "learner_quick_reference_pdf" else "approved pre/post answer-key sections only; instructor-only remainder excluded"}
            if role == "learner_quick_reference_pdf" and txt.strip():
                pdf_audit[pdf_path.name]["indexing"] = add_plaintext_source(pdf_path.name, txt, "quick_reference_pdf", None)
            elif role == "instructor_prepost_assessment_pdf" and txt.strip():
                guide_norm, pdf_norm = norm(guide), norm(txt)
                pdf_words, guide_words = set(guide_norm.split()), set(pdf_norm.split())
                pdf_audit[pdf_path.name]["text_similarity_to_txt_source"] = round(len(pdf_words & guide_words) / max(1, len(pdf_words | guide_words)), 3)
        zip_audit = []
        if QRG_ZIP.exists():
            with zipfile.ZipFile(QRG_ZIP, "r") as qz:
                for info in qz.infolist():
                    if info.is_dir(): continue
                    ext = Path(info.filename).suffix.lower()
                    record = {"path": QRG_ZIP.name + "!" + info.filename, "bytes": info.file_size, "kind": ext or "binary"}
                    data = qz.read(info.filename)
                    if ext in (".html", ".htm", ".xhtml"):
                        parser = parse_html(data.decode("utf-8", "replace"))
                        text_content = "\n\n".join(t for _, t in parser.blocks)
                        record["disposition"] = "html text checked and de-duplicated against canonical Quick Reference HTML"
                        record["indexing"] = add_plaintext_source(record["path"], text_content, "quick_reference_archive", None)
                    elif ext in (".txt", ".md", ".csv"):
                        record["disposition"] = "text extracted and de-duplicated"
                        record["indexing"] = add_plaintext_source(record["path"], data.decode("utf-8", "replace"), "quick_reference_archive", None)
                    elif ext == ".pdf":
                        txt, method = extract_pdf_text_bytes(data, record["path"])
                        record["pdf_text_method"] = method
                        record["disposition"] = "pdf text extracted and de-duplicated" if txt.strip() else "pdf found; text extraction unavailable"
                        record["indexing"] = add_plaintext_source(record["path"], txt, "quick_reference_archive", None) if txt.strip() else {"unique_records_added": 0}
                    else:
                        record["disposition"] = "nested binary audited; no distinct instructional text parser registered"
                    zip_audit.append(record)
        coverage["supplementary_files"] = [
            {"path": QRG.name, "bytes": QRG.stat().st_size, "kind": "learner_quick_reference_html", "disposition": "indexed and linked to curriculum topics", "indexed": True},
            {"path": QRG_PDF.name, "bytes": QRG_PDF.stat().st_size if QRG_PDF.exists() else 0, "kind": "learner_quick_reference_pdf",
             "disposition": pdf_audit.get(QRG_PDF.name, {}).get("status", "not_present"), "indexed": bool(pdf_audit.get(QRG_PDF.name, {}).get("extracted_chars", 0))},
            {"path": QRG_ZIP.name, "bytes": QRG_ZIP.stat().st_size if QRG_ZIP.exists() else 0, "kind": "quick_reference_archive", "disposition": "nested content inventoried; text extracted and deduplicated", "indexed": bool(zip_audit)},
            {"path": GUIDE.name, "bytes": GUIDE.stat().st_size, "kind": "trainer_guide_text", "disposition": "only approved pre/post answer-key Q&A indexed; Module Q&A Reference and other instructor-only material excluded by existing source policy", "indexed": True},
            {"path": GUIDE_PDF.name, "bytes": GUIDE_PDF.stat().st_size if GUIDE_PDF.exists() else 0, "kind": "trainer_guide_pdf",
             "disposition": pdf_audit.get(GUIDE_PDF.name, {}).get("policy", "approved pre/post answer-key Q&A only"), "indexed": False}
        ]
        # Add relationships and explicit importance metadata to every record, while retaining exact source strings.
        all_nodes, assessment_edges = attach_curriculum_links(concepts, course_obj, module_obj, module_topics, lesson_topics, assessment_items)
        edges.extend(assessment_edges)
        # Add course/module/topic vocabulary to the corresponding records and construct explicit sparse term vectors.
        course = {"id": "course", "node_type": "course", "title": "LNX-001 Linux Administration Essentials",
                  "statement": "Linux Administration Essentials course; Linux CLI, filesystems, users and permissions, hardware and storage, processes, host networking and baseline security.",
                  "term_vector": sparse_vector("Linux Administration Essentials Linux CLI filesystems users permissions hardware storage processes host networking baseline security"),
                  "importance_weight": 1.0}
        modules = []
        for mod in range(0,5):
            nodes_for = [n for n in all_nodes if n.get("module_number") == mod]
            modules.append({"id": "module_" + str(mod), "module_number": mod, "title": MODULE_TITLES[mod],
                "node_type": "module", "parent_ids": ["course"],
                "course_objective_ids": list(dict.fromkeys(coid for mo in module_obj if mo["module_number"] == mod
                    for coid in next((co["id"] for co in course_obj if mo["id"] in co.get("related_module_objective_ids", [])), []))),
                "module_objective_ids": [x["id"] for x in module_obj if x["module_number"] == mod],
                "module_topic_ids": [x["id"] for x in module_topics if x.get("module_number") == mod],
                "lesson_topic_ids": [x["id"] for x in lesson_topics if x.get("module_number") == mod],
                "term_vector": sparse_vector(MODULE_TITLES[mod])})
        for mod_record in modules:
            edges.append({"from": mod_record["id"], "relation": "part_of", "to": "course", "confidence": 1.0})
        for node in all_nodes:
            for parent_id in node.get("parent_ids", []):
                if parent_id == "course" or any(parent_id == mod_record["id"] for mod_record in modules):
                    edges.append({"from": node["id"], "relation": "part_of", "to": parent_id, "confidence": 1.0})
        structure = {"version": "curriculum-linked-sparse-vector-rrf-v2", "representation": "sparse lexical term vectors + explicit curriculum graph; no learned embeddings",
            "course": course, "modules": modules, "course_objectives": course_obj, "module_objectives": module_obj,
            "module_topics": module_topics, "lesson_topics": lesson_topics, "lesson_objectives": [],
            "nodes": [course] + modules + all_nodes,
            "edges": edges, "source_policy": "Learner-facing instructional content and approved assessment Q&A only; full assessment choices are typed metadata and distractors are never promoted to answer evidence."}
        bundle["concepts"] = concepts
        bundle["curriculum_structure"] = structure
        bundle["assessment_items"] = assessment_items
        rules = bundle.get("non_llm_generation_rules") or {}
        rules["curriculum_structure"] = {"version": structure["version"], "enabled": True,
            "node_count": len(structure["nodes"]), "edge_count": len(structure["edges"])}
        rules["curriculum_search"] = {"enabled": True, "objective_vector_scoring": True, "importance_weighting": True,
            "reciprocal_rank_fusion": True, "query_grammar": "Lucene-inspired safe subset; internal natural-question compilation, exact phrase and literal detection, field weighting; not a full Lucene parser",
            "lexical_ranker": "BM25-style term-frequency/inverse-document-frequency with field weights and exact technical literal boosts",
            "importance_policy": "Objective alignment influences rank only after topical relevance; direct answer evidence and exact commands outrank globally important but unrelated topics."}
        rules["training_sources"] = {**(rules.get("training_sources") or {}), "explicit_course_objectives": len(course_obj),
            "explicit_module_objectives": len(module_obj), "module_topics": len(module_topics), "lesson_topics": len(lesson_topics),
            "structured_assessment_items": len(assessment_items), "assessment_choices_in_dataset": sum(len(x.get("choices") or []) for x in assessment_items),
            "instructional_images_with_transcribed_content": image_added}
        rules["version"] = "non-llm-curriculum-graph-v2"
        bundle["non_llm_generation_rules"] = rules
        bundle["ai_tutor_lab_experiment"] = {"version":"non-llm-curriculum-linked-v2", "primary_tutor_ui_changed":False,
            "runtime":"pure JavaScript; sparse vectors + objective graph + BM25-style ranking + RRF; no LLM, neural embeddings, WebAssembly or runtime network calls",
            "source_policy": structure["source_policy"]}

        new_data_js = "window.__CS_AI_TUTOR_DATA__ = " + json.dumps(bundle, ensure_ascii=False, separators=(",", ":")) + ";\n"
        # Validate complete source package is untouched and repackage as a separate V2 candidate.
        with zipfile.ZipFile(CANDIDATE_V2, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zout:
            for entry in zin.infolist():
                payload = new_data_js.encode("utf-8") if entry.filename == dpath else zin.read(entry.filename)
                zout.writestr(entry, payload)
        with zipfile.ZipFile(CANDIDATE_V2, "r") as check:
            bad = check.testzip()
            if bad: raise ValueError("V2 package ZIP integrity failure: " + bad)
            new_names = check.namelist()
        if hashlib.sha256(PACKAGE.read_bytes()).hexdigest() != source_hash:
            raise ValueError("Original SCORM source package hash changed unexpectedly")

    # Rebuild searchable index data and preserve the pre-enrichment V1 dataset for a three-way comparison.
    old_payload = {"concepts": [], "generation_rules": {}}
    try:
        current_index = json.loads(IDX.read_text(encoding="utf-8"))
        old_payload = current_index
    except Exception: pass
    # V1 index is rebuilt from the V1 candidate before enrichment metadata is added by reading its tutor bundle.
    with zipfile.ZipFile(CANDIDATE_V1, "r") as z1:
        d1 = next(n for n in z1.namelist() if n.lower().endswith("ai-tutor/tutor-data.js"))
        base_bundle = builder.parse_bundle(z1.read(d1).decode("utf-8", "replace"))
        base_concepts = base_bundle.get("concepts") or []
        base_rules = base_bundle.get("non_llm_generation_rules") or {}
    (LAB / "nonllm-index-v1-baseline.json").write_text(json.dumps({"concepts": base_concepts, "generation_rules": base_rules}, ensure_ascii=False), encoding="utf-8")
    (LAB / "nonllm-index.json").write_text(json.dumps({"concepts": concepts, "generation_rules": rules, "curriculum_structure": structure,
        "assessment_items": assessment_items}, ensure_ascii=False), encoding="utf-8")

    # Finish file-by-file inventory, including directory, schema, and runtime entries; no silent source omissions.
    img_set = {Path(x).name for x in image_rows}
    for item in coverage["scorm_files"]:
        if item.get("kind") == "instructional_image":
            item["indexed"] = Path(item["path"]).name in img_set and Path(item["path"]).name in {x["file"] for x in image_metadata["images"]}
    coverage["nested_quick_reference_archive_entries"] = zip_audit
    coverage["pdf_extraction"] = pdf_audit
    coverage["html_block_dispositions"] = block_dispositions
    coverage["course_html_paths_indexed"] = html_source_names
    coverage["course_html_block_coverage"] = {"visible_chars_including_quiz": page_characters_visible, "eligible_text_blocks": page_blocks_eligible,
        "blocks_added_as_records": new_block_count, "blocks_already_covered": duplicate_block_count,
        "ui_or_short_fragments_excluded": excluded_ui_count, "structural_headings_mapped_to_topics_or_metadata": structural_heading_count}
    inventory_expected = len(names)
    inventory_covered = sum(1 for x in coverage["scorm_files"] if x.get("disposition"))
    coverage["scorm_inventory_counts"] = {"entries_in_package": inventory_expected, "entries_with_explicit_disposition": inventory_covered,
        "coverage_complete": inventory_expected == inventory_covered}
    coverage["curriculum_counts"] = {"course_objectives": len(course_obj), "module_objectives": len(module_obj),
        "module_topics": len(module_topics), "lesson_topics": len(lesson_topics), "lesson_objectives_explicitly_defined": 0,
        "graph_nodes": len(structure["nodes"]), "graph_edges": len(edges),
        "lesson_objective_policy": "No separately authored lesson-objective lists are present in the current source; lesson topics link to module objectives rather than fabricating objectives."}
    coverage["assessment_counts"] = {"pre_assessment_questions": sum(x["kind"] == "pre" for x in assessment_items),
        "post_assessment_questions": sum(x["kind"] == "post" for x in assessment_items),
        "module_quiz_questions": sum(x["kind"] == "module_quiz" for x in assessment_items), "total_items": len(assessment_items),
        "items_with_correct_answer": sum(bool(x.get("correct_answer")) for x in assessment_items),
        "items_with_choices": sum(bool(x.get("choices")) for x in assessment_items),
        "choices_total": sum(len(x.get("choices") or []) for x in assessment_items),
        "choices_with_correctness_labels": sum(1 for x in assessment_items for c in x.get("choices") or [] if "is_correct" in c),
        "items_linked_to_objectives_or_topics": sum(bool(x.get("course_objective_ids") or x.get("module_objective_ids") or x.get("module_topic_ids") or x.get("lesson_topic_ids")) for x in assessment_items)}
    c_linked = sum(bool(c.get("curriculum_node_ids")) for c in concepts)
    c_importance = sum("importance_score" in c and "importance_tier" in c for c in concepts)
    coverage["record_link_counts"] = {"searchable_records": len(concepts), "records_linked_to_curriculum": c_linked,
        "records_with_importance_metadata": c_importance, "curriculum_link_rate": round(c_linked/max(1,len(concepts)), 4)}
    # Capture actual source files and their treatment outside the SCORM archive.
    coverage["support_files"] = [{"path": str(p.name), "exists": p.exists(), "bytes": p.stat().st_size if p.exists() else 0} for p in (QRG, QRG_PDF, QRG_ZIP, GUIDE, GUIDE_PDF)]
    coverage["design_objectives"] = [
        {"id":"D1","objective":"Every SCORM archive entry has an explicit indexed/excluded/metadata-only disposition","status":"PASS" if coverage["scorm_inventory_counts"]["coverage_complete"] else "FAIL","measured":coverage["scorm_inventory_counts"]},
        {"id":"D2","objective":"All substantive learner-facing HTML blocks are searchable or demonstrably covered by an existing record","status":"PASS" if (len(html_source_names) and page_blocks_covered >= page_blocks_eligible) else "REVIEW","measured":coverage["course_html_block_coverage"]},
        {"id":"D3","objective":"All instructional SCORM images have reviewed textual content beyond filename-only indexing","status":"PASS" if image_added == len(image_rows) == len(image_metadata["images"]) else "FAIL","measured":coverage["image_transcriptions"]},
        {"id":"D4","objective":"Course objectives, module objectives, module topics, and lesson topics are extracted and represented as linked nodes; lesson-objective availability is explicitly audited","status":"PASS" if len(course_obj)==5 and len(module_obj)>=10 and len(module_topics)>0 and len(lesson_topics)>0 else "REVIEW","measured":coverage["curriculum_counts"]},
        {"id":"D5","objective":"Pre/post assessment and learner quiz questions, choices, correct answer and rationale are structured without promoting distractors to evidence","status":"PASS" if len(assessment_items)==48 and coverage["assessment_counts"]["items_with_choices"]==48 and coverage["assessment_counts"]["choices_with_correctness_labels"]==coverage["assessment_counts"]["choices_total"] else "REVIEW","measured":coverage["assessment_counts"]},
        {"id":"D6","objective":"Search records carry source provenance, topic/objective links, and explicit importance metadata","status":"PASS" if c_importance==len(concepts) and coverage["record_link_counts"]["curriculum_link_rate"]>=0.80 else "REVIEW","measured":coverage["record_link_counts"]},
        {"id":"D7","objective":"Query-time ranking can use sparse objective/topic vectors, importance and RRF without a neural model","status":"PENDING_TEST","measured":{"representation":structure["representation"],"runtime_model_count":0,"runtime_network_calls_added":False}},
        {"id":"D8","objective":"Candidate SCORM is valid and the original SCORM source hash is unchanged","status":"PASS" if CANDIDATE_V2.exists() and hashlib.sha256(PACKAGE.read_bytes()).hexdigest()==source_hash else "FAIL","measured":{"candidate_bytes":CANDIDATE_V2.stat().st_size,"source_sha256":source_hash,"source_package_unchanged":True}}
    ]
    (SUMMARY).write_text(json.dumps({"experiment":"non-llm-curriculum-linked-v2","source_package_hash":source_hash,
        "source_package_bytes":PACKAGE.stat().st_size,"candidate_v1_bytes":CANDIDATE_V1.stat().st_size,
        "candidate_v2":CANDIDATE_V2.name,"candidate_v2_sha256":hashlib.sha256(CANDIDATE_V2.read_bytes()).hexdigest(),
        "candidate_v2_bytes":CANDIDATE_V2.stat().st_size,"bytes_added_vs_v1":CANDIDATE_V2.stat().st_size-CANDIDATE_V1.stat().st_size,
        "runtime_model_count":0,"extra_model_bytes":0,"webassembly_added":False,"runtime_network_calls_added":False,
        "base_concepts_before_enrichment":len(base_concepts),"candidate_searchable_records":len(concepts),
        "course_objective_count":len(course_obj),"module_objective_count":len(module_obj),"module_topic_count":len(module_topics),
        "lesson_topic_count":len(lesson_topics),"assessment_item_count":len(assessment_items),"image_transcription_count":image_added,
        "source_block_records_added":new_block_count,"coverage":coverage,"design_objectives":coverage["design_objectives"],
        "pdf_audit":pdf_audit},ensure_ascii=False,indent=2),encoding="utf-8")
    (AUDIT).write_text(json.dumps(coverage,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"candidate":CANDIDATE_V2.name,"record_count":len(concepts),"course_objectives":len(course_obj),
        "module_objectives":len(module_obj),"module_topics":len(module_topics),"lesson_topics":len(lesson_topics),
        "assessment_items":len(assessment_items),"images":image_added,"design_objectives":coverage["design_objectives"],
        "source_sha256_unchanged":hashlib.sha256(PACKAGE.read_bytes()).hexdigest()==source_hash},ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
