'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {performance}=require('node:perf_hooks');
const Rag=require('./ai-tutor-lab/local-model-rag.js');
const cache=path.join(process.cwd(),'ai-tutor-lab','model-cache'),work='/tmp/lnx001-ai-tutor-lab';
function loadBundle(){
 const src=fs.readFileSync(path.join(work,'candidate','tutor-data.js'),'utf8'),w={};
 vm.runInNewContext(src,{window:w,console});
 if(!w.__CS_AI_TUTOR_DATA__)throw new Error('Candidate tutor data not found');
 return w.__CS_AI_TUTOR_DATA__;
}
async function main(){
 for(const file of ['inference.js','model-q8.json','model-q8.bin','tokenizer.json','LICENSE'])if(!fs.existsSync(path.join(cache,file)))throw new Error('Missing local model asset: '+file);
 global.requestAnimationFrame=cb=>setTimeout(()=>cb(performance.now()),0);
 require(path.join(cache,'inference.js'));
 const manifest=JSON.parse(fs.readFileSync(path.join(cache,'model-q8.json'),'utf8'));
 const vocab=JSON.parse(fs.readFileSync(path.join(cache,'tokenizer.json'),'utf8'));
 const tokenizer=new global.GabTokenizer(vocab),wb=fs.readFileSync(path.join(cache,'model-q8.bin'));
 const weightsBuffer=wb.buffer.slice(wb.byteOffset,wb.byteOffset+wb.byteLength),contextLimit=manifest.architecture.max_position_embeddings||2048;
 const t0=performance.now(),engine=await global.GabInferenceEngine.create({manifest,weightsBuffer,tokenizer,maxContext:768}),loadMs=Math.round(performance.now()-t0);
 const bundle=loadBundle(),concepts=bundle.concepts;
 if(!Array.isArray(concepts)||concepts.length<300)throw new Error('Candidate course knowledge incomplete: '+(concepts||[]).length);
 const cases=[
  {id:'directory-execute',question:'Why does a user need execute permission on a directory to use cd?',patterns:[/execute/i,/director/i,/traversal|search/i]},
  {id:'ssh-root-hardening',question:'Which exact SSH configuration file and directive in this course disable direct root SSH login?',patterns:[/99-hardening\.conf/i,/PermitRootLogin\s+no/i]},
  {id:'ufw-remote-ssh',question:'What should I do before enabling UFW on a remote server so that I do not lock myself out of SSH?',patterns:[/ufw\s+allow/i,/OpenSSH|22\/tcp/i]}
 ];
 const results=[];
 for(const test of cases){
  const started=performance.now(),ranked=Rag.rank(test.question,concepts,{topK:3}),prompt=Rag.buildPrompt(test.question,ranked,[]),promptTokens=tokenizer.encode(prompt).length;
  if(promptTokens>=768-64)throw new Error(test.id+' prompt too long: '+promptTokens);
  let response='';
  for await(const event of engine.generate([{role:'user',text:prompt}],{maxNewTokens:48,temperature:0,topK:1,thinking:false}))if(event.kind==='response')response+=event.token.text;
  response=response.replace(/<\|end\|>|<\|endoftext\|>/g,'').trim();
  const hits=test.patterns.filter(rx=>rx.test(response)).map(String);
  const result={id:test.id,question:test.question,pass:test.patterns.every(rx=>rx.test(response)),prompt_tokens:promptTokens,latency_ms:Math.round(performance.now()-started),retrieved:ranked.map(x=>({title:x.concept.title,module:x.concept.module_title,citation:x.concept.citation,score:Number(x.score.toFixed(3)),coverage:Number(x.coverage.toFixed(3))})),response,required_patterns:test.patterns.map(String),matched_patterns:hits};
  results.push(result);
  console.log('\n[LOCAL MODEL TEST '+test.id+'] '+(result.pass?'PASS':'FAIL'));
  console.log('Question: '+test.question);
  console.log('Retrieved: '+ranked.map(x=>x.concept.title).join(' | '));
  console.log('Prompt tokens: '+promptTokens+'; generation latency: '+result.latency_ms+' ms');
  console.log('Answer: '+response);
 }
 const out={experiment:'local-js-generation-poc-v1',runtime:'Gab 100M Q8 pure-JavaScript CPU inference; no WebAssembly; no hosted AI inference',model:{name:'Gab 100M Q8',source_revision:'339be056d94f5615e7764f2ce3c8e67667dcabbb',weights_bytes:wb.byteLength,context_limit:contextLimit,load_ms:loadMs,tokenizer_vocab_entries:vocab.merges.length},knowledge_concepts:concepts.length,test_count:results.length,pass_count:results.filter(x=>x.pass).length,fail_count:results.filter(x=>!x.pass).length,results,limitations:['Small 100M-parameter model; answer quality must be measured rather than assumed.','This does not establish cross-LMS launch behavior.','Normal tutor UI is not switched to local generation in this experiment.']};
 fs.writeFileSync('ai-tutor-lab/local-model-results.json',JSON.stringify(out,null,2));
 console.log('\n[LOCAL MODEL SUMMARY]\n'+JSON.stringify({load_ms:loadMs,weights_bytes:wb.byteLength,test_count:out.test_count,pass_count:out.pass_count,fail_count:out.fail_count,results:results.map(x=>({id:x.id,pass:x.pass,latency_ms:x.latency_ms,prompt_tokens:x.prompt_tokens}))},null,2));
}
main().catch(e=>{console.error(e&&e.stack||e);process.exitCode=1;});
