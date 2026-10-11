#!/usr/bin/env python3
"""Prepare a reproducible SmolLM2-135M pure-JavaScript inference experiment."""
import hashlib, json, re, urllib.request, zipfile
from pathlib import Path

ROOT = Path.cwd()
CACHE = ROOT / "ai-tutor-lab" / "smollm2-cache"
V6_ZIP = ROOT / "LNX-001_EN_SCORM2004_AI-TUTOR-LAB-V6-LOCAL-LLM.zip"
OUT_ZIP = ROOT / "LNX-001_EN_SCORM2004_AI-TUTOR-LAB-V8-SMOLLM2.zip"
MANIFEST_PATH = ROOT / "ai-tutor-lab" / "smollm2-manifest.json"
MODEL_REPO = "bartowski/SmolLM2-135M-Instruct-GGUF"
MODEL_FILE = "SmolLM2-135M-Instruct-Q4_K_M.gguf"
ENGINE_REPO = "lrusso/llama3pure"
ENGINE_COMMIT = "03d2b7d794dfb7501f0106e55eb08bd584a745f6"
UA = {"User-Agent": "LNX001-AITutor-Offline-Model-Experiment/1.0"}

def request_bytes(url, timeout=240):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()

def download_to(url, path, timeout=600):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".download")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp, tmp.open("wb") as out:
        while True:
            block = resp.read(1024 * 1024)
            if not block:
                break
            out.write(block)
    tmp.replace(path)

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def download_assets():
    CACHE.mkdir(parents=True, exist_ok=True)
    info = json.loads(request_bytes(f"https://huggingface.co/api/models/{MODEL_REPO}", 60))
    model_revision = info.get("sha")
    if not model_revision or not re.fullmatch(r"[0-9a-f]{40}", model_revision):
        raise RuntimeError("Hugging Face model metadata did not provide a commit SHA")
    model_path = CACHE / MODEL_FILE
    revision_file = CACHE / "model-source.json"
    cached_revision = None
    if revision_file.exists():
        try:
            cached_revision = json.loads(revision_file.read_text(encoding="utf-8")).get("revision")
        except Exception:
            cached_revision = None
    if not model_path.exists() or model_path.stat().st_size < 50_000_000 or cached_revision != model_revision:
        url = f"https://huggingface.co/{MODEL_REPO}/resolve/{model_revision}/{MODEL_FILE}"
        print(f"Downloading {MODEL_REPO}@{model_revision}: {MODEL_FILE}")
        download_to(url, model_path)
        if model_path.stat().st_size < 50_000_000:
            raise RuntimeError(f"GGUF download unexpectedly small: {model_path.stat().st_size}")
        with model_path.open("rb") as f:
            if f.read(4) != b"GGUF":
                raise RuntimeError("Downloaded model file does not start with GGUF magic")
        revision_file.write_text(json.dumps({"repo": MODEL_REPO, "revision": model_revision, "file": MODEL_FILE}, indent=2), encoding="utf-8")
    else:
        print(f"Using cached model revision {model_revision}")

    engine_path = CACHE / "llama3pure-js-engine.upstream.js"
    engine_url = f"https://raw.githubusercontent.com/{ENGINE_REPO}/{ENGINE_COMMIT}/llama3pure-js-engine.js"
    if not engine_path.exists():
        print(f"Downloading pure-JS engine from {ENGINE_REPO}@{ENGINE_COMMIT}")
        download_to(engine_url, engine_path, 120)
    original = engine_path.read_text(encoding="utf-8")
    if "module.exports = llama3pure" not in original or "function encodeLlama3Chat(chatHistory, sysPrompt)" not in original:
        raise RuntimeError("Pinned pure-JavaScript engine source did not match expected API")

    # SmolLM2 uses the ChatML tokens rather than the Llama 3 header tokens.
    start = original.index("function encodeLlama3Chat(chatHistory, sysPrompt) {")
    end = original.index("function encodeGemma3Chat(chatHistory, sysPrompt) {", start)
    replacement = r'''function encodeLlama3Chat(chatHistory, sysPrompt) {
  var tokens = []
  var startMessage = findSpecialToken("<|im_start|>")
  var endMessage = findSpecialToken("<|im_end|>")
  if (startMessage < 0 || endMessage < 0) {
    throw new Error("SmolLM2 ChatML special tokens are missing from this GGUF model")
  }
  function append(values) {
    for (var i = 0; i < values.length; i = i + 1) tokens.push(values[i])
  }
  function appendMessage(role, content) {
    tokens.push(startMessage)
    append(bpeEncode(role + "\n" + content))
    tokens.push(endMessage)
    append(bpeEncode("\n"))
  }
  if (sysPrompt && sysPrompt.length > 0) appendMessage("system", sysPrompt)
  for (var m = 0; m < chatHistory.length; m = m + 1) {
    var role = chatHistory[m].role || "user"
    if (role === "model") role = "assistant"
    appendMessage(role, chatHistory[m].content || "")
  }
  tokens.push(startMessage)
  append(bpeEncode("assistant\n"))
  return tokens
}

'''
    patched = original[:start] + replacement + original[end:]
    patched = patched.replace('findSpecialToken("<|eot_id|>")', 'findSpecialToken("<|im_end|>")')
    old = "var effectiveMaxTokens = maxTokens"
    if patched.count(old) != 1:
        raise RuntimeError("Could not find the expected generation-limit anchor in the JS engine")
    # In this benchmark maxTokens is the total context size in the upstream engine.
    # Bound new output to 48 tokens so answer checks have a consistent latency ceiling.
    patched = patched.replace(old, "var effectiveMaxTokens = Math.min(maxTokens, numPromptTokens + 48)", 1)
    engine_patched_path = CACHE / "llama3pure-smollm2.js"
    engine_patched_path.write_text(patched, encoding="utf-8")

    engine_license = CACHE / "LICENSE-llama3pure.txt"
    if not engine_license.exists():
        download_to(f"https://raw.githubusercontent.com/{ENGINE_REPO}/{ENGINE_COMMIT}/LICENSE", engine_license, 120)
    model_license = CACHE / "LICENSE-SMOLLM2-Apache-2.0.txt"
    if not model_license.exists():
        download_to("https://www.apache.org/licenses/LICENSE-2.0.txt", model_license, 120)
    return {
        "model_repo": MODEL_REPO, "model_revision": model_revision, "model_file": MODEL_FILE,
        "model_bytes": model_path.stat().st_size, "model_sha256": sha256_file(model_path),
        "engine_repo": ENGINE_REPO, "engine_revision": ENGINE_COMMIT,
        "engine_upstream_sha256": sha256_file(engine_path),
        "engine_patched_sha256": sha256_file(engine_patched_path),
        "engine_license": "MIT", "model_license": "Apache-2.0",
        "runtime": "pure JavaScript CPU inference; no WebAssembly; no hosted inference",
        "chat_template_patch": "SmolLM2 ChatML special tokens and im_end stopping",
        "generation_limit_tokens": 48,
        "weights_quantization": "Q4_K_M"
    }

def build_candidate(model_info):
    if not V6_ZIP.exists():
        raise FileNotFoundError(f"Expected prior candidate package not found: {V6_ZIP}")
    model_path = CACHE / MODEL_FILE
    engine_path = CACHE / "llama3pure-smollm2.js"
    engine_license = CACHE / "LICENSE-llama3pure.txt"
    model_license = CACHE / "LICENSE-SMOLLM2-Apache-2.0.txt"
    rag_path = ROOT / "ai-tutor-lab" / "local-model-rag.js"
    replacements = {
        "ai-tutor/local-model/llama3pure-js-engine.js": engine_path,
        f"ai-tutor/local-model/{MODEL_FILE}": model_path,
        "ai-tutor/local-model/LICENSE-llama3pure.txt": engine_license,
        "ai-tutor/local-model/LICENSE-SMOLLM2-Apache-2.0.txt": model_license,
        "ai-tutor/local-model/rag.js": rag_path
    }
    old_gab = {
        "ai-tutor/local-model/inference.js", "ai-tutor/local-model/model-q8.json",
        "ai-tutor/local-model/model-q8.bin", "ai-tutor/local-model/tokenizer.json",
        "ai-tutor/local-model/LICENSE", "ai-tutor/local-model-demo.html"
    }
    with zipfile.ZipFile(V6_ZIP, "r") as zin, zipfile.ZipFile(OUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=5) as zout:
        bad = zin.testzip()
        if bad:
            raise RuntimeError(f"Existing candidate archive failed integrity test at {bad}")
        for entry in zin.infolist():
            if entry.filename in old_gab or entry.filename.startswith("ai-tutor/local-model/"):
                continue
            zout.writestr(entry, zin.read(entry.filename))
        for archive_path, source_path in replacements.items():
            zi = zipfile.ZipInfo(archive_path)
            zi.external_attr = 0o100644 << 16
            zi.compress_type = zipfile.ZIP_STORED if archive_path.endswith(".gguf") else zipfile.ZIP_DEFLATED
            with source_path.open("rb") as f:
                zout.writestr(zi, f.read())
    with zipfile.ZipFile(OUT_ZIP, "r") as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError(f"SmolLM2 candidate archive failed integrity test at {bad}")
        names = z.namelist()
        for path in replacements:
            if path not in names:
                raise RuntimeError(f"SmolLM2 candidate archive missing {path}")
    model_info.update({
        "candidate_package": OUT_ZIP.name,
        "candidate_package_bytes": OUT_ZIP.stat().st_size,
        "candidate_package_sha256": sha256_file(OUT_ZIP),
        "candidate_changed_assets": list(replacements),
        "primary_tutor_switched_to_generation": False,
        "original_source_package_modified": False
    })
    MANIFEST_PATH.write_text(json.dumps(model_info, indent=2), encoding="utf-8")
    print(json.dumps(model_info, indent=2))

if __name__ == "__main__":
    info = download_assets()
    build_candidate(info)
