#!/usr/bin/env python3
import hashlib, html, json, re, sys, zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path.cwd()
PACKAGE=ROOT/"LNX-001_EN_SCORM2004.zip"
GUIDE=ROOT/"LNX-001_EN_TrainerPreparationGuide.txt"
QRG=ROOT/"Day-01-QuickReference.html"
OUT=ROOT/"LNX-001_EN_SCORM2004_AI-TUTOR-LAB-V4.zip"
WORK=Path("/tmp/lnx001-ai-tutor-lab")
STOP=set("a an the and or but if then of to in on at by for with do does did have has had is are was were be been being what which who when where why how this that these those you your my me we us our it its they them their can could would should will as from about into than so not nor too very just only also still even any some all every most more less few command commands linux system administrator administrators user users using use used uses need should must question answer explain explanation correct choice option select following".split())
class Visible(HTMLParser):
    skip={"script","style","noscript","svg","nav","footer","button","head","template"}
    block={"p","li","pre","code","blockquote","td","th","dt","dd","figcaption","summary","tr"}
    heads={"h1","h2","h3","h4","h5","h6"}
    def __init__(self):
        super().__init__(convert_charrefs=True); self.sk=0; self.tag=None; self.buf=[]; self.blocks=[]; self.title=""
    def flush(self):
        s=re.sub(r"\s+"," ",html.unescape(" ".join(self.buf))).strip()
        if s:
            if self.tag=="title": self.title=s
            else: self.blocks.append((self.tag or "p",s))
        self.buf=[]; self.tag=None
    def handle_starttag(self,t,attrs):
        t=t.lower()
        if self.sk:
            if t in self.skip:self.sk+=1
            return
        if t in self.skip:self.sk=1;return
        if t in self.heads or t in self.block or t=="title":self.flush();self.tag=t
        elif t=="br":self.buf.append(" ")
        elif t=="img":
            a=dict(attrs).get("alt")
            if a:self.blocks.append(("p",a))
    def handle_endtag(self,t):
        t=t.lower()
        if self.sk:
            if t in self.skip:self.sk-=1
            return
        if t in self.heads or t in self.block or t=="title":self.flush()
    def handle_data(self,d):
        if not self.sk and d.strip():
            if self.tag is None:self.tag="p"
            self.buf.append(d.strip())
def norm(s):return re.sub(r"[^a-z0-9]+"," ",s.lower()).strip()
def toks(s):return {x for x in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_+.#/-]*",s.lower()) if len(x)>1 and x not in STOP}
def split_chunks(s,limit=1000):
    s=re.sub(r"\s+"," ",s).strip()
    if len(s)<100:return []
    if len(s)<=limit:return [s]
    parts=re.split(r"(?<=[.!?])\s+(?=[A-Z0-9/])",s); out=[]; cur=""
    for p in parts:
        if len(p)>limit:
            if cur:out.append(cur);cur=""
            while len(p)>limit:
                i=p.rfind(" ",0,limit)
                if i<100:i=limit
                out.append(p[:i].strip());p=p[i:].strip()
            cur=p
        elif not cur:cur=p
        elif len(cur)+len(p)+1<=limit:cur+=" "+p
        else:out.append(cur);cur=p
    if cur:out.append(cur)
    return [x for x in out if len(x)>=100]
def html_sections(raw,fallback):
    p=Visible();p.feed(raw);p.close(); groups=[]; heading=p.title or fallback; parts=[]
    def flush():
        nonlocal parts
        joined=" ".join(parts).strip()
        if joined:groups.append((heading,joined))
        parts=[]
    for tag,text in p.blocks:
        if tag in p.heads:flush();heading=text
        else:parts.append(text)
    flush();out=[]
    for title,body in groups:
        for i,chunk in enumerate(split_chunks(body),1):out.append((title if i==1 else title+" — Part "+str(i),chunk))
    # If source had no structural blocks, preserve the visible text as a fallback.
    if not out:
        text=" ".join(x[1] for x in p.blocks)
        for i,chunk in enumerate(split_chunks(text),1):out.append((fallback+" — Part "+str(i),chunk))
    return out,p
def module_guess(text,path,bundle):
    m=re.search(r"(?:module|mod|m|day)[\s_./-]*0?([1-4])\b",(path+" "+text).lower())
    if m:return int(m.group(1))
    kws={1:["path","filesystem","directory","grep","tail","pipeline","redirect","touch","relative","absolute"],
         2:["permission","chmod","chown","usermod","group","uid","gid","shadow","visudo","sudoers"],
         3:["lspci","lsblk","partition","ext4","fstab","uuid","mount","process","sigterm","kill"],
         4:["network","netplan","ssh","openssh","ufw","firewall","socket","tcp","udp","yaml"]}
    scores={n:sum(x in (text+" "+path).lower() for x in a) for n,a in kws.items()}
    return max(scores,key=scores.get) if max(scores.values()) else 1
def make_record(i,title,answer,mod,mtitle,citation,kind):
    original_title=re.sub(r"\s+"," ",title).strip()
    body=re.sub(r"\s+"," ",answer).strip()

    # Preserve high-signal technical literals before frequent words so key identifiers
    # survive the bounded index (paths, addresses, interface names, versions, code spans).
    paths=re.findall(r"(?<![\w.])/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+",body)
    ips=re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b",body)
    identifiers=re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\d+[A-Za-z0-9_]*\b",body)
    chunks=body.split(chr(96))
    code_spans=[chunks[j].strip() for j in range(1,len(chunks),2) if chunks[j].strip()]
    technical=[]
    for value in paths+ips+identifiers+code_spans:
        technical.append(value)
        technical.extend(re.findall(r"[A-Za-z0-9_+#./:-]+",value))
    technical.extend(re.findall(r"\b[A-Z][A-Z0-9_.+-]{1,}\b",body))
    technical.extend(re.findall(r"\b[A-Za-z][A-Za-z0-9_.+-]*-[A-Za-z0-9_.+-]+\b",body))

    words=re.findall(r"[A-Za-z][A-Za-z0-9_+#./-]{2,}",original_title+" "+body)
    counts=Counter(x.lower() for x in words if x.lower() not in STOP)
    frequent=[x for x,_ in counts.most_common(70)]
    seen_kw=set();kw=[]
    for value in technical+frequent:
        value=value.strip();key=value.lower()
        if key and key not in seen_kw:
            seen_kw.add(key);kw.append(value)
        if len(kw)>=100:break

    display_title=original_title
    cleaned_for_match=re.sub(r"^[^\w]+","",original_title)
    generic=bool(re.match(r"^(?:procedures?(?:\s*[—–:-]\s*part\s*\d+)?|troubleshooting|overview|key concepts?|learning objectives?|summary|course content|module content)\b",cleaned_for_match,re.I))
    if generic:
        fragments=re.split(r"(?<=[.!?])\s+(?=[A-Z0-9/])|(?<=[;:])\s+(?=[A-Z0-9/])",body)
        best_fragment="";best_score=-1
        for fragment in fragments:
            fragment=fragment.strip(" .;:")
            if len(fragment)<28:continue
            fpaths=re.findall(r"(?<![\w.])/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+",fragment)
            fips=re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b",fragment)
            fids=re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\d+[A-Za-z0-9_]*\b",fragment)
            fwords=[x for x in re.findall(r"[A-Za-z][A-Za-z0-9_+#./-]{2,}",fragment) if x.lower() not in STOP]
            score=10*len(fpaths)+15*len(fips)+4*len(fids)+min(len(set(w.lower() for w in fwords)),20)
            if len(fragment)>220:score-=3
            if score>best_score:best_score=score;best_fragment=fragment
        if best_fragment:
            display_title=(original_title+" — "+best_fragment)[:240]

    anchors=[original_title,display_title,"Explain "+display_title]
    if kind=="qrg":anchors.append("How do I "+display_title[:1].lower()+display_title[1:]+"?")
    elif kind=="assessment":anchors.append("Help me understand "+original_title)
    if ips and identifiers:
        for ident in identifiers[:2]:
            anchors.append("Which IP address is configured for "+ident+"?")
            if re.search(r"\b(?:verif(?:y|ies|ied|ication)|confirm|check|inspect|show|display|output)\b",body,re.I):
                anchors.append("Which command verifies the configured address on "+ident+"?")
    if len(paths)>=2:
        anchors.append("Which exact command paths does this procedure specify?")
        anchors.append("Which command paths are allowed by this procedure?")
    if paths:
        anchors.append("Which configuration file or absolute path is used in this procedure?")
    if code_spans:
        anchors.append("Which command or code example does this section provide?")
    if len(body)>25:
        anchors.append(re.split(r"(?<=[.!?])\s+",body)[0][:180])
    dedup=[];seen_anchor=set()
    for anchor in anchors:
        key=re.sub(r"\s+"," ",anchor).strip().lower()
        if key and key not in seen_anchor:
            seen_anchor.add(key);dedup.append(re.sub(r"\s+"," ",anchor).strip())
    ctype="framework" if kind=="qrg" else ("comparison" if re.search(r"\b(compare|difference|versus)\b",original_title,re.I) else "definition")
    return {"id":i,"module_number":mod,"module_title":mtitle,"lesson_title":citation,"section_title":original_title,"title":display_title,"concept_type":ctype,"direct_answer":body[:3500],"structured_points":[],"citation":citation,"keywords":kw,"query_anchors":dedup[:14]}

def parse_bundle(js):
    marker="window.__CS_AI_TUTOR_DATA__";at=js.find(marker)
    if at<0:raise ValueError("No window.__CS_AI_TUTOR_DATA__ assignment in SCORM")
    eq=js.find("=",at+len(marker));semi=js.rfind(";")
    return json.loads(js[eq+1:semi if semi>eq else None].strip())
def patch_lab_query_coverage(tutor_js):
    # This controlled experiment penalizes a high-scoring answer when it omits
    # distinctive query terms. Production code remains untouched.
    needle="""      if (isNewSessionQuery && c.polarity === 'termination') score *= 0.1;
      else if (isNewSessionQuery && c.polarity === 'initiation') score *= 2.5;

      if (score > best.score) {"""
    replacement="""      if (isNewSessionQuery && c.polarity === 'termination') score *= 0.1;
      else if (isNewSessionQuery && c.polarity === 'initiation') score *= 2.5;

      // LNX-001 lab V3: coverage penalty for candidates that omit query evidence.
      // Rare terms such as a specific interface, path, or command have higher IDF.
      var lnxQueryWeightTotal = 0;
      var lnxQueryWeightFound = 0;
      querySet.forEach(function (term) {
        var lnxWeight = getIdf(term);
        if (!(lnxWeight > 0)) lnxWeight = 1;
        lnxQueryWeightTotal += lnxWeight;
        if (doc.titleSet.has(term) || doc.kwSet.has(term) || doc.qaSet.has(term) || doc.bodySet.has(term)) {
          lnxQueryWeightFound += lnxWeight;
        }
      });
      var lnxQueryCoverage = lnxQueryWeightTotal > 0 ? lnxQueryWeightFound / lnxQueryWeightTotal : 1;
      score *= Math.pow(Math.max(0.20, lnxQueryCoverage), 1.25);

      if (score > best.score) {"""
    if tutor_js.count(needle) != 1:
        raise ValueError("Expected exactly one tutor scoring anchor for the lab coverage patch")
    return tutor_js.replace(needle, replacement, 1)

def assessment_records(guide):
    # Standardize typography in this text export before locating assessment answer-key sections.
    guide=guide.replace(chr(160)," ").replace("—","-").replace("–","-").replace("−","-").replace(chr(65533),"-")
    a=re.search("Pre-Assessment +- +Instructor Answer Key",guide,re.I)
    b=re.search("Post-Assessment +- +Student Handout",guide,re.I)
    c=re.search("Post-Assessment +- +Instructor Answer Key",guide,re.I)
    if not(a and b and c):
        nearby=[line for line in guide.splitlines() if "Assessment" in line and ("Instructor" in line or "Student Handout" in line)]
        raise ValueError("Missing expected answer-key headings: pre="+str(bool(a))+", post-student="+str(bool(b))+", post-key="+str(bool(c))+"; found="+repr(nearby[:12]))
    ret=[]
    for kind,s in (("pre",guide[a.end():b.start()]),("post",guide[c.end():])):
        ms=list(re.finditer(r"(?m)^\s*(\d{1,2})\.\s+",s))
        for j,m in enumerate(ms):
            block=s[m.end():ms[j+1].start() if j+1<len(ms) else len(s)]
            oa=re.search(r"(?m)^\s*A[.)]\s+",block); ans=re.search(r"(?im)^\s*Answer:\s*([A-D])\s*$",block)
            if not oa or not ans or ans.start()<oa.start():continue
            question=re.sub(r"\s+"," ",block[:oa.start()]).strip()
            choices={}; sl=block[oa.start():ans.start()]
            oms=list(re.finditer(r"(?m)^\s*([A-D])[.)]\s+",sl))
            for k,o in enumerate(oms):
                end=oms[k+1].start() if k+1<len(oms) else len(sl)
                choices[o.group(1)]=re.sub(r"\s+"," ",sl[o.end():end]).strip(" .\r\n\t")
            letter=ans.group(1).upper(); correct=choices.get(letter,"")
            expl=re.sub(r"\s+"," ",block[ans.end():]).strip()
            answer=("Correct answer: "+correct+". " if correct else "Correct answer: option "+letter+". ")+expl
            citation="Trainer Preparation Guide — "+("Pre-Assessment" if kind=="pre" else "Post-Assessment")+" Instructor Answer Key, question "+m.group(1)
            ret.append({"kind":kind,"n":int(m.group(1)),"question":question,"answer":answer.strip(),"citation":citation,"correct":correct})
    counts={k:sum(r["kind"]==k for r in ret) for k in ("pre","post")}
    if counts!={"pre":10,"post":20}:raise ValueError("Expected 10 pre and 20 post Q&A, parsed "+str(counts))
    return ret
def main():
    for f in (PACKAGE,GUIDE,QRG):
        if not f.exists():raise FileNotFoundError("Required source file not found: "+str(f))
    guide=GUIDE.read_text(encoding="utf-8",errors="replace"); qas=assessment_records(guide)
    WORK.mkdir(parents=True,exist_ok=True);(WORK/"baseline").mkdir(exist_ok=True);(WORK/"candidate").mkdir(exist_ok=True)
    with zipfile.ZipFile(PACKAGE) as zin:
        bad=zin.testzip()
        if bad:raise ValueError("Corrupt source ZIP entry "+bad)
        names=zin.namelist();tpath=next((n for n in names if n.lower().endswith("ai-tutor/tutor.js")),None);dpath=next((n for n in names if n.lower().endswith("ai-tutor/tutor-data.js")),None)
        if not tpath or not dpath:raise ValueError("Source SCORM missing ai-tutor/tutor.js or tutor-data.js")
        tutor=zin.read(tpath).decode("utf-8",errors="replace"); data=zin.read(dpath).decode("utf-8",errors="replace");bundle=parse_bundle(data)
        concepts=bundle.get("concepts") if isinstance(bundle.get("concepts"),list) else []
        if not concepts:
            for j,p in enumerate(bundle.get("pairs") or [],1):
                concepts.append(make_record("base_pair_"+str(j),p.get("question","Question "+str(j)),p.get("answer",""),int(p.get("module_number",1)),str(bundle.get("module_titles",{}).get(str(p.get("module_number",1)),"Module")),p.get("source_lesson","Existing tutor Q&A"),"base"))
        if not concepts:raise ValueError("Existing tutor bundle has no searchable concepts")
        base_count=len(concepts);bundle["concepts"]=concepts;titles=bundle.get("module_titles") or {}
        seen_questions={norm(str(x.get("title",""))) for x in concepts}
        qa_add=qa_enrich=0
        for q in qas:
            titlekey=norm(q["question"]);best=None;bestscore=0
            qt=toks(q["question"])
            for x in concepts:
                xt=toks(str(x.get("title",""))+" "+str(x.get("direct_answer",""))+" "+" ".join(x.get("keywords") or []))
                score=len(qt&xt)/max(1,len(qt))
                if score>bestscore:best,bestscore=x,score
            if best and bestscore>=0.55:
                anchors=best.setdefault("query_anchors",[])
                if q["question"] not in anchors:anchors.append(q["question"])
                best.setdefault("keywords",[]).extend([z for z in [q["correct"],q["citation"]] if z and z not in best["keywords"]])
                old=str(best.get("direct_answer","")).strip()
                if norm(q["answer"]) not in norm(old):best["direct_answer"]=(old+"\n\nAssessment explanation: "+q["answer"]).strip()[:4000]
                best.setdefault("source_references",[]).append(q["citation"]);qa_enrich+=1
            elif titlekey not in seen_questions:
                mod=module_guess(q["question"]+" "+q["answer"],q["kind"],bundle)
                concepts.append(make_record("lab_assessment_"+q["kind"]+"_"+str(q["n"]).zfill(2),q["question"],q["answer"],mod,str(titles.get(str(mod),titles.get(mod,"Module "+str(mod)))),q["citation"],"assessment"))
                seen_questions.add(titlekey);qa_add+=1
        # Add all readable learner-facing SCORM HTML and QRG HTML as chunked knowledge.
        sources=[];added_course=[];added_qrg=[];seen_text=set()
        def add_source(raw,source,kind,records):
            added=0
            for heading,body in html_sections(raw,Path(source).name)[0]:
                key=norm(heading+" "+body)
                if len(key)<100 or key in seen_text:continue
                seen_text.add(key)
                mod=module_guess(heading+" "+body[:300],source,bundle)
                mt=str(titles.get(str(mod),titles.get(mod,"Module "+str(mod))))
                cid="lab_"+("qrg_" if kind=="qrg" else "course_")+str(len(records)+1).zfill(4)
                rec=make_record(cid,heading,body,mod,mt,("Quick Reference Guide" if kind=="qrg" else "SCORM course content")+" — "+source+" — "+heading,kind)
                records.append(rec);concepts.append(rec);added+=1
            return added
        qrg_count=add_source(QRG.read_text(encoding="utf-8",errors="replace"),QRG.name,"qrg",added_qrg)
        course_count=0
        for name in names:
            low=name.lower()
            if low.startswith("ai-tutor/") or "/ai-tutor/" in low or not low.endswith((".html",".htm",".xhtml")):continue
            raw=zin.read(name).decode("utf-8",errors="replace"); secs,p=html_sections(raw,name)
            visible=sum(len(t) for _,t in p.blocks)
            if visible<160:continue
            sources.append({"path":name,"visible_chars":visible,"title":p.title or Path(name).name})
            course_count+=add_source(raw,name,"course",added_course)
        bundle["concepts"]=concepts
        bundle["ai_tutor_lab_experiment"]={"version":"full-course-knowledge-v4","sources":["readable SCORM HTML","Quick Reference Guide HTML","trainer guide pre/post instructor answer-key Q&A only"],"runtime":"lab-only query-coverage reranker; no hosted inference; no network calls; no WebAssembly"}
        newdata="window.__CS_AI_TUTOR_DATA__ = "+json.dumps(bundle,ensure_ascii=False,separators=(",",":"))+";\n"
        candidate_tutor=patch_lab_query_coverage(tutor)
        for d,content,jsdata in ((WORK/"baseline",data,tutor),(WORK/"candidate",newdata,candidate_tutor)):
            (d/"tutor.js").write_text(jsdata,encoding="utf-8");(d/"tutor-data.js").write_text(content,encoding="utf-8")
        with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as zout:
            for info in zin.infolist():
                if info.filename==dpath: payload=newdata.encode("utf-8")
                elif info.filename==tpath: payload=candidate_tutor.encode("utf-8")
                else: payload=zin.read(info.filename)
                zout.writestr(info,payload)
        entries=[{"path":x.filename,"size":x.file_size} for x in zin.infolist()]
    summary={"experiment":"full-course-knowledge-v4","baseline_package":PACKAGE.name,"candidate_package":OUT.name,"baseline_package_sha256":hashlib.sha256(PACKAGE.read_bytes()).hexdigest(),"baseline_package_bytes":PACKAGE.stat().st_size,"candidate_package_bytes":OUT.stat().st_size,"baseline_tutor_data_bytes":len(data.encode()),"candidate_tutor_data_bytes":len(newdata.encode()),"baseline_concept_count":base_count,"candidate_concept_count":len(concepts),"assessment_qas_parsed":{"pre":10,"post":20},"assessment_qas_added_as_new_concepts":qa_add,"existing_concepts_enriched_by_assessment_qas":qa_enrich,"quick_reference_concepts_added":qrg_count,"course_html_concepts_added":course_count,"course_html_sources":sources,"qrg_source":QRG.name,"assessment_source_policy":"Only pre/post instructor answer-key Q&A; no trainer guide module Q&A or other guide content","runtime_changed":True,"runtime_patch":"Lab-only IDF-weighted query-coverage penalty to discourage high-scoring answers that omit distinctive question terms","source_runtime_bytes":len(tutor.encode()),"candidate_runtime_bytes":len(candidate_tutor.encode()),"changed_package_entries":[tpath,dpath],"hosted_inference_added":False,"webassembly_added":False,"original_zip_modified":False,"tutor_runtime_path":tpath,"tutor_data_path":dpath,"zip_entries":entries,"added_qrg_titles":[{"title":x["title"],"citation":x["citation"]} for x in added_qrg],"added_course_titles":[{"title":x["title"],"citation":x["citation"],"module":x["module_number"]} for x in added_course],"assessment_titles":[{"assessment":x["kind"],"question_number":x["n"],"question":x["question"]} for x in qas]}
    Path("ai-tutor-lab/experiment-summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k not in ("zip_entries","added_qrg_titles","added_course_titles","assessment_titles")},ensure_ascii=False,indent=2))
if __name__=="__main__":
    try:main()
    except Exception as e:print("AI Tutor lab build failed: "+str(e),file=sys.stderr);raise
