# LNX-001 AI Tutor Lab — Local Inference Feasibility Findings (V6/V7)

## Scope and safeguards

This report records experiments performed only on the `ai-tutor-lab/full-course-knowledge-v1` branch of `neiltucker/lnx001`. No files, settings, or deployments in Courseware Studio were changed. The `main` branch was not changed; all candidate SCORM packages were created as GitHub Actions artifacts, not committed over the source package.

The candidate retains the course-wide knowledge corpus from V1–V5: readable lesson HTML in the SCORM package, the learner-facing Quick Reference Guide HTML, and only the pre/post instructor answer-key Q&A from the Trainer Preparation Guide. The guide’s Module Q&A Reference and other instructor-only material are excluded.

## Experiment A — Retrieval baseline (V5 data and ranking)

GitHub Actions run: https://github.com/neiltucker/lnx001/actions/runs/38105670109

- Existing tutor passed 14 of 20 deterministic retrieval checks.
- Expanded knowledge + lab-only query-coverage ranking passed 19 of 20.
- Five questions improved, zero test regressions, one retrieval miss remained.
- This only tested whether a prepared record was selected and contained expected terms. It did not test generated answers or Chatbase-equivalent behavior.

## Experiment B — Local JavaScript LLM with course retrieval (V6)

GitHub Actions run: https://github.com/neiltucker/lnx001/actions/runs/38106364063

Pinned runtime/model: Gab 100M Q8, pure JavaScript CPU, no WebAssembly, no hosted model API. Approximate weight file size: 100,334,656 bytes. The model and runtime were packaged in a separate SCORM candidate; the primary tutor chat UI was not switched to use the model.

Result: **0 of 3 generated answers passed the expected-fact checks.**

| Query | Prompt tokens | Generation latency | Result |
|---|---:|---:|---|
| Directory execute permission | 718 | 94.4 seconds | Partly correct idea, but missed the expected traversal/search explanation |
| Exact SSH hardening file/directive | 839 | 115.1 seconds | Incomplete answer; did not provide the required filename/directive |
| UFW remote-access safety | 714 | 96.9 seconds | Incorrect/risky answer: it advised enabling UFW instead of first allowing SSH/OpenSSH |

The model was therefore too slow for normal tutor interaction in this CPU test and did not reliably follow the grounding instructions. The failure on the UFW question is especially important because an instructional tutor must not return unsafe or misleading technical guidance.

## Experiment C — Reduced one-question smoke test (V7)

GitHub Actions run: https://github.com/neiltucker/lnx001/actions/runs/38106570010

The workload was reduced to one question, one retrieved evidence passage, and a 20-token generation limit. It still failed the required factual checks and took 46.8 seconds to generate a short, irrelevant answer fragment.

The GitHub Actions jobs concluded successfully because the harness completed and wrote the result. That status must not be interpreted as a model-quality pass.

## Decision

**Reject Gab 100M Q8 as a production AI Tutor candidate.** The issue is not just prompt construction; the tested model/CPU combination produced insufficiently reliable explanations at unacceptable latency for this use case. It should not be integrated into the primary tutor.

The JS-based course-wide retrieval architecture is still useful and validated as a direction. However, the current evidence does **not** support the stronger goal of Chatbase-like generative quality while simultaneously requiring:

- all knowledge bundled in the SCORM package;
- no hosted inference service;
- pure JavaScript inference with no WebAssembly;
- broad LMS/browser compatibility.

These constraints are in tension. A larger local model may improve answer quality but usually increases package size and compute requirements. WebGPU could improve performance on supported hardware, but its availability varies by browser and LMS embedding environment. A hosted model endpoint offers the most direct route to Chatbase-like answers but would relax the no-hosted-inference constraint.

## Recommended next experiment

Continue on this repository branch only. Keep the V5 course-wide knowledge pack, then compare two separate approaches:

1. **Strict offline / pure-JS fallback:** improve deterministic multi-passage answer composition, exact technical-value preservation, and explicit insufficient-evidence responses. This keeps compatibility, but should not be marketed as equivalent to Chatbase.
2. **Higher-quality generation trial:** only if you authorize revisiting either the no-WebAssembly or no-hosted-inference constraint, prototype an alternate local GPU runtime or model endpoint in a separate branch/test configuration and compare answer quality, latency, compatibility and package size.

No production change should be proposed until the selected approach passes a representative question set and a separate LMS launch/import test. No Courseware Studio change is authorized by this finding.
