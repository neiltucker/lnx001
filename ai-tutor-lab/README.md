# LNX-001 AI Tutor Lab — Local JS Generation POC

All work remains on `ai-tutor-lab/full-course-knowledge-v1`; Courseware Studio is not modified, and the original SCORM archive is not overwritten.

V1–V5 tested course-wide knowledge ingestion and retrieval. V6 is the first local-generation feasibility experiment. It pins the MIT-licensed Gab 100M Q8 model assets from public repository `gszauer/Gab`, packages the pure-JavaScript CPU runtime and approximately 100 MB quantized weights into a separate SCORM candidate, and tests generated answers grounded in passages retrieved from the LNX-001 knowledge bundle.

Constraints: no hosted inference, no runtime network requests, no WebAssembly, and no external database. GitHub Actions downloads fixed-revision model assets at build time; those assets are included in the candidate ZIP. The original tutor remains available; a separate local-model demo page is included but the primary tutor UI is not switched to local generation yet.

Actions results include the baseline retrieval comparison, each generated model answer, retrieved passages, prompt size, latency and expected-fact checks. This is a feasibility experiment, not a claim that a 100M-parameter model is equivalent to Chatbase. Do not promote the model or modify Courseware Studio based on this first test alone.
