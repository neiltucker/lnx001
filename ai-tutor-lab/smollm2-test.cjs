'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { performance } = require('node:perf_hooks');
const Rag = require('./local-model-rag.js');

const ROOT = process.cwd();
const CACHE = path.join(ROOT, 'ai-tutor-lab', 'smollm2-cache');
const MODEL_FILE = 'SmolLM2-135M-Instruct-Q4_K_M.gguf';
const PACKAGE = path.join(ROOT, 'LNX-001_EN_SCORM2004_AI-TUTOR-LAB-V8-SMOLLM2.zip');
const DATA_FILE = '/tmp/lnx001-ai-tutor-lab/candidate/tutor-data.js';

function loadCourseData() {
  const source = fs.readFileSync(DATA_FILE, 'utf8');
  const w = {};
  require('node:vm').runInNewContext(source, { window: w, console });
  const bundle = w.__CS_AI_TUTOR_DATA__;
  if (!bundle || !Array.isArray(bundle.concepts) || bundle.concepts.length < 300) {
    throw new Error('Full packaged course knowledge corpus is missing or incomplete');
  }
  return bundle;
}
function checkPatterns(response, patterns) {
  return patterns.map((pattern) => ({ pattern: String(pattern), pass: pattern.test(response) }));
}
function makeTests() {
  return [
    {
      id: 'ssh-root-hardening',
      question: 'Which exact SSH configuration file and directive disable direct root login?',
      patterns: [/99-hardening\.conf/i, /PermitRootLogin\s+no/i]
    },
    {
      id: 'directory-execute-permission',
      question: 'What does execute permission on a Linux directory allow a user to do?',
      patterns: [/\b(directory|directory's)\b/i, /\b(travers|search)\w*/i]
    },
    {
      id: 'ufw-remote-access-safety',
      question: 'What should I do before enabling UFW on a remote Linux server to avoid locking out my SSH session?',
      patterns: [/ufw\s+allow\s+(openssh|ssh)|allow\s+(openssh|ssh)/i, /ufw\s+enable/i],
      ordered: true
    }
  ];
}
async function main() {
  const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, 'ai-tutor-lab', 'smollm2-manifest.json'), 'utf8'));
  const modelPath = path.join(CACHE, MODEL_FILE);
  const enginePath = path.join(CACHE, 'llama3pure-smollm2.js');
  if (!fs.existsSync(modelPath) || !fs.existsSync(enginePath)) throw new Error('Prepared SmolLM2 model/runtime assets are missing');
  const engineSource = fs.readFileSync(enginePath, 'utf8');
  if (/WebAssembly|\.wasm\b/i.test(engineSource)) throw new Error('The selected inference runtime unexpectedly references WebAssembly');

  const engineEvents = [];
  let completeOutput = '';
  global.self = { postMessage(message) {
    engineEvents.push(message);
    if (message && message.type === 'complete') completeOutput = message.output || '';
  }};
  const llama3pure = require(enginePath);
  const w = fs.readFileSync(modelPath);
  const modelBuffer = w.buffer.slice(w.byteOffset, w.byteOffset + w.byteLength);
  const course = loadCourseData();
  const tests = makeTests();

  const loadStart = performance.now();
  llama3pure({
    type: 'load',
    model: modelBuffer,
    systemPrompt: 'You are a technical course tutor. Use the provided course evidence. Preserve exact paths, commands, and directives. Do not invent facts. If the evidence is insufficient, say so. Answer concisely.',
    maxTokens: 1024,
    contextSize: 1024,
    temperature: 0,
    topP: 1,
    topK: 1,
    cbRender: () => {}
  });
  const loadMs = Math.round(performance.now() - loadStart);
  if (!engineEvents.some(e => e && e.type === 'loaded')) {
    throw new Error('Pure-JS engine did not emit its loaded event; inspect the run log for model incompatibility');
  }

  const results = [];
  for (const test of tests) {
    const ranked = Rag.rank(test.question, course.concepts, { topK: 3 });
    const prompt = Rag.buildPrompt(test.question, ranked, []);
    completeOutput = '';
    const eventsStart = engineEvents.length;
    const genStart = performance.now();
    llama3pure({
      type: 'generate',
      chatHistory: [{ role: 'user', content: prompt }]
    });
    const latencyMs = Math.round(performance.now() - genStart);
    const emittedEvents = engineEvents.slice(eventsStart);
    const tokenChunks = emittedEvents.filter(e => e && e.type === 'token').map(e => String(e.token || ''));
    const stopDebug = emittedEvents.find(e => e && e.type === 'stop-debug') || null;
    const completeEvent = emittedEvents.find(e => e && e.type === 'complete') || null;
    const response = String(completeOutput || tokenChunks.join('') || '').replace(/<\|im_end\|>|<\|endoftext\|>/g, '').trim();
    const checks = checkPatterns(response, test.patterns);
    let sequencePass = true;
    if (test.ordered) {
      const allowAt = response.search(/ufw\s+allow\s+(openssh|ssh)|allow\s+(openssh|ssh)/i);
      const enableAt = response.search(/ufw\s+enable/i);
      sequencePass = allowAt >= 0 && enableAt >= 0 && allowAt < enableAt;
    }
    results.push({
      id: test.id, question: test.question,
      pass: checks.every(c => c.pass) && sequencePass,
      checks, ordered_check: test.ordered ? { pass: sequencePass, description: 'Allow SSH/OpenSSH before enabling UFW' } : null,
      response, prompt_chars: prompt.length, prompt_source_count: ranked.length,
      engine_diagnostics: { event_types: emittedEvents.map(e => e && e.type).filter(Boolean), token_event_count: tokenChunks.length, first_tokens: tokenChunks.slice(0, 12), stop: stopDebug, complete_output_length: completeEvent && typeof completeEvent.output === 'string' ? completeEvent.output.length : null },
      retrieved: ranked.map(x => ({ title: x.concept.title, module: x.concept.module_title, citation: x.concept.citation, score: Number(x.score.toFixed(3)) })),
      latency_ms: latencyMs, response_words: response ? response.split(/\s+/).length : 0
    });
    console.log('\n[SMOLLM2 TEST ' + test.id + '] ' + (results[results.length - 1].pass ? 'PASS' : 'FAIL'));
    console.log('Question: ' + test.question);
    console.log('Response latency: ' + latencyMs + ' ms');
    console.log('Retrieved: ' + ranked.map(x => x.concept.title).join(' | '));
    console.log('Answer: ' + response);
    console.log('Engine diagnostics: ' + JSON.stringify(results[results.length - 1].engine_diagnostics));
    console.log('Checks: ' + JSON.stringify(checks) + (test.ordered ? '; ordered=' + sequencePass : ''));
  }
  const result = {
    experiment: 'smollm2-135m-instruct-pure-js-v1',
    runtime: 'llama3pure JavaScript CPU; no WebAssembly; no hosted inference',
    source: manifest,
    course_knowledge_concepts: course.concepts.length,
    runtime_load_ms: loadMs,
    context_size: 1024,
    max_new_tokens: 48,
    test_count: results.length,
    pass_count: results.filter(x => x.pass).length,
    fail_count: results.filter(x => !x.pass).length,
    results,
    qualifications: [
      'These are deterministic keyword/fact checks, not a human evaluation of overall answer quality.',
      'GitHub Actions CPU latency is a comparison point, not a guarantee for a learner browser.',
      'The primary SCORM tutor UI remains unchanged; the model is packaged as a separate candidate asset.',
      'Only the test harness and candidate package were created. The original course ZIP and main branch were not modified.'
    ]
  };
  fs.writeFileSync(path.join(ROOT, 'ai-tutor-lab', 'smollm2-results.json'), JSON.stringify(result, null, 2));
  console.log('\n[SMOLLM2 SUMMARY]\n' + JSON.stringify({
    runtime_load_ms: loadMs, package_bytes: fs.statSync(PACKAGE).size,
    model_bytes: w.byteLength, test_count: result.test_count, pass_count: result.pass_count,
    fail_count: result.fail_count,
    results: results.map(x => ({ id: x.id, pass: x.pass, latency_ms: x.latency_ms, response_words: x.response_words }))
  }, null, 2));
}
main().catch(e => { console.error(e && e.stack || e); process.exitCode = 1; });
