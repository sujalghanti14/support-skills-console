"use strict";

// ---------- helpers (all output goes through textContent; never innerHTML) ----------
function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}
const ICONS = { ok: "✓", bad: "✕", warn: "!" };
function banner(kind, text) {
  const b = el("div", `banner ${kind}`);
  b.appendChild(el("span", "ico", ICONS[kind]));
  b.appendChild(el("span", "", text));
  return b;
}
// "BANNED PHRASE: 'x'" -> [BANNED PHRASE] 'x'  (label shown as a small badge)
function list(items, cls) {
  const ul = el("ul", "list");
  items.forEach(t => {
    const li = el("li", cls);
    const m = /^([A-Z][A-Z ]{3,}):\s*(.*)$/s.exec(t);
    if (m) { li.appendChild(el("span", "chip", m[1])); li.appendChild(document.createTextNode(m[2])); }
    else li.textContent = t;
    ul.appendChild(li);
  });
  return ul;
}
function show(target, ...nodes) { target.replaceChildren(...nodes); }

async function post(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  let data;
  try { data = await res.json(); } catch { data = {}; }
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

// Disable the button while a request runs; report network/API errors in the result area.
async function run(button, target, fn) {
  button.disabled = true;
  try { await fn(); }
  catch (e) { show(target, banner("bad", `Error: ${e.message}`)); }
  finally { button.disabled = false; }
}

// ---------- tabs ----------
const tabs = [...document.querySelectorAll('[role="tab"]')];
function selectTab(name) {
  tabs.forEach(t => {
    const on = t.dataset.tab === name;
    t.setAttribute("aria-selected", String(on));
    t.tabIndex = on ? 0 : -1;
    document.getElementById(`panel-${t.dataset.tab}`).hidden = !on;
  });
  try { localStorage.setItem("tab", name); } catch { /* storage unavailable */ }
}
tabs.forEach((t, i) => {
  t.addEventListener("click", () => selectTab(t.dataset.tab));
  t.addEventListener("keydown", e => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
    selectTab(next.dataset.tab); next.focus();
  });
});
let saved = null;
try { saved = localStorage.getItem("tab"); } catch { /* ignore */ }
selectTab(tabs.some(t => t.dataset.tab === saved) ? saved : "triage");

// ---------- examples ----------
const EXAMPLES = {
  triage: {
    ticket_id: "T-1093", category: "bug", team: "incident-oncall", priority: "urgent",
    escalation: "outage", confidence: 0.92,
    summary: "Entire 40-person workspace gets 502 errors opening boards.",
    reasoning: "'none of the 40 people' and '502' indicate a workspace-wide failure.",
  },
  reply:
`Dear Customer,

We apologize for any inconvenience. Per our policy, you can get a full refund within 30 days, and we can add a fifty dollar credit. Refunds arrive in 3-5 business days.

Rest assured we value your business.`,
  qa: [
    { ticket_id: "T-2201", team: "billing-ops", agent: "sam",
      scores: { resolution: 4, accuracy: 4, tone: 4, ownership: 4, efficiency: 3 }, tags: [], evidence: {} },
    { ticket_id: "T-2202", team: "billing-ops", agent: "lee",
      scores: { resolution: 3, accuracy: 1, tone: 3, ownership: 3, efficiency: 3 },
      tags: ["wrong_policy_figure"], evidence: { wrong_policy_figure: "full refund within 30 days" } },
    { ticket_id: "T-2203", team: "tier1-support", agent: "ana",
      scores: { resolution: 2, accuracy: 3, tone: 2, ownership: 2, efficiency: 3 },
      tags: ["banned_phrase", "no_next_step"],
      evidence: { banned_phrase: "we apologize for any inconvenience", no_next_step: "Thanks for reaching out." } },
    { ticket_id: "T-2205", team: "tier2-support", agent: "raj",
      scores: { resolution: 3, accuracy: 3, tone: 3, ownership: 2, efficiency: 3 },
      tags: ["no_next_step"], evidence: { no_next_step: "we'll look into it" } },
  ],
};

// ---------- triage ----------
const $ = id => document.getElementById(id);
$("triage-example").addEventListener("click", () => {
  $("triage-input").value = JSON.stringify(EXAMPLES.triage, null, 2);
});
$("triage-run").addEventListener("click", () => {
  const out = $("triage-result");
  run($("triage-run"), out, async () => {
    if (!$("triage-input").value.trim()) { show(out, banner("warn", "Paste a triage record first.")); return; }
    const r = await post("/api/triage/validate", { record: $("triage-input").value });
    if (r.valid) show(out, banner("ok", "Valid: the record matches the routing table."));
    else show(out, banner("bad", `Invalid: ${r.errors.length} problem(s)`), list(r.errors, "bad"));
  });
});

// ---------- reply ----------
$("reply-example").addEventListener("click", () => {
  $("reply-input").value = EXAMPLES.reply;
  $("reply-allow").value = "";
});
$("reply-run").addEventListener("click", () => {
  const out = $("reply-result");
  run($("reply-run"), out, async () => {
    if (!$("reply-input").value.trim()) { show(out, banner("warn", "Write or paste a draft first.")); return; }
    const r = await post("/api/reply/check", { draft: $("reply-input").value, allow: $("reply-allow").value });
    const nodes = [r.passed ? banner("ok", "PASS: safe to send against the current policy.")
                            : banner("bad", `FAIL: ${r.problems.length} problem(s) to fix`)];
    if (r.problems.length) nodes.push(list(r.problems, "bad"));
    if (r.warnings.length) nodes.push(list(r.warnings, "warn"));
    if (r.ok.length) { nodes.push(el("h3", "", "Verified figures")); nodes.push(list(r.ok, "ok")); }
    show(out, ...nodes);
  });
});
$("policy-toggle").addEventListener("click", async () => {
  const view = $("policy-view"), btn = $("policy-toggle");
  if (!view.hidden) { view.hidden = true; btn.textContent = "Show current policy"; btn.setAttribute("aria-expanded", "false"); return; }
  try {
    const res = await fetch("/api/policy");
    view.textContent = (await res.json()).text;
  } catch (e) { view.textContent = `Could not load policy: ${e.message}`; }
  view.hidden = false; btn.textContent = "Hide policy"; btn.setAttribute("aria-expanded", "true");
});

// ---------- QA ----------
$("qa-example").addEventListener("click", () => {
  $("qa-input").value = JSON.stringify(EXAMPLES.qa, null, 2);
});
$("qa-run").addEventListener("click", () => {
  const out = $("qa-result");
  run($("qa-run"), out, async () => {
    if (!$("qa-input").value.trim()) { show(out, banner("warn", "Paste grades first.")); return; }
    const r = await post("/api/qa/aggregate", { grades: $("qa-input").value });
    if (r.errors.length) { show(out, banner("bad", `Validation failed: ${r.errors.length} problem(s)`), list(r.errors, "bad")); return; }
    const stats = el("div", "stats");
    [["Tickets", r.n], ["Passed", `${r.passes}/${r.n}`], ["Patterns", r.patterns.length]].forEach(([k, v]) => {
      const s = el("div", "stat"); s.appendChild(el("b", "", String(v))); s.appendChild(el("span", "", k)); stats.appendChild(s);
    });
    const dl = el("button", "", "Download report (.md)");
    dl.id = "qa-download";
    dl.addEventListener("click", () => {
      const a = el("a");
      a.href = URL.createObjectURL(new Blob([r.report_md], { type: "text/markdown" }));
      a.download = "qa-report.md"; a.click(); URL.revokeObjectURL(a.href);
    });
    show(out, banner(r.patterns.length ? "warn" : "ok",
                     r.patterns.length ? `Recurring patterns: ${r.patterns.join(", ")}` : "No recurring patterns"),
         stats, dl, el("pre", "doc", r.report_md));
  });
});

// ---------- bugs ----------
$("bugs-form").addEventListener("submit", e => {
  e.preventDefault();
  const out = $("bugs-result");
  run($("bugs-run"), out, async () => {
    const q = $("bugs-input").value;
    if (!q.trim()) { show(out, banner("warn", "Describe the symptom first.")); return; }
    const r = await post("/api/bugs/search", { query: q, top: 5 });
    if (!r.terms.length) { show(out, banner("warn", "No searchable words in that query. Try product terms.")); return; }
    const nodes = [banner(r.weak ? "warn" : "ok",
      !r.results.length ? "No candidates: likely a NEW bug. Try another phrasing to confirm."
      : r.weak ? "Only weak candidates: probably NEW, but read them to confirm."
      : `${r.results.length} possible match(es). Make sure it's the same feature and device before telling the customer.`)];
    r.results.forEach(x => {
      const c = el("div", "card result-card");
      const meta = el("div", "meta");
      meta.appendChild(el("span", `pill ${x.status}`, x.status));
      const bar = el("span", "score"); const fill = el("i");
      fill.style.width = `${Math.round(x.score * 100)}%`; bar.appendChild(fill);
      meta.appendChild(bar);
      meta.appendChild(el("span", "", `${Math.round(x.score * 100)}% match`));
      meta.appendChild(el("span", "", x.version));
      if (x.ki) meta.appendChild(el("span", "", x.ki));
      c.appendChild(meta);
      c.appendChild(el("div", "body", x.text));
      c.appendChild(el("div", "meta", `matched: ${x.matched.join(", ")}`));
      nodes.push(c);
    });
    show(out, ...nodes);
  });
});
