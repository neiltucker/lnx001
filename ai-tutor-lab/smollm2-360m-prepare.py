#!/usr/bin/env python3
"""Prepare a reproducible SmolLM2-360M pure-JavaScript inference experiment."""
import hashlib, json, re, urllib.request, zipfile
from pathlib import Path

ROOT = Path.cwd()
CACHE = ROOT / "ai-tutor-lab" / "smollm2-360m-cache"
V6_ZIP = ROOT / "LNX-001_EN_SCORM2004_AI-TUTOR-LAB-V6-LOCAL-LLM.zip"
OUT_ZIP = ROOT / "LNX-001_EN_SCORM2004_AI-TUTOR-LAB-V9-SMOLLM2-360M.zip"
MANIFEST_PATH = ROOT / "ai-tutor-lab" / "smollm2-360m-manifest.json"
MODEL_REPO = "unsloth/SmolLM2-360M-Instruct-GGUF"
MODEL_FILE = "SmolLM2-360M-Instruct-Q4_K_M.gguf"
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
    # llama3pure's default fast path uses greedy matching and skips GGUF BPE merges.
    # SmolLM2 uses GPT-2 byte-level BPE, so load and apply its embedded merge ranks.
    patched = patched.replace('  "tokenizer.ggml.merges": true,\n', "")
    patched = patched.replace('  "tokenizer.ggml.pre": true,\n', "")
    tokenizer_anchor = '    specialTokens: {},'
    tokenizer_replacement = '    preTokenizer: meta["tokenizer.ggml.pre"] || "",\n    mergeRefs: meta["tokenizer.ggml.merges"] || null,\n    mergeRanks: null,\n    specialTokens: {},'
    if patched.count(tokenizer_anchor) != 1:
        raise RuntimeError("Could not find tokenizer configuration object for GPT-2 BPE metadata")
    patched = patched.replace(tokenizer_anchor, tokenizer_replacement, 1)

    gpt2_bpe_helpers = r'''function buildSmolLM2MergeRanks() {
  if (tokenizer.mergeRanks) {
    return
  }
  var refs = tokenizer.mergeRefs
  if (!refs || !refs.__stringRefs) {
    throw new Error("SmolLM2 GGUF is missing tokenizer.ggml.merges")
  }
  var ranks = Object.create(null)
  var p = refs.vocabOffset
  var dv = dataView
  for (var i = 0; i < refs.vocabCount; i = i + 1) {
    var len = dv.getUint32(p, true)
    var merge = decodeUTF8(ggufUint8.subarray(p + 8, p + 8 + len))
    ranks[merge] = i
    p = p + 8 + len
  }
  tokenizer.mergeRanks = ranks
}

function bpeEncodeSmolLM2(text) {
  buildVocabHash()
  buildSmolLM2MergeRanks()
  // GPT-2 ByteLevel pre-tokenizer pattern, preserving every source character.
  var chunks = text.match(/'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+/giu) || []
  if (chunks.join("") !== text) {
    throw new Error("SmolLM2 GPT-2 pre-tokenizer did not preserve the full prompt")
  }
  var tokens = []
  var ranks = tokenizer.mergeRanks
  for (var c = 0; c < chunks.length; c = c + 1) {
    var mapped = textToTiktoken(chunks[c])
    var parts = Array.from(mapped)
    for (;;) {
      var bestRank = Infinity
      var bestIndex = -1
      for (var j = 0; j + 1 < parts.length; j = j + 1) {
        var rank = ranks[parts[j] + " " + parts[j + 1]]
        if (rank !== undefined && rank < bestRank) {
          bestRank = rank
          bestIndex = j
        }
      }
      if (bestIndex < 0) {
        break
      }
      parts[bestIndex] = parts[bestIndex] + parts[bestIndex + 1]
      parts.splice(bestIndex + 1, 1)
    }
    for (var t = 0; t < parts.length; t = t + 1) {
      var bytes = encodeStringToUTF8(parts[t])
      var tokenId = vocabLongestMatch(bytes, 0, bytes.length)
      if (tokenId < 0 || tokenizer.vocabLengths[tokenId] !== bytes.length) {
        throw new Error("SmolLM2 BPE piece is absent from the GGUF vocabulary")
      }
      tokens.push(tokenId)
    }
  }
  return tokens
}

'''
    bpe_anchor = "function bpeEncode(text) {\n"
    bpe_branch = 'function bpeEncode(text) {\n  if (!config.isGemma && tokenizer.mergeRefs && /gpt-2|gpt2|smollm/i.test(tokenizer.preTokenizer)) {\n    return bpeEncodeSmolLM2(text)\n  }\n'
    if patched.count(bpe_anchor) != 1:
        raise RuntimeError("Could not find bpeEncode anchor for model-specific tokenizer")
    patched = patched.replace(bpe_anchor, gpt2_bpe_helpers + bpe_branch, 1)

    loaded_anchor = '        postMessage({\n          type: "loaded",\n        })'
    loaded_replacement = '        postMessage({\n          type: "loaded",\n          preTokenizer: tokenizer.preTokenizer,\n          mergeCount: tokenizer.mergeRefs && tokenizer.mergeRefs.__stringRefs ? tokenizer.mergeRefs.vocabCount : 0,\n          eosToken: tokenizer.eosToken,\n          eotToken: tokenizer.eotToken,\n        })'
    if patched.count(loaded_anchor) != 1:
        raise RuntimeError("Could not find model-loaded event for tokenizer diagnostics")
    patched = patched.replace(loaded_anchor, loaded_replacement, 1)
    patched = patched.replace('findSpecialToken("<|eot_id|>")', 'findSpecialToken("<|im_end|>")')
    eos_old = 'if (next === tokenizer.eosToken) {\n        break\n      }'
    eos_new = 'if (next === tokenizer.eosToken) {\n        postMessage({ type: "stop-debug", stop: "eos", nextToken: next, eosToken: tokenizer.eosToken, eotToken: tokenizer.eotToken })\n        break\n      }'
    eot_old = 'if (next === tokenizer.eotToken) {\n        break\n      }'
    eot_new = 'if (next === tokenizer.eotToken) {\n        postMessage({ type: "stop-debug", stop: "eot", nextToken: next, eosToken: tokenizer.eosToken, eotToken: tokenizer.eotToken })\n        break\n      }'
    if patched.count(eos_old) != 1 or patched.count(eot_old) != 1:
        raise RuntimeError("Could not find exactly one EOS and EOT stopping branch for diagnostics")
    patched = patched.replace(eos_old, eos_new, 1)
    patched = patched.replace(eot_old, eot_new, 1)

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
        "weights_quantization": "Q4_K_M",
        "tokenizer_strategy": "GGUF-embedded GPT-2 byte-level BPE merge ranks when metadata reports GPT-2/SmolLM tokenizer"
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
