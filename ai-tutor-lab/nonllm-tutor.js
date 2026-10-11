(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.CSNonLLMTutor = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const STOP = new Set(("a an the and or but if then of to in on at by for with do does did have has had is are was were be been being what which who when where why how this that these those you your my me we us our it its they them their can could would should will as from about into than so not nor too very just only also still even any some all every most more less few please tell explain describe following".split(/\s+/)));
  const ALIAS_GROUPS = [
    { phrases: ["directory traversal", "traverse a directory", "traversing a directory", "change into a directory", "enter a directory", "directory execute permission", "directory search permission", "use cd into"], terms: ["execute", "search", "traversal", "permission", "directory", "cd"] },
    { phrases: ["supplementary group", "additional group", "keep existing group memberships", "without removing existing memberships"], terms: ["usermod", "-aG", "append", "group", "membership"] },
    { phrases: ["gracefully stop", "stop a process gracefully", "stuck process", "before forcing it"], terms: ["SIGTERM", "kill -15", "termination", "process"] },
    { phrases: ["remote ssh server", "lock myself out", "locking myself out", "remote access safety"], terms: ["ufw", "allow OpenSSH", "firewall", "SSH"] },
    { phrases: ["persistent mount", "mounting with uuid", "uuid based mount", "automatically mount"], terms: ["UUID", "fstab", "ext4", "mount"] },
    { phrases: ["pci bus", "devices connected to pci", "pci devices"], terms: ["lspci", "hardware", "device"] },
    { phrases: ["static ip configuration", "netplan static ip", "configured address", "network interface address"], terms: ["Netplan", "labnet0", "192.168.200.10/24", "90-virtual-lab.yaml"] },
    { phrases: ["root login", "direct root login", "ssh root login", "disable root login"], terms: ["PermitRootLogin no", "99-hardening.conf", "sshd", "SSH"] },
    { phrases: ["yaml parsing error", "yaml syntax error", "yaml indentation", "netplan yaml"], terms: ["tabs", "spaces", "indentation", "90-virtual-lab.yaml", "Netplan"] },
    { phrases: ["append log records", "add to the existing log", "without deleting old", "append output"], terms: [">>", "append", "redirection", "log"] },
    { phrases: ["case insensitive", "ignore case", "last 20 matches"], terms: ["grep -i", "tail -n 20", "syslog"] },
    { phrases: ["syntax check sudoers", "edit sudoers safely", "sudoers syntax validation"], terms: ["visudo", "syntax validation", "sudoers"] }
  ];
  function normalize(value) {
    return String(value || "").toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[’‘]/g, "'").replace(/\s+/g, " ").trim();
  }
  function tokenize(value) {
    const raw = normalize(value);
    const tokens = raw.match(/(?:--?[a-z0-9][a-z0-9-]*|\/(?:[a-z0-9_.-]+\/)*[a-z0-9_.-]+|[a-z0-9_+#]+(?:[./:-][a-z0-9_+#-]+)*)/gi) || [];
    const expanded = [];
    for (const token of tokens) {
      const t = token.toLowerCase();
      if ((t.length > 1 || /^-\w/.test(t)) && !STOP.has(t)) expanded.push(t);
      for (const p of t.split(/[\/.:#-]+/).filter(Boolean)) if (p.length > 1 && !STOP.has(p)) expanded.push(p);
    }
    return [...new Set(expanded)];
  }
  function aliasesFor(question, learnedRules) {
    const n = normalize(question), values = [];
    for (const group of ALIAS_GROUPS) if (group.phrases.some(p => n.includes(normalize(p)))) values.push(...group.terms);
    const rules = learnedRules && Array.isArray(learnedRules.aliases) ? learnedRules.aliases : [];
    for (const rule of rules) if (rule && rule.phrase && n.includes(normalize(rule.phrase))) values.push(...(rule.terms || []));
    return values;
  }
  function classifyIntent(question, learnedRules) {
    const q = normalize(question);
    if (/\b(compare|comparison|difference|different from|versus|vs\.?)\b/.test(q)) return "compare";
    if (/^(why|what is the reason|for what reason)\b/.test(q)) return "why";
    if (/^(how|what steps|in what way|what is the process)\b/.test(q)) return "how";
    if (/\b(troubleshoot|troubleshooting|fix|resolve|debug|error|not working|fails to)\b/.test(q)) return "troubleshoot";
    if (/\b(example|sample|demonstrate|show me)\b/.test(q)) return "example";
    if (/\b(command|configuration file|config file|file path|exact path|directive|ip address|which file|which setting|which option|which port)\b/.test(q)) return "identify";
    if (/^(where|when)\b/.test(q)) return q.startsWith("where") ? "where" : "when";
    if (/^(which|who|what|name|identify|list|define)\b/.test(q)) return /^(list|name)\b/.test(q) || /\bwhat fields\b/.test(q) ? "list" : "explain";
    const learned = learnedRules && Array.isArray(learnedRules.question_stems) ? learnedRules.question_stems : [];
    let best = null;
    for (const item of learned) {
      const prefix = normalize(item.prefix || "");
      if (prefix && q.startsWith(prefix) && (!best || prefix.length > best.prefix.length)) best = { prefix, intent: item.intent };
    }
    if (best && ["why", "how", "compare", "troubleshoot", "example", "identify", "where", "when", "list", "explain"].includes(best.intent)) return best.intent;
    return "explain";
  }
  function recordText(c) {
    return [c.title, c.section_title, c.lesson_title, c.module_title, c.direct_answer, (c.keywords || []).join(" "), (c.query_anchors || []).join(" "), (c.structured_points || []).join(" "), (c.source_references || []).join(" ")].filter(Boolean).join(" ");
  }
  function createIndex(concepts, learnedRules) {
    const records = Array.isArray(concepts) ? concepts : [];
    const docs = records.map((c, i) => {
      const title = tokenize([c.title, c.section_title, c.lesson_title, c.module_title].filter(Boolean).join(" "));
      const keywords = tokenize((c.keywords || []).join(" "));
      const anchors = tokenize((c.query_anchors || []).join(" "));
      const body = tokenize([c.direct_answer, ...(c.structured_points || [])].filter(Boolean).join(" "));
      const tf = Object.create(null);
      const add = (list, weight) => list.forEach(t => { tf[t] = (tf[t] || 0) + weight; });
      add(body, 1); add(keywords, 1.5); add(title, 2.7); add(anchors, 3.6);
      const length = body.length + keywords.length * 1.5 + title.length * 2.7 + anchors.length * 3.6;
      return { c, i, tf, length, titleSet: new Set(title), keywordSet: new Set(keywords), anchorSet: new Set(anchors), raw: recordText(c), anchorsRaw: (c.query_anchors || []).map(normalize) };
    });
    const df = Object.create(null);
    for (const d of docs) for (const term of Object.keys(d.tf)) df[term] = (df[term] || 0) + 1;
    const avgLength = docs.reduce((n, d) => n + d.length, 0) / Math.max(1, docs.length);
    const idf = Object.create(null);
    for (const term of Object.keys(df)) idf[term] = Math.log(1 + (docs.length - df[term] + 0.5) / (df[term] + 0.5));
    return { docs, df, idf, avgLength, learnedRules: learnedRules || {}, recordCount: docs.length };
  }
  function rank(question, index, options) {
    const limit = Math.max(1, Math.min(8, options && options.topK || 5));
    if (!index || !Array.isArray(index.docs) || !index.docs.length) return [];
    const originalTerms = tokenize(question);
    if (!originalTerms.length) return [];
    const aliasTerms = tokenize(aliasesFor(question, index.learnedRules).join(" "));
    const allTerms = [...new Set(originalTerms.concat(aliasTerms))], qnorm = normalize(question), qwords = new Set(originalTerms);
    const literals = [];
    const literalPatterns = [
      /\/(?:[A-Za-z0-9_.-]+\/)*[A-Za-z0-9_.-]+/g,
      /\bPermitRootLogin\s+no\b/ig,
      /\b\d{1,3}(?:\.\d{1,3}){3}(?:\/\d{1,2})?\b/g,
      /\b[A-Za-z][A-Za-z0-9_.-]*\.(?:conf|yaml|yml|json|ini|service)\b/ig,
      /\b(?:grep|tail|usermod|chown|chmod|lspci|ip|ufw|mount|visudo|systemctl)\s+(?:-[A-Za-z]+\s+)?[^\s,;?]+/ig
    ];
    for (const rx of literalPatterns) for (const m of qnorm.matchAll(rx)) literals.push(normalize(m[0]));
    const scored = index.docs.map(d => {
      let score = 0;
      for (const term of allTerms) {
        const f = d.tf[term] || 0;
        if (!f) continue;
        const termIdf = index.idf[term] || Math.log(1 + index.docs.length);
        score += termIdf * (f * 2.2 / (f + 1.2 * (1 - 0.72 + 0.72 * d.length / Math.max(1, index.avgLength))));
        if (d.titleSet.has(term)) score += termIdf * 1.4;
        if (d.keywordSet.has(term)) score += termIdf * 0.65;
        if (d.anchorSet.has(term)) score += termIdf * 1.8;
      }
      const exactAnchor = d.anchorsRaw.some(a => a && a === qnorm);
      if (exactAnchor) score += 18;
      else if (d.anchorsRaw.some(a => a && qnorm.length > 12 && (a.includes(qnorm) || qnorm.includes(a)))) score += 5.5;
      if (qnorm.length > 10 && normalize(d.raw).includes(qnorm)) score += 6;
      for (const lit of literals) if (lit.length > 2 && normalize(d.raw).includes(lit)) score += 8;
      const meaningful = [...qwords];
      const matched = meaningful.filter(t => d.tf[t]);
      const coverage = matched.length / Math.max(1, meaningful.length);
      const expandedMatched = allTerms.filter(t => d.tf[t]).length / Math.max(1, allTerms.length);
      score *= 0.35 + 0.65 * Math.sqrt(Math.max(0, coverage));
      if (aliasTerms.length && expandedMatched > 0.2) score *= 1 + Math.min(0.35, expandedMatched * 0.18);
      return { concept: d.c, score, coverage, exactAnchor, _doc: d };
    }).sort((a, b) => b.score - a.score || b.coverage - a.coverage || a._doc.i - b._doc.i);
    return scored.slice(0, limit).map(({ _doc, ...item }) => item);
  }
  function splitSentences(text) {
    const source = String(text || "").replace(/\r/g, "\n").replace(/[ \t]+/g, " ").trim();
    if (!source) return [];
    return source.split(/(?<=[!?])\s+|(?<=\.)\s+(?=[A-Z0-9/])/g).map(s => s.trim()).filter(s => s.length >= 20);
  }
  function sentenceScore(sentence, question, intent, index) {
    const terms = tokenize(question), st = new Set(tokenize(sentence));
    let score = 0;
    for (const t of terms) if (st.has(t)) score += (index.idf[t] || 1) * 1.2;
    if (intent === "why" && /\b(because|reason|purpose|so that|in order to|prevents?|allows?|ensures?|therefore|as a result)\b/i.test(sentence)) score += 2.8;
    if (intent === "how" && /\b(first|then|before|after|run|use|edit|add|set|configure|create|check|verify|enable|allow|mount|execute|install|open)\b/i.test(sentence)) score += 2;
    if (intent === "compare" && /\b(whereas|while|unlike|difference|instead|however|both|rather than)\b/i.test(sentence)) score += 2.5;
    if (intent === "troubleshoot" && /\b(check|verify|inspect|error|fix|correct|validate|syntax|indentation|restart)\b/i.test(sentence)) score += 2;
    if (intent === "explain" && /\b(is|are|means|refers to|allows|provides|consists of|defined as)\b/i.test(sentence)) score += 1;
    if (sentence.length < 35) score *= 0.55;
    if (sentence.length > 420) score *= 0.6;
    if (/^(learning objective|in this lesson|in this module|question \d+)\b/i.test(sentence)) score *= 0.2;
    return score;
  }
  function cleanSentence(s) { return String(s || "").replace(/\s+/g, " ").replace(/^[\s•*-]+/, "").trim(); }
  function answer(question, index, options) {
    const intent = classifyIntent(question, index && index.learnedRules), ranked = rank(question, index, { topK: options && options.topK || 6 }), top = ranked[0];
    if (!top || top.score < 0.65 || (top.coverage < 0.08 && !top.exactAnchor)) {
      return { category: "OUT_OF_COURSE", answer: "I could not find enough relevant evidence in this course to answer confidently. Try using the course's technical terms or name the command, file, or lesson you are asking about.", intent, score: top ? top.score : 0, concept: null, sources: [], ranked: ranked.slice(0, 3).map(r => ({ title: r.concept.title, score: r.score, coverage: r.coverage })) };
    }
    const best = top.concept, bestAnswer = String(best.direct_answer || "").trim(), qnorm = normalize(question);
    const exact = (best.query_anchors || []).some(a => normalize(a) === qnorm);
    const preparedAnswer = /^\s*Correct answer:/i.test(bestAnswer);
    const candidateRows = [];
    for (const row of ranked.slice(0, 4)) {
      const c = row.concept;
      if (row.score < top.score * 0.58 && row !== top) continue;
      const all = [];
      if (Array.isArray(c.structured_points)) all.push(...c.structured_points.map(cleanSentence));
      all.push(...splitSentences(c.direct_answer || ""));
      for (const s of [...new Set(all.map(cleanSentence).filter(x => x.length >= 20))]) {
        const sc = sentenceScore(s, question, intent, index) + (row === top ? 1.4 : 0);
        if (sc > 0) candidateRows.push({ sentence: s, score: sc, record: c, rankScore: row.score });
      }
    }
    candidateRows.sort((a, b) => b.score - a.score);
    let selected = [];
    const seen = new Set();
    for (const row of candidateRows) {
      const key = normalize(row.sentence);
      if (seen.has(key)) continue;
      if (selected.length && selected.every(x => x.record.id !== row.record.id) && row.rankScore < top.score * 0.72) continue;
      seen.add(key); selected.push(row);
      if (selected.length >= (intent === "how" || intent === "troubleshoot" ? 3 : 2)) break;
    }
    if (!selected.length) selected = [{ sentence: cleanSentence(bestAnswer).slice(0, 500), record: best, score: top.score }];
    selected.sort((a, b) => (a.record === best ? -1 : 1) - (b.record === best ? -1 : 1));
    let response;
    if (preparedAnswer) {
      const m = bestAnswer.match(/^\s*Correct answer:\s*([^.]*)\.?\s*(.*)$/i);
      response = m ? "The correct answer identified by the course is " + m[1].trim().replace(/[.]$/, "") + (m[2] ? ". " + m[2].trim() : ".") : bestAnswer;
    } else {
      const body = selected.map(x => cleanSentence(x.sentence)).filter(Boolean).join(" ");
      if (intent === "why") response = "The key reason is: " + body;
      else if (intent === "how") response = "To approach this task, use the course-supported procedure: " + body;
      else if (intent === "compare") response = "The key distinction is: " + body;
      else if (intent === "troubleshoot") response = "Start with the course-supported checks and corrections: " + body;
      else if (intent === "identify" || intent === "where") response = "The course identifies the relevant item as follows: " + body;
      else if (intent === "list") response = "The course identifies these relevant items: " + body;
      else if (intent === "example") response = "A course-supported example is: " + body;
      else if (intent === "when") response = "The course indicates this applies in the following situation: " + body;
      else response = "In this course context: " + body;
    }
    response = response.replace(/\s+/g, " ").trim();
    if (response.length > 1100) response = response.slice(0, 1097).replace(/\s+\S*$/, "") + "...";
    const sources = [];
    for (const row of selected) {
      const c = row.record;
      const label = [c.module_title, c.lesson_title, c.section_title || c.title, c.citation].filter(Boolean).join(" — ");
      if (label && !sources.includes(label)) sources.push(label);
    }
    if (!sources.length) {
      const label = [best.module_title, best.lesson_title, best.section_title || best.title, best.citation].filter(Boolean).join(" — ");
      if (label) sources.push(label);
    }
    return { category: "IN_COURSE", answer: response, intent, score: top.score, coverage: top.coverage, concept: best, sources: sources.slice(0, 3), exactAnchor: exact, ranked: ranked.slice(0, 4).map(r => ({ title: r.concept.title || r.concept.section_title, score: r.score, coverage: r.coverage })) };
  }
  return { normalize, tokenize, classifyIntent, createIndex, rank, answer, ALIAS_GROUPS };
});
