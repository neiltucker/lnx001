# LNX-001 AI Tutor Lab — Version 5

The lab remains isolated to `ai-tutor-lab/full-course-knowledge-v1`. No Courseware Studio files are changed, and the original SCORM ZIP is never overwritten.

V5 retains the course-wide knowledge pack, technical metadata, and lab-only IDF-weighted query-coverage patch validated in V4. It makes one targeted indexing correction: the generated "address verification command" query anchor is no longer inferred merely from the presence of generic "display/output" wording. A passage must contain a meaningful verification, inspection, or show reference.

GitHub Actions rebuilds a separate candidate ZIP, reruns the same baseline comparison, and publishes the package and report as an artifact. No generated package is committed automatically. The experiment still uses prepared answers rather than a generative local model.
