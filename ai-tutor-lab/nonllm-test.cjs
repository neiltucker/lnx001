'use strict';
const fs = require('node:fs');
const path = require('node:path');
const NLT = require('./nonllm-tutor.js');
const ROOT = process.cwd();
const WORK = '/tmp/lnx001-ai-tutor-lab/nonllm';
const tests = [
  {id:'qrg-live-log',q:'How can I follow a live system log in real time?',any:[/tail\s+-f/i]},
  {id:'qrg-grep-tail',q:'Find case-insensitive error lines from syslog and show the last 20 matches.',all:[/grep/i,/tail\s+-n\s+20/i]},
  {id:'qrg-append',q:'How do I append new log records without deleting old ones?',any:[/>>/]},
  {id:'qrg-usermod',q:'Add a user to a supplementary group without removing existing memberships.',all:[/usermod/i,/-aG/i]},
  {id:'qrg-mount-uuid',q:'Configure persistent ext4 mounting with UUID.',all:[/UUID/i,/fstab/i]},
  {id:'qrg-process',q:'How should I stop a stuck process gracefully before forcing it?',any:[/SIGTERM/i,/kill\s+-15/i]},
  {id:'qrg-ufw-ssh',q:'What should I allow before enabling UFW on a remote SSH server?',any:[/OpenSSH/i,/ufw\s+allow/i]},
  {id:'pre-assessment-x-dir',q:'What permission lets a user traverse a directory and change into it with cd?',any:[/execute/i,/travers/i]},
  {id:'post-assessment-visudo',q:'Why use visudo instead of editing sudoers with a normal text editor?',all:[/visudo/i,/(syntax validation|validates?.{0,35}syntax)/i]},
  {id:'course-pci',q:'Which Linux command inspects devices connected to PCI buses?',any:[/lspci/i]},
  {id:'course-absolute-path',q:'Explain the difference between absolute and relative filesystem paths.',any:[/absolute path/i,/root directory/i,/forward slash/i]},
  {id:'cross-source-firewall',q:'How can I turn on a firewall without locking myself out of SSH?',any:[/OpenSSH/i,/ufw\s+allow/i]},
  {id:'course-netplan-address',q:'What IP address is configured for labnet0 in the Netplan file?',all:[/192\.168\.200\.10\/24/i,/labnet0/i]},
  {id:'course-netplan-dropin',q:'What path does the lab use for its Netplan static IP configuration file for labnet0?',all:[/90-virtual-lab\.yaml/i,/labnet0/i]},
  {id:'course-sudo-allowed-commands',q:'Which two command paths are allowed by the secadmin sudo drop-in?',all:[/\/usr\/sbin\/ufw status/i,/\/usr\/bin\/ss/i]},
  {id:'course-verify-lab-address',q:'Which command verifies the configured address on the labnet0 dummy interface?',all:[/ip addr show labnet0/i,/192\.168\.200\.10\/24/i]},
  {id:'course-fstab-fields',q:'What six fields go into an /etc/fstab entry for a UUID-based ext4 mount?',all:[/UUID/i,/Mount Point/i,/Filesystem Type/i,/Mount Options/i]},
  {id:'course-yaml-troubleshooting',q:'How should I fix a YAML parsing error in the lab Netplan configuration?',all:[/tab/i,/spaces/i,/90-virtual-lab\.yaml/i]},
  {id:'course-ssh-root-config',q:'In which exact drop-in file does the lab set PermitRootLogin no?',all:[/PermitRootLogin no/i,/99-hardening\.conf/i]},
  {id:'out-of-scope-brakes',q:'How do I replace brake pads on a 2026 Honda Accord?',outside:true},
  {id:'paraphrase-directory-cd',q:'If a user cannot cd into a directory, which directory permission should I check?',any:[/execute/i,/search|travers/i]},
  {id:'paraphrase-append-output',q:'How can command output be added to an existing log file rather than overwriting it?',any:[/>>/]},
  {id:'paraphrase-ssh-root',q:'Which sshd setting prevents direct login as root, and where is it configured?',all:[/PermitRootLogin no/i,/99-hardening\.conf/i]},
  {id:'paraphrase-ufw-safe',q:'Before switching on the firewall remotely, how do I preserve SSH access?',any:[/OpenSSH/i,/ufw\s+allow/i]},
  {id:'paraphrase-visudo',q:'What is the reason for editing sudoers with visudo?',all:[/visudo/i,/(syntax validation|validates?.{0,35}syntax)/i]},
  {id:'paraphrase-groups',q:'How can I add someone to another Linux group and retain their other memberships?',all:[/usermod/i,/-aG/i]}
];
function loadBaseline() {
  const dir=path.join(WORK,'baseline');
  const js=fs.readFileSync(path.join(dir,'tutor.js'),'utf8');
  const data=fs.readFileSync(path.join(dir,'tutor-data.js'),'utf8');
  const w={__CS_AI_TUTOR_ENABLED__:1,__CS_AI_TUTOR_CONFIG__:{moduleNumber:1,totalModules:4,courseTitle:'Linux Administration Essentials',language:'english'},__CS_AI_TUTOR_DATA__:null};
  const doc={readyState:'complete',addEventListener:()=>{},getElementById:()=>null,getElementsByTagName:()=>[],createElement:()=>({appendChild:()=>{},setAttribute:()=>{},addEventListener:()=>{},removeChild:()=>{},querySelectorAll:()=>[],style:{}}),body:{appendChild:()=>{},children:[],style:{}},documentElement:{},querySelector:()=>null};
  const storage={getItem:()=>null,setItem:()=>{},removeItem:()=>{}};
  new Function('mockWindow',data.replace(/\bwindow\./g,'mockWindow.'))(w);
  new Function('window','document','sessionStorage',js)(w,doc,storage);
  const api=w.__CS_AI_TUTOR_API__;
  if(!api||!api.initCorpus||!api.searchConcepts)throw new Error('Original tutor API failed to initialize');
  api.initCorpus();return api;
}
function check(answer,t){
  const category=String(answer&&answer.category||'NO_RESULT'),text=String(answer&&answer.answer||'');
  const patterns=t.all||t.any||[],hits=patterns.filter(rx=>rx.test(text));
  const pass=t.outside?category!=='IN_COURSE':category==='IN_COURSE'&&(t.all?hits.length===patterns.length:hits.length>0);
  return {pass,category,answer:text,matchedPatterns:hits.map(String)};
}
function main(){
  const payload=JSON.parse(fs.readFileSync(path.join(ROOT,'ai-tutor-lab','nonllm-index.json'),'utf8'));
  const index=NLT.createIndex(payload.concepts,payload.generation_rules),baselineApi=loadBaseline(),results=[];
  for(const t of tests){
    let oldResult,newResult,bError=null,cError=null;
    try{oldResult=baselineApi.searchConcepts(t.q)}catch(e){bError=String(e)}
    try{newResult=NLT.answer(t.q,index)}catch(e){cError=String(e)}
    const b=oldResult?check(oldResult,t):{pass:false,category:'TEST_ERROR',answer:'',matchedPatterns:[]};
    const c=newResult?check(newResult,t):{pass:false,category:'TEST_ERROR',answer:'',matchedPatterns:[]};
    results.push({id:t.id,question:t.q,outside:!!t.outside,baseline_pass:b.pass,candidate_pass:c.pass,
      change:!b.pass&&c.pass?'improved':b.pass&&!c.pass?'regressed':b.pass&&c.pass?'both-pass':'both-fail',
      baseline_category:b.category,candidate_category:c.category,baseline_answer:b.answer.slice(0,850),candidate_answer:c.answer.slice(0,1100),
      candidate_intent:newResult&&newResult.intent,candidate_score:newResult&&newResult.score,candidate_coverage:newResult&&newResult.coverage,
      candidate_sources:newResult&&newResult.sources,candidate_ranked:newResult&&newResult.ranked,matched_patterns:c.matchedPatterns,
      errors:{baseline:bError,candidate:cError}});
  }
  const baselinePass=results.filter(x=>x.baseline_pass).length,candidatePass=results.filter(x=>x.candidate_pass).length;
  const result={experiment:'non-llm-algorithmic-poc-v1',test_count:results.length,index_record_count:index.recordCount,
    baseline_pass_count:baselinePass,candidate_pass_count:candidatePass,improved:results.filter(x=>x.change==='improved').length,
    regressed:results.filter(x=>x.change==='regressed').length,both_pass:results.filter(x=>x.change==='both-pass').length,
    both_fail:results.filter(x=>x.change==='both-fail').length,out_of_scope_tests:results.filter(x=>x.outside).length,
    intent_counts:results.reduce((o,x)=>{const k=x.candidate_intent||'error';o[k]=(o[k]||0)+1;return o;},{}),results};
  fs.writeFileSync(path.join(ROOT,'ai-tutor-lab','nonllm-results.json'),JSON.stringify(result,null,2));
  const summary=JSON.parse(fs.readFileSync(path.join(ROOT,'ai-tutor-lab','nonllm-build-summary.json'),'utf8'));
  const md=[
    '# LNX-001 AI Tutor Lab — algorithmic no-LLM experiment','','## Configuration','',
    '- No LLM or embedding model; no model weight files.',
    '- Pure JavaScript runtime: BM25-style weighted lexical ranking, exact technical-term boosts, domain aliases, quiz/assessment question anchors, sentence selection, and intent-based response templates.',
    '- Knowledge sources: learner-facing SCORM HTML, Quick Reference Guide HTML, and only pre/post instructor answer-key Q&A from the Trainer Preparation Guide.',
    '- Quiz distractors are not treated as facts. A quiz answer is used only when an explicit correct-answer or feedback marker is visible in learner-facing content.',
    '- A separate model-free demo page is included. The original tutor UI is not replaced in this experiment.',
    '- Original SCORM ZIP hash verified unchanged.','',
    '## Knowledge build','','| Metric | Result |','|---|---:|',
    '| Base concepts | '+summary.base_concept_count+' |','| Candidate concepts | '+summary.candidate_concept_count+' |',
    '| Pre-assessment answer-key Q&A | '+summary.assessment_qas.pre+' |','| Post-assessment answer-key Q&A | '+summary.assessment_qas.post+' |',
    '| Existing concepts enriched from assessments | '+summary.existing_concepts_enriched_from_assessments+' |',
    '| Quick Reference concepts added | '+summary.quick_reference_concepts_added+' |','| Course HTML concepts added | '+summary.course_html_concepts_added+' |',
    '| End-of-module quiz pages detected | '+summary.module_quiz_sources_detected+' |','| Quiz questions detected | '+summary.module_quiz_questions_detected+' |',
    '| Quiz questions with visible answer/feedback | '+summary.module_quiz_questions_with_explicit_answers+' |',
    '| Quiz questions linked as query anchors | '+summary.module_quiz_questions_linked_as_query_anchors+' |',
    '| Derived question-stem rules | '+summary.question_stem_rules+' |','| Additional model bytes | 0 |','',
    '## Fixed retrieval-and-answer benchmark','',
    'Baseline: **'+baselinePass+'/'+results.length+'**; no-LLM candidate: **'+candidatePass+'/'+results.length+'**; improved: **'+result.improved+'**; regressed: **'+result.regressed+'**.','',
    '| Test | Baseline | No-LLM | Change | Intent | Top concept |','|---|---|---|---|---|---|'
  ];
  for(const x of results){
    const title=x.candidate_ranked&&x.candidate_ranked[0]&&x.candidate_ranked[0].title||'';
    md.push('| '+x.id+' | '+(x.baseline_pass?'PASS':'FAIL')+' | '+(x.candidate_pass?'PASS':'FAIL')+' | '+x.change+' | '+(x.candidate_intent||'')+' | '+String(title).replace(/\|/g,'\\|').replace(/\r?\n/g,' ')+' |');
  }
  md.push('','## Per-question outputs','');
  for(const x of results){
    md.push('### '+x.id,'','**Question:** '+x.question,'','**Candidate result:** '+(x.candidate_pass?'PASS':'FAIL')+' — '+(x.candidate_category||''),'',x.candidate_answer||'(No answer)','');
    if(x.candidate_sources&&x.candidate_sources.length)md.push('**Sources:** '+x.candidate_sources.join('; '),'');
  }
  md.push('## Interpretation','',
    'This is a small curated benchmark, not proof of general language understanding. Answers are assembled from course-grounded sentences and deterministic intent templates. Inspect each response for completeness, source relevance, and awkward templates before treating the score as acceptance.',
    '');
  fs.writeFileSync(path.join(ROOT,'ai-tutor-lab','NONLLM_EXPERIMENT_REPORT.md'),md.join('\n'));
  console.log(JSON.stringify({test_count:result.test_count,index_record_count:result.index_record_count,
    baseline_pass_count:result.baseline_pass_count,candidate_pass_count:result.candidate_pass_count,improved:result.improved,
    regressed:result.regressed,both_fail:result.both_fail,intent_counts:result.intent_counts,
    quiz_pages_detected:summary.module_quiz_sources_detected,quiz_questions_detected:summary.module_quiz_questions_detected},null,2));
}
main();
