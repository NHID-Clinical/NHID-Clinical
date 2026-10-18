// Shared helpers for the NHID-Clinical workspace pages.

// Fetch JSON. A non-2xx response or a network failure comes back as
// { error } instead of throwing, so every page can show an error state
// rather than freezing on its loading skeleton.
async function api(path, method = "GET", body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body !== null) opts.body = JSON.stringify(body);
  try {
    const r = await fetch(path, opts);
    const data = await r.json().catch(() => ({}));
    if (!r.ok) return { error: data.detail || data.error || `Request failed (${r.status})` };
    return data;
  } catch (e) {
    return { error: "Could not reach the platform server." };
  }
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
function spin(node) { node.innerHTML = '<span class="spinner" aria-hidden="true"></span> Working…'; }
// Placeholder lines while a panel loads.
function skeleton(node, lines = 4) {
  node.innerHTML = `<div class="skel" aria-busy="true" aria-label="Loading">${"<i></i>".repeat(lines)}</div>`;
}
// Calm empty state with an optional next step.
function empty(node, title, text, actionHtml = "") {
  node.innerHTML = `<div class="empty"><b>${esc(title)}</b>${esc(text)}${actionHtml ? `<div class="act">${actionHtml}</div>` : ""}</div>`;
}
function failed(node, message) {
  node.innerHTML = `<div class="err" role="alert">${esc(message)}</div>`;
}
