# LNX-001 AI Tutor Lab

All experiments are isolated to branch `ai-tutor-lab/full-course-knowledge-v1`. Courseware Studio is not modified, and the original SCORM ZIP in `main` is never overwritten.

V1–V5 expanded the packaged knowledge corpus from 320 to 488 concepts using learner-facing SCORM HTML, the Quick Reference Guide HTML and only pre/post instructor answer-key Q&A from the Trainer Preparation Guide. V5 improved the fixed deterministic retrieval benchmark from 14/20 to 19/20 with no regressions, but that measured prepared-answer selection, not response generation.

V6/V7 tested the pinned Gab 100M Q8 model with pure-JavaScript CPU inference, no WebAssembly and no hosted service. The model prototype failed its factual answer checks and was too slow for a normal chat experience. **Do not integrate Gab 100M Q8 into the primary tutor.** See `docs/AI_TUTOR_LOCAL_MODEL_V6_FINDINGS.md` for the per-question results and the recommended next experiment.

All validation remains in GitHub Actions and all candidate SCORM packages are workflow artifacts; no generated ZIP overwrites the source package. No changes to Courseware Studio are permitted until the findings are discussed and a production plan is explicitly agreed.


## Offline small-model evaluations

See [`docs/AI_TUTOR_SMALL_MODEL_TESTS.md`](../docs/AI_TUTOR_SMALL_MODEL_TESTS.md) for the validated SmolLM2-135M result and ordered model sequence. Results from GitHub Actions, not local testing, determine acceptance. The 135M pure-JavaScript CPU configuration failed all 3 technical fact checks and took 45.7–74.1 seconds per response.


## Algorithmic no-LLM experiment

The isolated experiment in `nonllm-experiment.py` evaluates a model-free alternative that uses weighted lexical/BM25-style ranking, exact technical-term matching, course-specific aliases, question anchors from the pre/post answer keys and learner-visible module quizzes, sentence selection, and deterministic natural-language answer templates.

The build source policy remains restricted to learner-facing SCORM HTML, Quick Reference Guide HTML, and pre/post instructor answer-key Q&A from the Trainer Preparation Guide. Learner-facing quiz questions improve query matching; quiz choices are not treated as facts unless the source explicitly identifies a correct answer or feedback. The candidate adds a standalone in-package demo page without replacing the primary tutor UI.

Results and the candidate package are produced as a GitHub Actions artifact named `lnx001-ai-tutor-nonllm-algorithmic-v1`. No model files, WebAssembly, hosted inference, or runtime network requests are added. The original SCORM ZIP and Courseware Studio production assets remain unchanged.


## Curriculum-linked, full-coverage no-LLM experiment (V2)

The next isolated experiment is defined in `curriculum-enrichment.py`. It audits every SCORM archive entry, preserves all searchable learner-facing HTML blocks including inline code, ingests all 11 instructional figures through reviewed text transcriptions, deduplicates supplemental Quick Reference PDF/ZIP text, and records the approved 30 pre/post assessment questions plus 18 learner-facing quiz questions with typed choices, correctness labels, answers and rationales.

The generated knowledge graph links course objectives, module objectives, module and lesson topics, searchable source records, and assessment items. Each searchable record carries source provenance, curriculum relationships, objective alignment and a bounded importance tier. The JavaScript query path uses a Lucene-inspired structured query plan, BM25-style lexical retrieval, exact technical-literal boosts, sparse curriculum-term matching, and Reciprocal Rank Fusion (RRF). Objective weighting is applied only after topical relevance, so globally important but unrelated concepts cannot displace exact technical evidence.

Validation compares three configurations on the same fixed and held-out question set: the original tutor, the prior no-LLM prototype, and curriculum-linked V2. The build writes a per-file source coverage audit, a curriculum build summary, a per-design-objective measurement JSON, detailed per-question outputs and a separate V2 candidate SCORM package. Any absent lesson-level objectives are reported as absent in the source rather than invented. Runtime still contains no LLM, neural embedding model, WebAssembly, or network dependency. Production and the original source SCORM are untouched.
