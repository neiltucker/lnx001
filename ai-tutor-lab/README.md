# LNX-001 AI Tutor Lab — Version 3

This lab is isolated to the `ai-tutor-lab/full-course-knowledge-v1` branch in this repository. No Courseware Studio files are changed; the original SCORM ZIP is never overwritten.

Version 1 tested adding the complete learner-facing course HTML, Quick Reference Guide HTML, and only the pre/post instructor answer-key Q&A from the Trainer Preparation Guide. Version 2 improved indexing by prioritizing exact paths, IP addresses, identifiers, and inline code, and by giving generic procedure passages more descriptive titles.

Version 3 keeps those knowledge-source rules and adds one experimental change to the candidate's embedded JavaScript only: an IDF-weighted query-coverage penalty intended to discourage answers that score highly on general words but omit a distinctive query term. The original package's tutor.js is the baseline; only the candidate receives this ranking patch. No hosted inference, WebAssembly, external request, or new runtime dependency is introduced.

The workflow compares baseline and candidate against fixed Linux course questions, publishes the new SCORM package and reports as an artifact, and does not commit generated ZIPs/reports. Review the per-question answers and any regressions before importing this candidate into a separate LMS test course.
