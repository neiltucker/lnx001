'use strict';
const fs=require('node:fs'),path=require('node:path');
const work='/tmp/lnx001-ai-tutor-lab';
const tests=[
{id:'qrg-live-log',q:'How can I follow a live system log in real time?',any:[/tail\s+-f/i]},
{id:'qrg-grep-tail',q:'Find case-insensitive error lines from syslog and show the last 20 matches.',all:[/grep/i,/tail\s+-n\s+20/i]},
{id:'qrg-append',q:'How do I append new log records without deleting old ones?',any:[/>>/]},
{id:'qrg-usermod',q:'Add a user to a supplementary group without removing existing memberships.',all:[/usermod/i,/-aG/i]},
{id:'qrg-mount-uuid',q:'Configure persistent ext4 mounting with UUID.',all:[/UUID/i,/fstab/i]},
{id:'qrg-process',q:'How should I stop a stuck process gracefully before forcing it?',any:[/SIGTERM/i,/kill\s+-15/i]},
{id:'qrg-ufw-ssh',q:'What should I allow before enabling UFW on a remote SSH server?',any:[/OpenSSH/i,/ufw\s+allow/i]},
{id:'pre-assessment-x-dir',q:'What permission lets a user traverse a directory and change into it with cd?',any:[/execute/i,/traversal/i]},
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
{id:'out-of-scope-brakes',q:'How do I replace brake pads on a 2026 Honda Accord?',outside:true}
];
function makeEnv(which){
 const d=path.join(work,which),js=fs.readFileSync(path.join(d,'tutor.js'),'utf8'),data=fs.readFileSync(path.join(d,'tutor-data.js'),'utf8');
 const w={__CS_AI_TUTOR_ENABLED__:1,__CS_AI_TUTOR_CONFIG__:{moduleNumber:1,totalModules:4,courseTitle:'Linux Administration Essentials',language:'english'},__CS_AI_TUTOR_DATA__:null};
 const doc={readyState:'complete',addEventListener:()=>{},getElementById:()=>null,getElementsByTagName:()=>[],createElement:()=>({appendChild:()=>{},setAttribute:()=>{},addEventListener:()=>{},removeChild:()=>{},querySelectorAll:()=>[],style:{}}),body:{appendChild:()=>{},children:[],style:{}},documentElement:{},querySelector:()=>null};
 const store={getItem:()=>null,setItem:()=>{},removeItem:()=>{}};
 new Function('mockWindow',data.replace(/\bwindow\./g,'mockWindow.'))(w);
 new Function('window','document','sessionStorage',js)(w,doc,store);
 const api=w.__CS_AI_TUTOR_API__;if(!api||!api.initCorpus||!api.searchConcepts)throw new Error('Tutor test API missing from '+which);
 api.initCorpus();return api;
}
function run(api,t){let r;try{r=api.searchConcepts(t.q)}catch(e){return{id:t.id,query:t.q,error:String(e),pass:false}}
 const cat=r&&r.category||'NO_RESULT',a=String(r&&r.answer||''),title=r&&r.concept&&(r.concept.title||r.concept.section_title)||null,score=typeof(r&&r.score)==='number'?r.score:null,arr=t.all||t.any||[],hits=arr.filter(rx=>rx.test(a));
 const good=t.outside?cat!=='IN_COURSE':cat==='IN_COURSE'&&(t.all?hits.length===arr.length:hits.length>0);
 return{id:t.id,query:t.q,category:cat,score,selectedTitle:title,answer:a.slice(0,1200),matchedPatterns:hits.map(String),pass:!!good};
}
let b,c,be=null,ce=null;try{b=makeEnv('baseline')}catch(e){be=String(e)}try{c=makeEnv('candidate')}catch(e){ce=String(e)}
const unavailable=(t,e)=>({id:t.id,query:t.q,category:'TEST_UNAVAILABLE',error:e,selectedTitle:null,answer:'',pass:false});
const br=tests.map(t=>b?run(b,t):unavailable(t,be)),cr=tests.map(t=>c?run(c,t):unavailable(t,ce));
const bm=new Map(br.map(x=>[x.id,x])),cm=new Map(cr.map(x=>[x.id,x]));
const comparison=tests.map(t=>{const x=bm.get(t.id),y=cm.get(t.id);return{id:t.id,query:t.q,baseline_pass:x.pass,candidate_pass:y.pass,change:!x.pass&&y.pass?'improved':x.pass&&!y.pass?'regressed':x.pass&&y.pass?'still-passes':'still-fails',baseline_category:x.category,candidate_category:y.category,baseline_title:x.selectedTitle,candidate_title:y.selectedTitle,baseline_score:x.score,candidate_score:y.score,baseline_answer:x.answer,candidate_answer:y.answer}});
const out={test_count:tests.length,baseline_runtime_available:!!b,baseline_runtime_error:be,candidate_runtime_available:!!c,candidate_runtime_error:ce,baseline_pass_count:br.filter(x=>x.pass).length,candidate_pass_count:cr.filter(x=>x.pass).length,improved:comparison.filter(x=>x.change==='improved').length,regressed:comparison.filter(x=>x.change==='regressed').length,still_fails:comparison.filter(x=>x.change==='still-fails').length,baseline_results:br,candidate_results:cr,comparison};
fs.writeFileSync('ai-tutor-lab/runtime-comparison.json',JSON.stringify(out,null,2));
const sum=JSON.parse(fs.readFileSync('ai-tutor-lab/experiment-summary.json','utf8')),safe=s=>String(s||'—').replace(/\|/g,'\\|').replace(/\r?\n/g,' ');
const lines=['# LNX-001 AI Tutor Lab — full-course knowledge retrieval baseline — local-generation POC V6','','Isolated branch. Original SCORM package is unchanged. No Courseware Studio changes.','','## Package and knowledge coverage','','| Metric | Result |','|---|---:|','| Original package bytes | '+sum.baseline_package_bytes+' |','| Candidate package bytes | '+sum.candidate_package_bytes+' |','| Tutor data bytes | '+sum.baseline_tutor_data_bytes+' → '+sum.candidate_tutor_data_bytes+' |','| Existing concepts | '+sum.baseline_concept_count+' |','| Candidate concepts | '+sum.candidate_concept_count+' |','| SCORM course HTML records added | '+sum.course_html_concepts_added+' |','| Quick Reference records added | '+sum.quick_reference_concepts_added+' |','| Pre/post Q&A parsed | 10 / 20 |','| Assessment Q&As added/enriched | '+sum.assessment_qas_added_as_new_concepts+' / '+sum.existing_concepts_enriched_by_assessment_qas+' |','','## Baseline versus candidate','','Baseline: **'+out.baseline_pass_count+'/'+out.test_count+'**; candidate: **'+out.candidate_pass_count+'/'+out.test_count+'**; improved: **'+out.improved+'**; regressed: **'+out.regressed+'**; still failing: **'+out.still_fails+'**.','','| Test | Baseline | Candidate | Change | Baseline result | Candidate result |','|---|---|---|---|---|---|'];
for(const x of comparison)lines.push('| '+safe(x.id)+' | '+(x.baseline_pass?'PASS':'FAIL')+' | '+(x.candidate_pass?'PASS':'FAIL')+' | '+safe(x.change)+' | '+safe(x.baseline_title)+' | '+safe(x.candidate_title)+' |');
lines.push('','## Source coverage','','| SCORM HTML source | Visible text characters |','|---|---:|');for(const x of sum.course_html_sources)lines.push('| '+safe(x.path)+' | '+x.visible_chars+' |');
lines.push('','## Guardrails','','- Only Pre-Assessment Instructor Answer Key and Post-Assessment Instructor Answer Key Q&A are extracted from the trainer guide; all other guide material is excluded.','- Quick Reference HTML is indexed once; its PDF duplicate is not indexed separately.','- The candidate contains a lab-only IDF-weighted query-coverage patch in ai-tutor/tutor.js. No hosted AI, external runtime calls, WebAssembly, or new runtime dependency is added.','- Candidate changes only ai-tutor/tutor.js and ai-tutor/tutor-data.js; the original ZIP remains unchanged.','- This is still a retrieval-only experiment: the candidate uses an IDF-weighted coverage penalty but still returns one prepared answer and does not synthesize novel multi-passage responses.','','## Interpretation','');
if(!out.baseline_runtime_available||!out.candidate_runtime_available)lines.push('Runtime comparison unavailable: baseline '+safe(be)+'; candidate '+safe(ce)+'.');
else if(out.regressed)lines.push('Review each regression using the included answer text before accepting the experiment.');
else lines.push('The fixed benchmark found no regressions; review full answer text and manually launch the candidate in a separate LMS test course before drawing broader conclusions.');
lines.push('');
fs.writeFileSync('ai-tutor-lab/EXPERIMENT_REPORT.md',lines.join('\n'));
console.log(JSON.stringify({test_count:out.test_count,baseline_available:out.baseline_runtime_available,candidate_available:out.candidate_runtime_available,baseline_pass_count:out.baseline_pass_count,candidate_pass_count:out.candidate_pass_count,improved:out.improved,regressed:out.regressed,still_fails:out.still_fails,baseline_error:be,candidate_error:ce},null,2));
