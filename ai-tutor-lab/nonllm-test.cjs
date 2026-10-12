'use strict';
const fs = require('node:fs');
const path = require('node:path');
const NLT = require('./nonllm-tutor.js');
const NLTV1 = require('./nonllm-tutor-v1-baseline.js');
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
  {id:'course-fstab-fields',q:'What six fields go into an /etc/fstab entry for a UUID-based ext4 mount?',all:[/UUID/i,/Mount Point/i,/Filesystem Type/i,/Mount Options/i,/Dump Flag/i,/Fsck Pass/i]},
  {id:'course-yaml-troubleshooting',q:'How should I fix a YAML parsing error in the lab Netplan configuration?',all:[/tab/i,/spaces/i,/90-virtual-lab\.yaml/i]},
  {id:'course-ssh-root-config',q:'In which exact drop-in file does the lab set PermitRootLogin no?',all:[/PermitRootLogin no/i,/99-hardening\.conf/i]},
  {id:'quiz-m04-network-interfaces',group:'learner-quiz-answer',q:'Which modern command displays all network interfaces, their assigned IP addresses, and their current link state on Ubuntu 24?',any:[/ip addr show/i]},
  {id:'quiz-m04-netplan-yaml',group:'learner-quiz-answer',q:'What is the primary formatting requirement when configuring Netplan YAML files in /etc/netplan/?',all:[/spaces/i,/\btabs?\b/i]},
  {id:'quiz-m03-block-devices',group:'learner-quiz-answer',q:'Which Linux command lists block devices, including hard drives, partitions, and virtual disks in a tree-like format?',any:[/lsblk/i]},
  {id:'diagram-pipeline-stderr',group:'held-out-visual',q:'In the pipeline diagram, where is stderr redirected and where is grep output appended?',all:[/errors\.log/i,/incident_report\.txt/i,/2>/i,/>>/]},
  {id:'diagram-directory-traversal',group:'held-out-visual',q:'What does the x permission on a Linux directory let a user do that read permission alone does not?',all:[/execute/i,/(traversal|search)/i]},
  {id:'diagram-storage-workflow',group:'held-out-visual',q:'What sequence should I follow to identify a new disk, partition it, and create an ext4 filesystem?',all:[/lsblk/i,/fdisk/i,/mkfs\.ext4/i]},
  {id:'diagram-process-signals',group:'held-out-visual',q:'Before using the force-kill signal on a process, which signal should I try and why?',all:[/SIGTERM/i,/SIGKILL/i,/(cleanup|clean up)/i]},
  {id:'diagram-netplan-example',group:'held-out-visual',q:'What example IP address and interface appear in the Netplan diagram?',all:[/enp0s3/i,/192\.168\.1\.100\/24/i]},
  {id:'diagram-account-files',group:'held-out-visual',q:'How do the Linux passwd and shadow files differ in the user identity diagram?',all:[/\/etc\/passwd/i,/\/etc\/shadow/i]},
  {id:'diagram-octal-mode',group:'held-out-visual',q:'What do permissions 750 mean for the owner, group, and other users?',all:[/750/i,/rwxr-x---/i]},
  {id:'objective-aligned-accounts',group:'objective-alignment',q:'Which topics in this course teach managing local accounts, groups, and permissions?',all:[/(account|user)/i,/group/i,/permission/i]},
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
  const v1Payload=JSON.parse(fs.readFileSync(path.join(ROOT,'ai-tutor-lab','nonllm-index-v1-baseline.json'),'utf8'));
  const index=NLT.createIndex(payload.concepts,payload.generation_rules,payload.curriculum_structure);
  const v1Index=NLTV1.createIndex(v1Payload.concepts,v1Payload.generation_rules);
  const baselineApi=loadBaseline(),results=[];
  for(const t of tests){
    let oldResult,v1Result,newResult,bError=null,v1Error=null,cError=null;
    try{oldResult=baselineApi.searchConcepts(t.q)}catch(e){bError=String(e)}
    try{v1Result=NLTV1.answer(t.q,v1Index)}catch(e){v1Error=String(e)}
    try{newResult=NLT.answer(t.q,index)}catch(e){cError=String(e)}
    const b=oldResult?check(oldResult,t):{pass:false,category:'TEST_ERROR',answer:'',matchedPatterns:[]};
    const v1=v1Result?check(v1Result,t):{pass:false,category:'TEST_ERROR',answer:'',matchedPatterns:[]};
    const c=newResult?check(newResult,t):{pass:false,category:'TEST_ERROR',answer:'',matchedPatterns:[]};
    results.push({id:t.id,group:t.group||'core-benchmark',question:t.q,outside:!!t.outside,
      baseline_pass:b.pass,v1_pass:v1.pass,candidate_pass:c.pass,
      change:!b.pass&&c.pass?'improved':b.pass&&!c.pass?'regressed':b.pass&&c.pass?'both-pass':'both-fail',
      change_vs_v1:!v1.pass&&c.pass?'improved':v1.pass&&!c.pass?'regressed':v1.pass&&c.pass?'both-pass':'both-fail',
      baseline_category:b.category,v1_category:v1.category,candidate_category:c.category,
      baseline_answer:b.answer.slice(0,850),v1_answer:v1.answer.slice(0,850),candidate_answer:c.answer.slice(0,1100),
      candidate_intent:newResult&&newResult.intent,candidate_score:newResult&&newResult.score,candidate_coverage:newResult&&newResult.coverage,
      candidate_sources:newResult&&newResult.sources,candidate_ranked:newResult&&newResult.ranked,
      candidate_query_plan:newResult&&newResult.queryPlan,candidate_curriculum_matches:newResult&&newResult.curriculumMatches,
      matched_patterns:c.matchedPatterns,errors:{baseline:bError,v1:v1Error,candidate:cError}});
  }
  const baselinePass=results.filter(x=>x.baseline_pass).length;
  const v1Pass=results.filter(x=>x.v1_pass).length;
  const candidatePass=results.filter(x=>x.candidate_pass).length;
  const regressionsV1=results.filter(x=>x.v1_pass&&!x.candidate_pass).length;
  const groupSummary = {};
  for (const row of results) {
    const name = row.group || "core-benchmark";
    if (!groupSummary[name]) groupSummary[name] = { count: 0, baseline_pass: 0, v1_pass: 0, candidate_pass: 0 };
    groupSummary[name].count++;
    if (row.baseline_pass) groupSummary[name].baseline_pass++;
    if (row.v1_pass) groupSummary[name].v1_pass++;
    if (row.candidate_pass) groupSummary[name].candidate_pass++;
  }
  const result={experiment:'non-llm-curriculum-linked-v2',test_count:results.length,index_record_count:index.recordCount,
    curriculum_node_count:(index.curriculumDocs||[]).length,
    baseline_pass_count:baselinePass,v1_pass_count:v1Pass,candidate_pass_count:candidatePass,
    improved_vs_original:results.filter(x=>!x.baseline_pass&&x.candidate_pass).length,
    regressed_vs_original:results.filter(x=>x.baseline_pass&&!x.candidate_pass).length,
    improved_vs_v1:results.filter(x=>!x.v1_pass&&x.candidate_pass).length,
    regressed_vs_v1:regressionsV1,
    both_pass:results.filter(x=>x.baseline_pass&&x.candidate_pass).length,
    both_fail:results.filter(x=>!x.baseline_pass&&!x.candidate_pass).length,
    out_of_scope_tests:results.filter(x=>x.outside).length,group_summary:groupSummary,
    intent_counts:results.reduce((o,x)=>{const k=x.candidate_intent||'error';o[k]=(o[k]||0)+1;return o;},{}),results};
  fs.writeFileSync(path.join(ROOT,'ai-tutor-lab','nonllm-results.json'),JSON.stringify(result,null,2));
  const stageOneSummary=JSON.parse(fs.readFileSync(path.join(ROOT,'ai-tutor-lab','nonllm-build-summary.json'),'utf8'));
  const curriculumBuild=JSON.parse(fs.readFileSync(path.join(ROOT,'ai-tutor-lab','curriculum-build-summary.json'),'utf8'));
  const buildCoverage=curriculumBuild.coverage;
  const curriculumCounts=buildCoverage.curriculum_counts;
  const assessmentCounts=buildCoverage.assessment_counts;
  const sourceBlockCoverage=buildCoverage.course_html_block_coverage;
  const imageCoverage=buildCoverage.image_transcriptions;
  const qrgPdfIndexing=(curriculumBuild.pdf_audit||{})['Day-01-QuickReference.pdf']?.indexing||{};
  const md=[
    '# LNX-001 AI Tutor Lab — curriculum-linked non-LLM experiment','','## Runtime design','',
    '- No LLM, neural embedding model, model weights, WebAssembly, hosted service, or runtime network calls.',
    '- Pure JavaScript query pipeline: safe Lucene-inspired structured query plans, BM25-style lexical ranking, exact technical literal boosts, controlled aliases, sparse objective/topic vectors, importance metadata, and Reciprocal Rank Fusion (RRF).',
    '- Answer construction uses course-grounded evidence, intent classification, sentence selection, and deterministic response templates.',
    '- Knowledge combines the full learner-facing SCORM content, reviewed transcriptions for instructional images, learner Quick Reference material, the existing tutor corpus, the approved pre/post assessment answer keys, and learner-visible module quiz items.',
    '- Every SCORM archive entry has an explicit disposition. Trainer-only Module Q&A Reference and other instructor-only guide sections remain excluded under the established source policy; approved pre/post answer-key material is included.',
    '- Original SCORM ZIP hash verified unchanged. The tutor UI in the source package is not replaced; the candidate contains a separate experimental demo page.','',
    '## Knowledge coverage and curriculum structure','','| Metric | Result |','|---|---:|',
    '| Original tutor knowledge records | '+stageOneSummary.base_concept_count+' |',
    '| Prior no-LLM searchable records | '+curriculumBuild.base_concepts_before_enrichment+' |',
    '| Curriculum V2 searchable records | '+curriculumBuild.candidate_searchable_records+' |',
    '| SCORM archive entries with explicit disposition | '+buildCoverage.scorm_inventory_counts.entries_with_explicit_disposition+'/'+buildCoverage.scorm_inventory_counts.entries_in_package+' |',
    '| Learner-facing HTML visible characters audited | '+sourceBlockCoverage.visible_chars_including_quiz+' |',
    '| Learner-facing HTML blocks accounted for | '+sourceBlockCoverage.eligible_text_blocks+' |',
    '| New source-block records / blocks already covered | '+sourceBlockCoverage.blocks_added_as_records+' / '+sourceBlockCoverage.blocks_already_covered+' |',
    '| Structural headings represented as topic/metadata | '+sourceBlockCoverage.structural_headings_mapped_to_topics_or_metadata+' |',
    '| Instructional image transcriptions | '+imageCoverage.added+'/'+imageCoverage.expected+' |',
    '| Quick Reference PDF unique records added | '+(qrgPdfIndexing.unique_records_added||0)+' |',
    '| Course objectives | '+curriculumBuild.course_objective_count+' |',
    '| Module objectives | '+curriculumBuild.module_objective_count+' |',
    '| Module topics | '+curriculumBuild.module_topic_count+' |',
    '| Lesson topics | '+curriculumBuild.lesson_topic_count+' |',
    '| Curriculum graph nodes / edges | '+curriculumCounts.graph_nodes+' / '+curriculumCounts.graph_edges+' |',
    '| Searchable records linked to curriculum | '+buildCoverage.record_link_counts.records_linked_to_curriculum+'/'+curriculumBuild.candidate_searchable_records+' ('+(100*buildCoverage.record_link_counts.curriculum_link_rate).toFixed(2)+'%) |',
    '| Pre-assessment questions | '+assessmentCounts.pre_assessment_questions+' |',
    '| Post-assessment questions | '+assessmentCounts.post_assessment_questions+' |',
    '| End-of-module quiz questions | '+assessmentCounts.module_quiz_questions+' |',
    '| Structured assessment/quiz items linked to objectives or topics | '+assessmentCounts.items_linked_to_objectives_or_topics+'/'+assessmentCounts.total_items+' |',
    '| Correctness-labeled choices | '+assessmentCounts.choices_with_correctness_labels+'/'+assessmentCounts.choices_total+' |',
    '| Candidate SCORM package | '+curriculumBuild.candidate_v2_bytes+' bytes ('+(curriculumBuild.candidate_v2_bytes-curriculumBuild.source_package_bytes)+' bytes larger than source) |',
    '| Additional model bytes | 0 |','',
    '## Three-way retrieval-and-answer benchmark','',
    'Original tutor: **'+baselinePass+'/'+results.length+'**; prior no-LLM engine: **'+v1Pass+'/'+results.length+'**; curriculum-aware candidate: **'+candidatePass+'/'+results.length+'**.','',
    'Improvements versus original: **'+result.improved_vs_original+'**; regressions versus original: **'+result.regressed_vs_original+'**; improvements versus prior no-LLM: **'+result.improved_vs_v1+'**; regressions versus prior no-LLM: **'+result.regressed_vs_v1+'**.','',
    '### Results by question group','','| Group | Questions | Original passed | Prior no-LLM passed | Curriculum V2 passed |','|---|---:|---:|---:|---:|',
    ...Object.entries(groupSummary).map(([name,g])=>'| '+name+' | '+g.count+' | '+g.baseline_pass+' | '+g.v1_pass+' | '+g.candidate_pass+' |'),
    '',
    '| Test | Group | Original | Prior no-LLM | Curriculum V2 | Change vs prior | Intent | Top retrieved record |','|---|---|---|---|---|---|---|---|'
  ];
  for(const x of results){
    const title=x.candidate_ranked&&x.candidate_ranked[0]&&x.candidate_ranked[0].title||'';
    md.push('| '+x.id+' | '+(x.group||'core-benchmark')+' | '+(x.baseline_pass?'PASS':'FAIL')+' | '+(x.v1_pass?'PASS':'FAIL')+' | '+(x.candidate_pass?'PASS':'FAIL')+' | '+x.change_vs_v1+' | '+(x.candidate_intent||'')+' | '+String(title).replace(/\|/g,'\\|').replace(/\r?\n/g,' ')+' |');
  }
  md.push('','## Per-question outputs','');
  for(const x of results){
    md.push('### '+x.id,'','**Question:** '+x.question,'','**Candidate result:** '+(x.candidate_pass?'PASS':'FAIL')+' — '+(x.candidate_category||''),'',x.candidate_answer||'(No answer)','');
    if(x.candidate_sources&&x.candidate_sources.length)md.push('**Sources:** '+x.candidate_sources.join('; '),'');
  }
  md.push('## Interpretation','',
    'This is a small curated benchmark, not proof of general language understanding. Answers are assembled from course-grounded sentences and deterministic intent templates. Inspect each response for completeness, source relevance, and awkward templates before treating the score as acceptance.',
    '');
  const audit=JSON.parse(fs.readFileSync(path.join(ROOT,'ai-tutor-lab','source-coverage-audit.json'),'utf8'));
  const build=JSON.parse(fs.readFileSync(path.join(ROOT,'ai-tutor-lab','curriculum-build-summary.json'),'utf8'));
  const runtimeReady=index.curriculumDocs.length>0 && results.every(x=>!x.errors.candidate);
  const heldout=results.filter(x=>(x.group||'').startsWith('held-out')||(x.group||'')==='objective-alignment');
  const heldoutPass=heldout.filter(x=>x.candidate_pass).length;
  const objectiveRows=(audit.design_objectives||[]).map(x=>({...x}));
  const replaceObj=(id,status,measured)=>{const hit=objectiveRows.find(x=>x.id===id);if(hit){hit.status=status;hit.measured={...(hit.measured||{}),...measured};}};
  replaceObj('D7',runtimeReady?'PASS':'FAIL',{query_time_curriculum_nodes:index.curriculumDocs.length,
    query_plan_engine:'Lucene-inspired structured query plan',fusion:'Reciprocal Rank Fusion (RRF)',
    weighted_retrieval_tests:results.length,queries_with_curriculum_matches:results.filter(x=>(x.candidate_curriculum_matches||[]).length>0).length});
  objectiveRows.push({id:'D9',objective:'Curriculum-aware candidate has no regressions against prior no-LLM benchmark',status:regressionsV1===0?'PASS':'REVIEW',
    measured:{tests:results.length,prior_no_llm_pass:v1Pass,curriculum_candidate_pass:candidatePass,regressions:regressionsV1}});
  objectiveRows.push({id:'D10',objective:'Held-out diagram and objective-aligned questions retrieve supported answers',status:heldoutPass===heldout.length?'PASS':'REVIEW',
    measured:{tests:heldout.length,passed:heldoutPass,failed:heldout.filter(x=>!x.candidate_pass).map(x=>x.id)}});
  objectiveRows.push({id:'D11',objective:'No LLM, model weights, WebAssembly, or runtime network dependency introduced',status:(build.runtime_model_count===0&&!build.webassembly_added&&!build.runtime_network_calls_added)?'PASS':'FAIL',
    measured:{runtime_model_count:build.runtime_model_count,extra_model_bytes:build.extra_model_bytes,webassembly_added:build.webassembly_added,runtime_network_calls_added:build.runtime_network_calls_added}});
  const measurement={experiment:'non-llm-curriculum-linked-v2',test_count:results.length,original_tutor_passes:baselinePass,
    prior_nonllm_passes:v1Pass,curriculum_candidate_passes:candidatePass,improvements_vs_original:result.improved_vs_original,
    regressions_vs_original:result.regressed_vs_original,improvements_vs_v1:result.improved_vs_v1,regressions_vs_v1:regressionsV1,
    heldout_tests:{count:heldout.length,passed:heldoutPass,pass_rate:heldout.length?heldoutPass/heldout.length:0},
    design_objectives:objectiveRows,coverage:audit.scorm_inventory_counts,
    build_metrics:{searchable_records:build.candidate_searchable_records,curriculum_nodes:build.coverage.curriculum_counts.graph_nodes,
      curriculum_edges:build.coverage.curriculum_counts.graph_edges,linked_records:build.coverage.record_link_counts.records_linked_to_curriculum,
      record_link_rate:build.coverage.record_link_counts.curriculum_link_rate}};
  fs.writeFileSync(path.join(ROOT,'ai-tutor-lab','curriculum-objective-measurement.json'),JSON.stringify(measurement,null,2));
  md.push('','## Design objectives and coverage acceptance','','| ID | Objective | Status | Evidence |','|---|---|---|---|');
  for(const row of objectiveRows)md.push('| '+row.id+' | '+row.objective.replace(/\|/g,'\\\\|')+' | **'+row.status+'** | '+JSON.stringify(row.measured||{}).replace(/\|/g,'\\\\|')+' |');
  md.push('','## Baseline comparison','','| Measure | Original tutor | Prior no-LLM | Curriculum v2 |','|---|---:|---:|---:|',
    '| Answer checks passed | '+baselinePass+'/'+results.length+' | '+v1Pass+'/'+results.length+' | '+candidatePass+'/'+results.length+' |',
    '| Improvement vs prior no-LLM | — | — | '+result.improved_vs_v1+' |',
    '| Regression vs prior no-LLM | — | — | '+regressionsV1+' |',
    '| Held-out checks passed | — | — | '+heldoutPass+'/'+heldout.length+' |','');
  fs.writeFileSync(path.join(ROOT,'ai-tutor-lab','NONLLM_EXPERIMENT_REPORT.md'),md.join('\n'));
  console.log(JSON.stringify({test_count:result.test_count,index_record_count:result.index_record_count,curriculum_node_count:result.curriculum_node_count,
    original_tutor_passes:baselinePass,prior_no_llm_passes:v1Pass,curriculum_candidate_passes:candidatePass,
    improved_vs_original:result.improved_vs_original,regressed_vs_original:result.regressed_vs_original,
    improved_vs_v1:result.improved_vs_v1,regressed_vs_v1:regressionsV1,heldout_tests:heldout.length,heldout_passed:heldoutPass,
    design_objectives:objectiveRows.map(x=>({id:x.id,status:x.status})),group_summary:groupSummary},null,2));
}
main();
