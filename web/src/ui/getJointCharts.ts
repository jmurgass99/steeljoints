import type { SteelJointResult } from "../data-model.ts";

export function renderBoltForcesPolarChart(canvas: HTMLCanvasElement, res: SteelJointResult): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const w = (canvas.width = canvas.clientWidth || 360);
  const h = (canvas.height = canvas.clientHeight || 205);
  ctx.clearRect(0, 0, w, h);

  ctx.strokeStyle = "rgba(148,163,184,0.25)";
  ctx.strokeRect(36, 16, w - 52, h - 38);

  const n = res.bolts.length;
  const maxV = Math.max(res.maxVKn, 1);
  const bw = (w - 60) / Math.max(n, 1);

  res.bolts.forEach((b, idx) => {
    const bh = (b.vTotalKn / maxV) * (h - 52);
    const x = 40 + idx * bw;
    ctx.fillStyle = "#38bdf8";
    ctx.fillRect(x, h - 22 - bh, bw - 6, bh);
    ctx.fillStyle = "#e2e8f0";
    ctx.font = "9px Inter, sans-serif";
    ctx.fillText(`P${idx + 1}`, x + 2, h - 8);
  });

  ctx.fillStyle = "#e2e8f0";
  ctx.font = "11px Inter, sans-serif";
  ctx.fillText(`Cortante por perno V_i — máx = ${res.maxVKn.toFixed(1)} kN`, 42, 30);
}

export function renderTensionPryingChart(canvas: HTMLCanvasElement, res: SteelJointResult): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const w = (canvas.width = canvas.clientWidth || 360);
  const h = (canvas.height = canvas.clientHeight || 205);
  ctx.clearRect(0, 0, w, h);

  ctx.strokeStyle = "rgba(148,163,184,0.25)";
  ctx.strokeRect(36, 16, w - 52, h - 38);

  const tDirect = res.maxTKn;
  const qPrying = res.pryingForceKn;
  const tTotal = tDirect + qPrying;
  const maxVal = Math.max(tTotal, 1);

  const hT = (tDirect / maxVal) * (h - 52);
  const hQ = (qPrying / maxVal) * (h - 52);

  ctx.fillStyle = "#eab308";
  ctx.fillRect(75, h - 22 - hT, 65, hT);
  ctx.fillStyle = "#ef4444";
  ctx.fillRect(175, h - 22 - hQ, 65, hQ);

  ctx.fillStyle = "#e2e8f0";
  ctx.font = "11px Inter, sans-serif";
  ctx.fillText(`Tracción T = ${tDirect.toFixed(1)} kN`, 65, h - 8);
  ctx.fillText(`Palanca Q = ${qPrying.toFixed(1)} kN`, 165, h - 8);
  ctx.fillText(`Momento chapa: ${res.plateMomentKnm.toFixed(2)} kN·m`, 42, 30);
}
