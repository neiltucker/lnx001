# LNX-001 AI Tutor Lab

All experiments are isolated to branch `ai-tutor-lab/full-course-knowledge-v1`. Courseware Studio is not modified, and the original SCORM ZIP in `main` is never overwritten.

V1–V5 expanded the packaged knowledge corpus from 320 to 488 concepts using learner-facing SCORM HTML, the Quick Reference Guide HTML and only pre/post instructor answer-key Q&A from the Trainer Preparation Guide. V5 improved the fixed deterministic retrieval benchmark from 14/20 to 19/20 with no regressions, but that measured prepared-answer selection, not response generation.

V6/V7 tested the pinned Gab 100M Q8 model with pure-JavaScript CPU inference, no WebAssembly and no hosted service. The model prototype failed its factual answer checks and was too slow for a normal chat experience. **Do not integrate Gab 100M Q8 into the primary tutor.** See `docs/AI_TUTOR_LOCAL_MODEL_V6_FINDINGS.md` for the per-question results and the recommended next experiment.

All validation remains in GitHub Actions and all candidate SCORM packages are workflow artifacts; no generated ZIP overwrites the source package. No changes to Courseware Studio are permitted until the findings are discussed and a production plan is explicitly agreed.
