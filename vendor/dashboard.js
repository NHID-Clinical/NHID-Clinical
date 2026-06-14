/* NHID-Clinical Vendor Compliance Dashboard — fetch/render logic */
const API_BASE = "https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod";

document.getElementById("loadBtn").addEventListener("click", loadMetrics);

async function loadMetrics() {
  const vendorId = document.getElementById("vendorId").value.trim();
  const apiKey = document.getElementById("apiKey").value.trim();
  const days = document.getElementById("days").value;
  const errorBox = document.getElementById("errorBox");
  errorBox.style.display = "none";

  if (!vendorId) { return showError("Enter a vendor_id."); }

  try {
    const resp = await fetch(
      `${API_BASE}/v1/vendor/metrics/summary?vendor_id=${encodeURIComponent(vendorId)}&days=${days}`,
      { headers: apiKey ? { "x-api-key": apiKey } : {} }
    );
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      return showError(body.error || `API returned ${resp.status}`);
    }
    const m = await resp.json();
    document.getElementById("callsTotal").textContent = m.calls_total;
    document.getElementById("passRate").textContent = (m.pass_rate * 100).toFixed(1) + "%";
    document.getElementById("casAvg").textContent = m.cas_avg.toFixed(4);
    document.getElementById("casRange").textContent = `${m.cas_min.toFixed(2)}–${m.cas_max.toFixed(2)}`;

    const badgeUrl = `${API_BASE}/v1/public/vendor/${encodeURIComponent(vendorId)}/badge`;
    document.getElementById("badgePreview").innerHTML =
      `<img src="${badgeUrl}" alt="NHID-CAS badge for ${vendorId}" />`;
    document.getElementById("badgeSnippet").textContent =
      `<a href="https://nhid-clinical.org" title="NHID-Clinical CAS badge">\n` +
      `  <img src="${badgeUrl}" alt="NHID-CAS compliance badge for ${vendorId}" />\n` +
      `</a>`;
  } catch (err) {
    showError("Network error: " + err.message);
  }
}

function showError(msg) {
  const errorBox = document.getElementById("errorBox");
  errorBox.textContent = msg;
  errorBox.style.display = "block";
}
