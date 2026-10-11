# LNX-001 AI Tutor Lab

This is an isolated, repeatable test environment for the existing exported Linux SCORM course. All work is on branch ai-tutor-lab/full-course-knowledge-v1. No files in Courseware Studio are changed and the original SCORM ZIP is never overwritten.

The first experiment keeps the existing tutor JavaScript unchanged and changes only the packaged knowledge data. It adds readable HTML content from the SCORM archive, the repository's Day-01-QuickReference.html, and only the pre/post instructor answer-key Q&A sections from LNX-001_EN_TrainerPreparationGuide.txt. It specifically excludes the guide's Module Q&A Reference and all other guide content.

A GitHub Actions run builds a separately named candidate SCORM, executes a fixed baseline-versus-candidate question suite, and publishes the candidate plus JSON/Markdown reports as a downloadable workflow artifact. Generated packages and reports are not committed automatically.

This experiment tests retrieval coverage only. It does not provide generative multi-passage synthesis or establish Chatbase equivalence. The candidate should be reviewed before importing it into a separate LMS test course.
