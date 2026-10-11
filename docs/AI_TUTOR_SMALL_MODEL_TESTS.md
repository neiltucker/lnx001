# Offline JavaScript AI Tutor — Small Model Evaluation

## Constraints

All experiments are limited to GitHub repository [`neiltucker/lnx001`](https://github.com/neiltucker/lnx001), branch `ai-tutor-lab/full-course-knowledge-v1`. Tests must keep inference offline, use JavaScript only, avoid WebAssembly, package course knowledge into the SCORM archive, and avoid changing the Courseware Studio repository or its production package.

## Model 1: SmolLM2-135M-Instruct

- GitHub Actions run: [38108416690](https://github.com/neiltucker/lnx001/actions/runs/38108416690)
- Model snapshot: `bartowski/SmolLM2-135M-Instruct-GGUF`, revision `09816acd5d99df7be770d85ea30822623dab342c`
- Quantization: Q4_K_M; model bytes: 105,454,432
- Inference runtime: pure-JavaScript CPU, pinned `lrusso/llama3pure` revision `03d2b7d794dfb7501f0106e55eb08bd584a745f6`, with GGUF GPT-2/SmolLM merge-rank tokenization added. No WebAssembly or hosted inference.
- Candidate SCORM: `LNX-001_EN_SCORM2004_AI-TUTOR-LAB-V8-SMOLLM2.zip` (114,998,551 bytes).
- The production tutor and original source SCORM were not modified.

### Results

| Test | Latency | Result |
|---|---:|---|
| SSH root-login directive and exact drop-in filename | 74.1 s | Fail — omitted both `99-hardening.conf` and `PermitRootLogin no` |
| Linux directory execute permission | 45.7 s | Fail — did not explain traversal/search access |
| Safe order for enabling UFW over SSH | 50.2 s | Fail — gave `sudo ufw allow OpenSSH` but did not complete the procedure |

**Result: 0/3 technical checks passed; 45.7–74.1 seconds per response.** The initial empty-output tests were caused by tokenizer/runtime incompatibility and were not scored as model-quality results. After adding the GGUF merge ranks, the model emitted text but remained too slow and inaccurate for this application.

This is a measured result from GitHub Actions on a Node.js CPU runner. It is not a browser/LMS benchmark. Full details are stored in `ai-tutor-lab/smollm2-135m-results.json`.

## Next in sequence: SmolLM2-360M-Instruct

The next experiment uses the Q4_K_M GGUF published by Unsloth (approximately 271 MB per repository metadata), the same corrected tokenizer approach, corpus, three questions, and 48-token response cap. The larger weights may increase both package size and latency; GitHub Actions will determine whether answer quality improves enough to justify those costs.

## Guardrails

No model is integrated into the primary tutor UI based on these tests alone. All output remains a candidate artifact. Do not change `main`, the original course ZIP, or Courseware Studio without explicit permission.
