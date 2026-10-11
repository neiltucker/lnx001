(function(root,factory){
  const api=factory();
  if(typeof module!=="undefined"&&module.exports) module.exports=api;
  if(root) root.CSLocalTutorRag=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
  "use strict";
  const STOP=new Set(("a an the and or but if then of to in on at by for with do does did have has had is are was were be been being what which who when where why how this that these those you your my me we us our it its they them their can could would should will as from about into than so not nor too very just only also still even any some all every most more less few".split(/\s+/)));
  function normalize(s){return String(s||"").toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9_+#./:-]+/g," ").replace(/\s+/g," ").trim();}
  function tokenize(s){return normalize(s).split(" ").filter(x=>x.length>1&&!STOP.has(x));}
  function distinct(a){return [...new Set(a)];}
  function docText(c){return [c.title,c.section_title,c.lesson_title,c.module_title,c.direct_answer,(c.keywords||[]).join(" "),(c.query_anchors||[]).join(" ")].filter(Boolean).join(" ");}
  function rank(question,concepts,options={}){
    const limit=Math.max(1,Math.min(8,options.topK||4)),q=tokenize(question);
    if(!q.length||!Array.isArray(concepts)||!concepts.length)return [];
    const docs=concepts.map((c,i)=>{
      const titleTokens=tokenize([c.title,c.section_title].filter(Boolean).join(" "));
      const kwTokens=tokenize((c.keywords||[]).join(" "));
      const anchorTokens=tokenize((c.query_anchors||[]).join(" "));
      const all=[...titleTokens,...kwTokens,...anchorTokens,...tokenize(c.direct_answer||"")];
      const tf=Object.create(null);for(const t of all)tf[t]=(tf[t]||0)+1;
      return {c,i,titleTokens:new Set(titleTokens),kwTokens:new Set(kwTokens),anchorTokens:new Set(anchorTokens),tf,length:all.length};
    });
    const avgLen=docs.reduce((s,d)=>s+d.length,0)/Math.max(1,docs.length),df=Object.create(null);
    for(const d of docs)for(const t of new Set(Object.keys(d.tf)))df[t]=(df[t]||0)+1;
    const nq=distinct(q),qnorm=normalize(question);
    return docs.map(d=>{
      let score=0;
      for(const t of nq){
        const f=d.tf[t]||0;if(!f)continue;
        const idf=Math.log(1+(docs.length-(df[t]||0)+0.5)/((df[t]||0)+0.5));
        score+=idf*(f*2.5/(f+1.5*(1-0.68+0.68*d.length/Math.max(1,avgLen))));
        if(d.titleTokens.has(t))score+=idf*1.6;
        if(d.kwTokens.has(t))score+=idf*0.7;
        if(d.anchorTokens.has(t))score+=idf*1.1;
      }
      const anchors=(d.c.query_anchors||[]).map(normalize);
      if(anchors.some(a=>a&&qnorm===a))score+=18;
      else if(anchors.some(a=>a&&qnorm.length>10&&(a.includes(qnorm)||qnorm.includes(a))))score+=8;
      const coverage=nq.filter(t=>d.tf[t]).length/Math.max(1,nq.length);
      score*=Math.pow(Math.max(0.10,coverage),1.35);
      return {concept:d.c,score,coverage};
    }).sort((a,b)=>b.score-a.score||b.coverage-a.coverage||String(a.concept.id||"").localeCompare(String(b.concept.id||""))).slice(0,limit);
  }
  function buildPrompt(question,ranked,history=[]){
    const sources=(ranked||[]).slice(0,3).map((r,i)=>{
      const c=r.concept||r,source=[c.module_title,c.lesson_title,c.section_title||c.title,c.citation].filter(Boolean).join(" / ");
      let answer=String(c.direct_answer||"").replace(/\s+/g," ").trim();
      if(answer.length>420)answer=answer.slice(0,417)+"...";
      return "["+(i+1)+"] "+source+"\n"+answer;
    });
    const evidence=sources.join("\n\n").slice(0,1800);
    const prior=(history||[]).slice(-4).map(m=>String(m.role||"user")+": "+String(m.text||"").slice(0,180)).join("\n");
    return ["You are a helpful tutor for a technical training course.","Answer the learner's question using the COURSE EVIDENCE below. Explain the concept in your own words instead of copying a whole passage.","Preserve exact commands, file paths, IP addresses, options, and configuration directives when the evidence supplies them.","You may combine compatible facts from multiple evidence passages. Do not invent steps, commands, values, or facts that are not supported by the evidence.","If the evidence is insufficient, say that you could not find enough information in the course material to answer confidently.","Keep the answer clear and practical. Use a short numbered procedure when the learner asks how to do a task.",prior?"RECENT CONVERSATION:\n"+prior:"","COURSE EVIDENCE:\n"+(evidence||"(No relevant evidence found.)"),"LEARNER QUESTION:\n"+question,"TUTOR ANSWER:"].filter(Boolean).join("\n\n");
  }
  return {rank,buildPrompt,normalize,tokenize};
});
