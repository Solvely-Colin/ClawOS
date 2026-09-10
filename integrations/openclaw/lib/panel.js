function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function duration(seconds) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function meter(label, value, suffix = "%", fill = value) {
  const normalized = Math.max(0, Math.min(100, Number(fill) || 0));
  return `<div class="meter-row">
    <div class="meter-copy"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}${suffix}</strong></div>
    <div class="meter"><span style="width:${normalized}%"></span></div>
  </div>`;
}

export function renderSystemPanel(status, options = {}) {
  const hostLabel = status.isClawOS ? status.operatingSystem : "Development host";
  const hostSubtitle = status.isClawOS
    ? "ClawOS is connected to the local OpenClaw Gateway."
    : `ClawOS integration is running on ${status.operatingSystem}; this is not the release OS.`;
  const battery = status.batteryPercent === null
    ? `<div class="fact"><span>Battery</span><strong>Not reported</strong></div>`
    : meter("Battery", status.batteryPercent);
  const brokerState = status.broker.available
    ? `<strong class="state">Guarded broker ready</strong><p>${escapeHtml(status.broker.message)}. Machine changes require an exact native approval and recovery point.</p>`
    : `<strong class="state">Privileged actions blocked</strong><p>${escapeHtml(status.broker.message)}.</p>`;
  const updateTarget = status.broker.openclawUpdate?.targetVersion;
  const updateNotice = options.notice
    ? `<div class="notice ${options.notice.error ? "error" : "ok"}">${escapeHtml(options.notice.message)}</div>`
    : "";
  const fullRoot = status.broker.securityLevel === "full-root";
  const updateAvailable = updateTarget && updateTarget !== status.openclawVersion;
  const updateControl = status.broker.available && updateAvailable
    ? `<form method="post"><button type="submit">${fullRoot ? "Install" : "Review"} update to ${escapeHtml(updateTarget)}</button></form>`
    : `<span class="chip">${status.openclawVersion ? `OpenClaw ${escapeHtml(status.openclawVersion)} · up to date` : "No promoted update"}</span>`;

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="refresh" content="15">
  <title>ClawOS System</title>
  <style>
    :root{color-scheme:dark;--canvas:#111311;--pane:#171917;--pane2:#1d201d;--line:#30332f;--text:#f3f1ee;--muted:#a5a19f;--coral:#ff684f;--green:#35ce78;--amber:#e6b95c}
    *{box-sizing:border-box}html,body{margin:0;min-height:100%;background:var(--canvas);color:var(--text);font:14px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    body{padding:24px}main{max-width:1120px;margin:0 auto}.eyebrow,.chip,.fact span,.meter-copy span,.timestamp{font:600 11px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.08em;text-transform:uppercase}
    header{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:22px}.eyebrow{color:var(--coral);margin-bottom:7px}h1{font-size:25px;line-height:1.15;margin:0 0 7px}.subtitle{color:var(--muted);margin:0}.chips{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}.chip{border:1px solid var(--line);background:var(--pane);padding:8px 10px;border-radius:7px;color:var(--muted)}.chip.live{color:var(--green);border-color:#286d45}
    .grid{display:grid;grid-template-columns:repeat(12,1fr);gap:12px}.card{grid-column:span 6;background:var(--pane);border:1px solid var(--line);border-radius:9px;padding:17px}.card.wide{grid-column:span 12}.card h2{font-size:13px;margin:0 0 15px}.facts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:7px;overflow:hidden}.fact{min-width:0;background:var(--pane2);padding:12px}.fact span{display:block;color:var(--muted);margin-bottom:6px}.fact strong{display:block;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .meter-row+.meter-row{margin-top:15px}.meter-copy{display:flex;justify-content:space-between;margin-bottom:7px}.meter-copy span{color:var(--muted)}.meter-copy strong{font:600 12px ui-monospace,SFMono-Regular,Consolas,monospace}.meter{height:5px;border-radius:9px;background:#292c29;overflow:hidden}.meter span{display:block;height:100%;background:var(--green)}
    .recovery{display:flex;align-items:center;justify-content:space-between;gap:20px}.recovery strong{font-size:14px}.recovery p{color:var(--muted);margin:4px 0 0}.key{font:600 12px ui-monospace,SFMono-Regular,Consolas,monospace;border:1px solid #50534e;background:#222522;border-radius:6px;padding:8px 10px;white-space:nowrap}.broker{border-left:3px solid var(--amber)}.broker .state{color:var(--amber)}button{appearance:none;border:0;border-radius:7px;background:var(--coral);color:#111311;font:700 12px/1 ui-monospace,SFMono-Regular,Consolas,monospace;padding:11px 14px;cursor:pointer;white-space:nowrap}button:focus-visible{outline:3px solid #fff;outline-offset:3px}.notice{border:1px solid var(--line);border-radius:7px;margin:0 0 12px;padding:11px 13px}.notice.ok{border-color:#286d45;color:var(--green)}.notice.error{border-color:#7b3d34;color:#ff8a75}.timestamp{color:#747773;margin-top:16px;text-align:right}
    @media(max-width:760px){body{padding:16px}header{display:block}.chips{justify-content:flex-start;margin-top:14px}.card{grid-column:span 12}.facts{grid-template-columns:1fr}.recovery{align-items:flex-start;flex-direction:column}}
  </style>
</head>
<body>
  <main>
    <header>
      <div><div class="eyebrow">Machine surface / API v${escapeHtml(status.apiVersion)}</div><h1>${escapeHtml(status.hostname)}</h1><p class="subtitle">${escapeHtml(hostSubtitle)}</p></div>
      <div class="chips"><span class="chip live">● Gateway online</span><span class="chip">${escapeHtml(status.role)}</span><span class="chip">${escapeHtml(status.isClawOS ? "ClawOS" : "Dev host")}</span><span class="chip">Full user + approvals</span></div>
    </header>
    ${updateNotice}
    <div class="grid">
      <section class="card">
        <h2>Machine</h2>
        <div class="facts">
          <div class="fact"><span>System</span><strong title="${escapeHtml(status.operatingSystem)}">${escapeHtml(hostLabel)}</strong></div>
          <div class="fact"><span>Kernel</span><strong title="${escapeHtml(status.kernel)}">${escapeHtml(status.kernel)}</strong></div>
          <div class="fact"><span>Architecture</span><strong>${escapeHtml(status.architecture)}</strong></div>
          <div class="fact"><span>Uptime</span><strong>${escapeHtml(duration(status.uptimeSeconds))}</strong></div>
        </div>
      </section>
      <section class="card">
        <h2>Resources</h2>
        ${meter("Memory", status.memory.percent)}
        ${meter("Load (1m)", status.load[0], "", Math.min(100, status.load[0] * 25))}
        ${battery}
      </section>
      <section class="card wide broker">
        <div class="recovery"><div>${brokerState}</div><span class="chip">M3 · typed approvals</span></div>
      </section>
      <section class="card wide">
        <div class="recovery"><div><strong>OpenClaw updates are owned by ClawOS</strong><p>The upstream package remains root-owned. Updates use an exact reviewed version, ${fullRoot ? "automatic Full Root authorization" : "local approval"}, a recovery snapshot, and verification.</p></div>${updateControl}</div>
      </section>
      <section class="card wide">
        <div class="recovery"><div><strong>Native recovery stays outside OpenClaw</strong><p>If the Gateway or Control UI fails, switch to the standard Linux recovery console.</p></div><span class="key">${escapeHtml(status.recovery.shortcut)}</span></div>
      </section>
    </div>
    <div class="timestamp">Refreshed ${escapeHtml(status.observedAt)}</div>
  </main>
</body>
</html>`;
}
