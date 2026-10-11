# LNX-001 AI Tutor Lab — Version 4

This lab is isolated to the `ai-tutor-lab/full-course-knowledge-v1` branch. No Courseware Studio files are changed, and the original SCORM ZIP is never overwritten.

V1 tested adding the full learner-facing SCORM HTML, the Quick Reference Guide HTML, and only pre/post instructor answer-key Q&A from the Trainer Preparation Guide. V2 improved build-time metadata, and V3 introduced a lab-only IDF-weighted query-coverage penalty to reduce overly generic matches.

V4 refines that experiment: the coverage penalty is less aggressive to preserve paraphrased questions, and a verification-command anchor is attached only to passages that actually contain verification/inspection wording. The candidate still has no hosted inference, network calls, WebAssembly, or new runtime dependency.

GitHub Actions compares the original package against a separate V4 candidate and uploads the candidate ZIP plus per-query answer report as an artifact. Generated outputs are not committed to the repository automatically.
