#!/usr/bin/env python3
import hashlib, html, json, re, sys, zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path.cwd()
PACKAGE=ROOT/"LNX-001_EN_SCORM2004.zip"
GUIDE=ROOT/"LNX-001_EN_TrainerPreparationGuide.txt"
QRG=ROOT/"Day-01-QuickReference.html"
OUT=ROOT/"LNX-001_EN_SCORM2004_AI-TUTOR-LAB.zip"
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
    words=re.findall(r"[A-Za-z][A-Za-z0-9_+#./-]{2,}",title+" "+answer)
    counts=Counter(x.lower() for x in words if x.lower() not in STOP)
    kw=[x for x,_ in counts.most_common(30)]
    anchors=[title,"Explain "+title]
    if kind=="qrg":anchors.append("How do I "+title[:1].lower()+title[1:]+"?")
    elif kind=="assessment":anchors.append("Help me understand "+title)
    if len(answer)>25:anchors.append(re.split(r"(?<=[.!?])\s+",answer)[0][:180])
    ctype="framework" if kind=="qrg" else ("comparison" if re.search(r"\b(compare|difference|versus)\b",title,re.I) else "definition")
    return {"id":i,"module_number":mod,"module_title":mtitle,"lesson_title":citation,"section_title":title,"title":title[:250],"concept_type":ctype,"direct_answer":answer[:3500],"structured_points":[],"citation":citation,"keywords":kw,"query_anchors":list(dict.fromkeys(anchors))[:5]}
def parse_bundle(js):
    marker="window.__CS_AI_TUTOR_DATA__";at=js.find(marker)
    if at<0:raise ValueError("No window.__CS_AI_TUTOR_DATA__ assignment in SCORM")
    eq=js.find("=",at+len(marker));semi=js.rfind(";")
    return json.loads(js[eq+1:semi if semi>eq else None].strip())
def assessment_records(guide):
    normalized=guide.replace("\\u00a0"," ").replace("\\u2014","-").replace("\\u2013","-")
    a=re.search(r"Pre-Assessment\\s*-\\s*Instructor Answer Key",normalized,re.I)
    b=re.search(r"Post-Assessment\\s*-\\s*Student Handout",normalized,re.I)
    c=re.search(r"Post-Assessment\\s*-\\s*Instructor Answer Key",normalized,re.I)
    if not(a and b and c):
        raise ValueError("Missing expected instructor answer-key headings: pre="+str(bool(a))+", post-student="+str(bool(b))+", post-key="+str(bool(c)))
    guide=normalized
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
        bundle["ai_tutor_lab_experiment"]={"version":"full-course-knowledge-v1","sources":["readable SCORM HTML","Quick Reference Guide HTML","trainer guide pre/post instructor answer-key Q&A only"],"runtime":"unchanged JavaScript; no hosted inference; no network calls; no WebAssembly"}
        newdata="window.__CS_AI_TUTOR_DATA__ = "+json.dumps(bundle,ensure_ascii=False,separators=(",",":"))+";\n"
        for d,content in ((WORK/"baseline",data),(WORK/"candidate",newdata)):
            (d/"tutor.js").write_text(tutor,encoding="utf-8");(d/"tutor-data.js").write_text(content,encoding="utf-8")
        with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as zout:
            for info in zin.infolist():zout.writestr(info,newdata.encode() if info.filename==dpath else zin.read(info.filename))
        entries=[{"path":x.filename,"size":x.file_size} for x in zin.infolist()]
    summary={"experiment":"full-course-knowledge-v1","baseline_package":PACKAGE.name,"candidate_package":OUT.name,"baseline_package_sha256":hashlib.sha256(PACKAGE.read_bytes()).hexdigest(),"baseline_package_bytes":PACKAGE.stat().st_size,"candidate_package_bytes":OUT.stat().st_size,"baseline_tutor_data_bytes":len(data.encode()),"candidate_tutor_data_bytes":len(newdata.encode()),"baseline_concept_count":base_count,"candidate_concept_count":len(concepts),"assessment_qas_parsed":{"pre":10,"post":20},"assessment_qas_added_as_new_concepts":qa_add,"existing_concepts_enriched_by_assessment_qas":qa_enrich,"quick_reference_concepts_added":qrg_count,"course_html_concepts_added":course_count,"course_html_sources":sources,"qrg_source":QRG.name,"assessment_source_policy":"Only pre/post instructor answer-key Q&A; no trainer guide module Q&A or other guide content","runtime_changed":False,"hosted_inference_added":False,"webassembly_added":False,"original_zip_modified":False,"tutor_runtime_path":tpath,"tutor_data_path":dpath,"zip_entries":entries,"added_qrg_titles":[{"title":x["title"],"citation":x["citation"]} for x in added_qrg],"added_course_titles":[{"title":x["title"],"citation":x["citation"],"module":x["module_number"]} for x in added_course],"assessment_titles":[{"assessment":x["kind"],"question_number":x["n"],"question":x["question"]} for x in qas]}
    Path("ai-tutor-lab/experiment-summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k not in ("zip_entries","added_qrg_titles","added_course_titles","assessment_titles")},ensure_ascii=False,indent=2))
if __name__=="__main__":
    try:main()
    except Exception as e:print("AI Tutor lab build failed: "+str(e),file=sys.stderr);raise
