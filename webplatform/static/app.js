// Tiny shared helpers for the NHID-Clinical platform pages.
async function api(path, method = "GET", body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body !== null) opts.body = JSON.stringify(body);
  const r = await fetch(path, opts);
  return r.json();
}
function el(id) { return document.getElementById(id); }
function pill(ok, txtOk, txtBad) {
  const cls = ok ? "ok" : "bad";
  return `<span class="pill ${cls}">${ok ? txtOk : txtBad}</span>`;
}
function tierPill(tier) {
  const t = (tier || "").toLowerCase();
  let cls = "warn";
  if (t.includes("verified")) cls = "ok";
  else if (t.includes("denied") || t.includes("hard")) cls = "bad";
  else if (t.includes("conditional")) cls = "ok";
  return `<span class="pill ${cls}">${tier || "—"}</span>`;
}
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function spin(node) { node.innerHTML = '<span class="spinner"></span> working…'; }
