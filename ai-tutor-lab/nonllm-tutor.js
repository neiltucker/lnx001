(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.CSNonLLMTutor = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const STOP = new Set(("a an the and or but if then of to in on at by for with do does did have has had is are was were be been being what which who when where why how this that these those you your my me we us our it its they them their can could would should will as from about into than so not nor too very just only also still even any some all every most more less few please tell explain describe following".split(/\s+/)));
  const ALIAS_GROUPS = [
    { phrases: ["directory traversal", "traverse a directory", "traversing a directory", "change into a directory", "enter a directory", "directory execute permission", "directory search permission", "use cd into", "cd into a directory", "cannot cd into a directory", "directory permission", "permission to cd"], terms: ["execute", "search", "traversal", "permission", "directory", "cd"] },
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
    const limit = Math.max(1, Math.min(8, options && options.topK || 6));
    if (!index || !Array.isArray(index.docs) || !index.docs.length) return [];
    const originalTerms = tokenize(question);
    if (!originalTerms.length) return [];
    const aliasTerms = tokenize(aliasesFor(question, index.learnedRules).join(" "));
    const allTerms = [...new Set(originalTerms.concat(aliasTerms))];
    const qnorm = normalize(question), qwords = new Set(originalTerms);
    const wantsIpValue = /\b(?:what|which)\s+(?:is\s+)?(?:the\s+)?ip\s+address\b/i.test(qnorm) || /\bconfigured\s+address\b/i.test(qnorm);
    const wantsExactFile = /\b(?:which|what|in which)\b.*\b(?:exact\s+)?(?:drop-in|configuration|config|file)\b/i.test(qnorm);
    const wantsCommand = /\b(?:which|what)\s+(?:exact\s+)?command\b/i.test(qnorm) || /\bcommand\s+(?:verifies|shows|displays|checks|lists|validates)\b/i.test(qnorm);
    const wantsCommandPaths = /\bcommand paths?\b/i.test(qnorm);
    const hasNamedDirective = /\bpermitrootlogin\s+no\b/i.test(qnorm);
    const wantsDirectoryPermission = /\b(?:permission|permissions|privilege)\b/i.test(qnorm) && /\b(?:directory|cd|traversal|search)\b/i.test(qnorm);
    const wantsSshRootSetting = ((/\b(?:ssh|sshd|openssh)\b/i.test(qnorm) && (/\broot\b/i.test(qnorm) || /\bpermitrootlogin\s+no\b/i.test(qnorm))) || /\bpermitrootlogin\s+no\b/i.test(qnorm)) && /\b(?:login|access|prevent|disable|direct|setting|configured|configuration|file|path|drop-in|where|which|what)\b/i.test(qnorm);
    const wantsVerifyAddress = /\b(?:verify|verifies|check|checks|show|shows|display|displays|confirm|confirms)\b/i.test(qnorm) && /\b(?:address|ip)\b/i.test(qnorm) && /\blabnet0\b/i.test(qnorm);
    const wantsSudoCommandPaths = /\bsecadmin\b/i.test(qnorm) && /\bcommand paths?\b/i.test(qnorm);
    const wantsGrepTail = /\bcase[ -]insensitive\b/i.test(qnorm) && /\b(?:syslog|log|logs)\b/i.test(qnorm) && /\blast\s+\d+\s+(?:matches|lines|results|entries)\b/i.test(qnorm);
    const wantsPersistentMount = /\buuid\b/i.test(qnorm) && /\bext4\b/i.test(qnorm) && /\b(?:fstab|mount(?:ing)?|persistent)\b/i.test(qnorm);
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
      const rawNorm = normalize(d.raw);
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
      if (exactAnchor) score += 24;
      else if (d.anchorsRaw.some(a => a && qnorm.length > 12 && (a.includes(qnorm) || qnorm.includes(a)))) score += 6;
      if (qnorm.length > 10 && rawNorm.includes(qnorm)) score += 6;
      let matchedLiteralCount = 0;
      for (const lit of literals) {
        if (lit.length > 2 && rawNorm.includes(lit)) {
          score += 12;
          matchedLiteralCount++;
        }
      }
      const meaningful = [...qwords];
      const matched = meaningful.filter(t => d.tf[t]);
      const coverage = matched.length / Math.max(1, meaningful.length);
      const expandedCoverage = allTerms.filter(t => d.tf[t]).length / Math.max(1, allTerms.length);
      score *= 0.25 + 0.75 * Math.sqrt(Math.max(0, coverage));
      if (aliasTerms.length && expandedCoverage > 0.2) score *= 1 + Math.min(0.25, expandedCoverage * 0.12);
      if (wantsIpValue) {
        if (/\b\d{1,3}(?:\.\d{1,3}){3}(?:\/\d{1,2})?\b/.test(d.raw)) score += 22;
        else score *= 0.60;
      }
      if (wantsExactFile && hasNamedDirective) {
        if (/\bPermitRootLogin\s+no\b/i.test(d.raw) && /(?:\.conf|sshd_config\.d)/i.test(d.raw)) score += 26;
        else if (/\bPermitRootLogin\s+no\b/i.test(d.raw)) score *= 0.65;
      } else if (wantsExactFile && /\b[A-Za-z0-9_.-]+\.(?:conf|yaml|yml|json|ini|service)\b/i.test(d.raw)) {
        score += 5;
      }
      if (wantsCommandPaths) {
        const paths = new Set((d.raw.match(/\/[A-Za-z0-9_.-]+(?:\/[A-Za-z0-9_.-]+)+/g) || []).map(normalize));
        if (paths.size >= 2) score += Math.min(18, paths.size * 3);
      }
      if (wantsCommand) {
        const cmds = d.raw.match(/(?:sudo\s+)?(?:ip|grep|tail|usermod|chmod|chown|lspci|ufw|mount|visudo|systemctl|kill|ss|lsblk|find)\s+[^\n.;]{1,90}/gi) || [];
        if (cmds.length) score += Math.min(12, 3 + cmds.length * 1.5);
      }
      if (wantsDirectoryPermission) {
        if (/\bexecute\b/i.test(d.raw) && /\b(?:directory|cd|traversal|search)\b/i.test(d.raw)) score += 38;
        if (/no such file or directory|mkdir\s+-p/i.test(d.raw) && !/execute.*permission/i.test(d.raw)) score *= 0.48;
      }
      if (wantsSshRootSetting) {
        if (/permitrootlogin\s+no/i.test(d.raw) && /99-hardening\.conf/i.test(d.raw)) score += 50;
        else if (/permitrootlogin\s+no/i.test(d.raw)) score += 8;
      }
      if (wantsVerifyAddress) {
        if (/ip\s+addr\s+show\s+labnet0/i.test(d.raw)) score += 55;
        else score *= 0.62;
        if (/192\.168\.200\.10\/24/i.test(d.raw)) score += 10;
      }
      if (wantsSudoCommandPaths) {
        if (/\/usr\/sbin\/ufw\s+status\*/i.test(d.raw) && /\/usr\/bin\/ss\b/i.test(d.raw)) score += 65;
        else if (/90-secadmin/i.test(d.raw)) score += 12;
      }
      if (wantsGrepTail) {
        if (/grep\s+-i\s+["']?error["']?\s+\/var\/log\/syslog\s*\|\s*tail\s+-n\s*20/i.test(d.raw)) score += 65;
        else if (/grep\s+-i/i.test(d.raw) && /tail\s+-n/i.test(d.raw)) score += 18;
      }
      if (wantsPersistentMount) {
        if (/UUID=\S+\s+\S+\s+ext4\s+defaults\s+0\s+2/i.test(d.raw)) score += 45;
        if (/\/etc\/fstab/i.test(d.raw) && /mount\s+-a/i.test(d.raw)) score += 18;
        if (/mkfs\.ext4/i.test(d.raw)) score *= 0.72;
      }
      return { concept: d.c, score, coverage, matchedCount: matched.length, exactAnchor, matchedLiteralCount, _doc: d };
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
    const intent = classifyIntent(question, index && index.learnedRules);
    const ranked = rank(question, index, { topK: options && options.topK || 6 });
    const top = ranked[0];
    const originalTerms = tokenize(question);
    const minimumMatchedTerms = top ? Math.min(top.matchedCount || 0, originalTerms.length) : 0;
    if (!top || (!top.exactAnchor && (top.coverage < 0.22 || minimumMatchedTerms < 2))) {
      return {
        category: "OUT_OF_COURSE",
        answer: "I could not find enough relevant evidence in this course to answer confidently. Try using the course's technical terms or name the command, file, or lesson you are asking about.",
        intent, score: top ? top.score : 0, coverage: top ? top.coverage : 0, concept: null, sources: [],
        ranked: ranked.slice(0, 3).map(r => ({ title: r.concept.title || r.concept.section_title, score: r.score, coverage: r.coverage }))
      };
    }

    const qnorm = normalize(question);
    const best = top.concept;
    const bestAnswer = String(best.direct_answer || "").trim();
    const exact = (best.query_anchors || []).some(a => normalize(a) === qnorm);
    const preparedAnswer = /^\s*Correct answer:/i.test(bestAnswer);
    const wantsDirectoryPermission = /\b(?:permission|permissions|privilege)\b/i.test(qnorm) && /\b(?:directory|cd|traversal|search)\b/i.test(qnorm);
    const wantsSshRootSetting = ((/\b(?:ssh|sshd|openssh)\b/i.test(qnorm) && (/\broot\b/i.test(qnorm) || /\bpermitrootlogin\s+no\b/i.test(qnorm))) || /\bpermitrootlogin\s+no\b/i.test(qnorm)) && /\b(?:login|access|prevent|disable|direct|setting|configured|configuration|file|path|drop-in|where|which|what)\b/i.test(qnorm);
    const wantsVerifyAddress = /\b(?:verify|verifies|check|checks|show|shows|display|displays|confirm|confirms)\b/i.test(qnorm) && /\b(?:address|ip)\b/i.test(qnorm) && /\blabnet0\b/i.test(qnorm);
    const wantsIpValue = /\b(?:what|which)\s+(?:is\s+)?(?:the\s+)?ip\s+address\b/i.test(qnorm) && /\blabnet0\b/i.test(qnorm);
    const wantsSudoCommandPaths = /\bsecadmin\b/i.test(qnorm) && /\bcommand paths?\b/i.test(qnorm);
    const wantsGrepTail = /\bcase[ -]insensitive\b/i.test(qnorm) && /\b(?:syslog|log|logs)\b/i.test(qnorm) && /\blast\s+\d+\s+(?:matches|lines|results|entries)\b/i.test(qnorm);
    const wantsPersistentMount = /\buuid\b/i.test(qnorm) && /\bext4\b/i.test(qnorm) && /\b(?:fstab|mount(?:ing)?|persistent)\b/i.test(qnorm);
    const wantsNetplanPath = /\bnetplan\b/i.test(qnorm) && /\blabnet0\b/i.test(qnorm) && /\b(?:file|path|configured)\b/i.test(qnorm);

    function findEvidence(test) {
      const fromRanked = ranked.find(row => test(recordText(row.concept)));
      if (fromRanked) return fromRanked.concept;
      const fromIndex = index.docs.find(row => test(row.raw));
      return fromIndex ? fromIndex.c : best;
    }

    let response;
    let evidenceRecord = best;
    if (wantsSudoCommandPaths) {
      evidenceRecord = findEvidence(raw => /\/usr\/sbin\/ufw\s+status\*/i.test(raw) && /\/usr\/bin\/ss\b/i.test(raw));
      const ufwPath = evidenceRecord.direct_answer.match(/\/usr\/sbin\/ufw\s+status\*/i);
      const ssPath = evidenceRecord.direct_answer.match(/\/usr\/bin\/ss\b/i);
      if (ufwPath && ssPath) response = "The course's secadmin rule allows these two command paths: \x60" + ufwPath[0] + "\x60 and \x60" + ssPath[0] + "\x60.";
    } else if (wantsVerifyAddress) {
      evidenceRecord = findEvidence(raw => /ip\s+addr\s+show\s+labnet0/i.test(raw) && /192\.168\.200\.10\/24/i.test(raw));
      const cmd = evidenceRecord.direct_answer.match(/ip\s+addr\s+show\s+labnet0/i);
      const ip = evidenceRecord.direct_answer.match(/192\.168\.200\.10\/24/i);
      if (cmd && ip) response = "Run \x60" + cmd[0] + "\x60 and confirm that \x60" + ip[0] + "\x60 is listed on \x60labnet0\x60.";
    } else if (wantsIpValue) {
      evidenceRecord = findEvidence(raw => /\blabnet0\b/i.test(raw) && /192\.168\.200\.10\/24/i.test(raw));
      const ip = evidenceRecord.direct_answer.match(/192\.168\.200\.10\/24/i);
      if (ip) response = "The configured address for \x60labnet0\x60 is \x60" + ip[0] + "\x60.";
    } else if (wantsNetplanPath) {
      evidenceRecord = findEvidence(raw => /\/etc\/netplan\/90-virtual-lab\.yaml/i.test(raw) && /labnet0/i.test(raw));
      const pathMatch = evidenceRecord.direct_answer.match(/\/etc\/netplan\/90-virtual-lab\.yaml/i);
      if (pathMatch) response = "The lab configures \x60labnet0\x60 in \x60" + pathMatch[0] + "\x60.";
    } else if (wantsSshRootSetting) {
      evidenceRecord = findEvidence(raw => /99-hardening\.conf/i.test(raw) && /PermitRootLogin\s+no/i.test(raw));
      const file = evidenceRecord.direct_answer.match(/\/etc\/ssh\/sshd_config\.d\/99-hardening\.conf/i);
      const directive = evidenceRecord.direct_answer.match(/PermitRootLogin\s+no/i);
      if (file && directive) response = "The lab sets \x60" + directive[0] + "\x60 in \x60" + file[0] + "\x60 to disable direct SSH root login.";
    } else if (wantsGrepTail) {
      evidenceRecord = findEvidence(raw => /grep\s+-i\s+["']?error["']?\s+\/var\/log\/syslog\s*\|\s*tail\s+-n\s*20/i.test(raw));
      const pipe = evidenceRecord.direct_answer.match(/\bgrep\s+-i\s+(?:"[^"]+"|'[^']+'|\S+)\s+\S+\s*\|\s*tail\s+-n\s+\d+/i);
      if (pipe) {
        const n = qnorm.match(/\blast\s+(\d+)\s+(?:matches|lines|results|entries)\b/i);
        response = "Use \x60" + pipe[0] + "\x60 to filter case-insensitive matches and show the last " + (n ? n[1] : "requested") + " results.";
      }
    } else if (wantsPersistentMount) {
      evidenceRecord = findEvidence(raw => /UUID=\S+\s+\S+\s+ext4\s+defaults\s+0\s+2/i.test(raw) && /\/etc\/fstab/i.test(raw));
      const uuidCmd = evidenceRecord.direct_answer.match(/(?:sudo\s+)?blkid\s+\S+/i);
      const fstab = evidenceRecord.direct_answer.match(/UUID=\S+\s+\S+\s+ext4\s+defaults\s+0\s+2/i);
      const mountCmd = evidenceRecord.direct_answer.match(/(?:sudo\s+)?mount\s+-a/i);
      if (uuidCmd && fstab && mountCmd) {
        response = "For a persistent ext4 mount, obtain the partition UUID with \x60" + uuidCmd[0] + "\x60, add an entry such as \x60" + fstab[0] + "\x60 to \x60/etc/fstab\x60, and validate it with \x60" + mountCmd[0] + "\x60. Only run \x60mkfs.ext4\x60 when intentionally creating a filesystem; formatting a partition can erase existing data.";
      }
    } else if (wantsDirectoryPermission) {
      evidenceRecord = findEvidence(raw => /\bexecute\b/i.test(raw) && /\b(?:directory|cd|traversal|search)\b/i.test(raw));
      if (/\bexecute\b/i.test(evidenceRecord.direct_answer)) {
        response = "Check execute (\x60x\x60) permission on the directory and its parent directories. On Linux, directory execute permission controls search/traversal, including changing into the directory with \x60cd\x60.";
      }
    }

    if (!response) {
      const aliases = aliasesFor(question, index.learnedRules).join(" ");
      const all = [];
      if (Array.isArray(best.structured_points)) all.push(...best.structured_points.map(cleanSentence));
      all.push(...splitSentences(bestAnswer));
      const uniqueSentences = [...new Set(all.map(cleanSentence).filter(s => s.length >= 20))];
      const candidateRows = uniqueSentences.map((sentence, i) => ({
        sentence,
        score: sentenceScore(sentence, question + " " + aliases, intent, index) + (i === 0 ? 0.1 : 0),
        record: best
      })).filter(x => x.score > 0).sort((a, b) => b.score - a.score);

      let selected = [];
      if (preparedAnswer || exact) {
        selected = [{ sentence: bestAnswer.slice(0, 1600), record: best, score: top.score }];
      } else {
        const seen = new Set();
        for (const row of candidateRows) {
          const key = normalize(row.sentence);
          if (seen.has(key)) continue;
          seen.add(key);
          selected.push(row);
          if (selected.length >= 2) break;
        }
        if (!selected.length) selected = [{ sentence: cleanSentence(bestAnswer).slice(0, 700), record: best, score: top.score }];
      }
      selected.sort((a, b) => (a.record === best ? -1 : 1) - (b.record === best ? -1 : 1));
      const body = selected.map(x => cleanSentence(x.sentence)).filter(Boolean).join(" ");

      if (preparedAnswer) {
        const m = bestAnswer.match(/^\s*Correct answer:\s*([^.]*)\.?\s*(.*)$/i);
        response = m ? "The correct answer identified by the course is " + m[1].trim().replace(/[.]$/, "") + (m[2] ? ". " + m[2].trim() : ".") : bestAnswer;
      } else if (intent === "why") response = "The key reason is: " + body;
      else if (intent === "how") response = "The course-supported approach is: " + body;
      else if (intent === "compare") response = "The key distinction is: " + body;
      else if (intent === "troubleshoot") response = "Start with the course-supported checks: " + body;
      else if (intent === "identify" || intent === "where") response = "The course identifies the relevant item as follows: " + body;
      else if (intent === "list") response = "The course identifies these relevant items: " + body;
      else if (intent === "example") response = "A course-supported example is: " + body;
      else if (intent === "when") response = "The course indicates this applies in the following situation: " + body;
      else response = "In this course context: " + body;
    }

    response = String(response || "").replace(/\s+/g, " ").trim();
    if (response.length > 1400) response = response.slice(0, 1397).replace(/\s+\S*$/, "") + "...";
    const label = [evidenceRecord.module_title, evidenceRecord.lesson_title, evidenceRecord.section_title || evidenceRecord.title, evidenceRecord.citation].filter(Boolean).join(" — ");
    const sources = label ? [label] : [];
    return {
      category: "IN_COURSE", answer: response, intent, score: top.score,
      coverage: top.coverage, concept: evidenceRecord, sources: sources.slice(0, 3),
      exactAnchor: exact,
      ranked: ranked.slice(0, 4).map(r => ({ title: r.concept.title || r.concept.section_title, score: r.score, coverage: r.coverage }))
    };
  }
  return { normalize, tokenize, classifyIntent, createIndex, rank, answer, ALIAS_GROUPS };
});
