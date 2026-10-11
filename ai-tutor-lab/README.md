# LNX-001 AI Tutor Lab — Version 2

This experiment is isolated to branch `ai-tutor-lab/full-course-knowledge-v1`. No Courseware Studio files are changed, and the original SCORM ZIP is never overwritten.

Version 1 assembled a course-wide knowledge pack from readable SCORM HTML, the learner-facing Quick Reference Guide HTML, and only pre/post instructor answer-key Q&A from the Trainer Preparation Guide. The guide's Module Q&A Reference and all other instructor-only material are excluded.

Version 2 keeps the same source policy and unchanged tutor JavaScript, but improves build-time indexing by prioritizing literal technical paths, IP addresses, identifiers, and inline code; generating descriptive titles from otherwise generic procedure headings; and adding generic question anchors for address/interface and configuration-path relationships.

GitHub Actions runs a fixed baseline-versus-candidate suite against the actual embedded JavaScript runtime and publishes the V2 package plus JSON/Markdown reports as an artifact. Generated packages and reports are not committed automatically.

This experiment tests deterministic retrieval only. It does not provide generative multi-passage synthesis or establish Chatbase equivalence.
