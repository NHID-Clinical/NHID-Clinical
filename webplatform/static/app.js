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
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function spin(node) { node.innerHTML = '<span class="spinner"></span> working…'; }
