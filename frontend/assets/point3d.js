// Aba "Água no ponto · 3D": terreno de 1,2 km × 1,2 km em volta do ponto escolhido, com o mapa do
// OpenStreetMap sobre o relevo e a água no nível do cenário (modelo de enchimento a partir do lago).
const p3 = {
  canvas: document.getElementById("point-canvas"), data: null, texture: null, request: 0, frame: 0,
  picker: null, marker: null, box: null,
};
p3.ctx = p3.canvas.getContext("2d");

function lonLatToTile(lon, lat, zoom) {
  const n = 2 ** zoom;
  return [(lon + 180) / 360 * n, (1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * n];
}

function loadTexture(bbox) {
  // Monta o recorte do mapa (zoom 16) que cobre exatamente a janela do terreno.
  const [west, south, east, north] = bbox, zoom = 16;
  const [fx0, fy0] = lonLatToTile(west, north, zoom), [fx1, fy1] = lonLatToTile(east, south, zoom);
  const tx0 = Math.floor(fx0), ty0 = Math.floor(fy0), tx1 = Math.floor(fx1), ty1 = Math.floor(fy1);
  const mosaic = document.createElement("canvas");
  mosaic.width = (tx1 - tx0 + 1) * 256; mosaic.height = (ty1 - ty0 + 1) * 256;
  const mctx = mosaic.getContext("2d");
  const jobs = [];
  for (let x = tx0; x <= tx1; x++) for (let y = ty0; y <= ty1; y++) {
    jobs.push(new Promise((resolve) => {
      const image = new Image();
      image.onload = () => { mctx.drawImage(image, (x - tx0) * 256, (y - ty0) * 256); resolve(true); };
      image.onerror = () => resolve(false);
      image.src = `https://tile.openstreetmap.org/${zoom}/${x}/${y}.png`;
    }));
  }
  return Promise.all(jobs).then((results) => {
    if (!results.some(Boolean)) return null;
    const texture = document.createElement("canvas");
    texture.width = texture.height = 600;
    texture.getContext("2d").drawImage(mosaic, (fx0 - tx0) * 256, (fy0 - ty0) * 256, (fx1 - fx0) * 256, (fy1 - fy0) * 256, 0, 0, 600, 600);
    return texture;
  });
}

function texturedTriangle(ctx, image, p0, p1, p2, t0, t1, t2) {
  // Mapeamento afim do triângulo de textura (t) para o triângulo na tela (p).
  const du1 = t1[0] - t0[0], dv1 = t1[1] - t0[1], du2 = t2[0] - t0[0], dv2 = t2[1] - t0[1];
  const det = du1 * dv2 - du2 * dv1;
  if (!det) return;
  const dx1 = p1[0] - p0[0], dy1 = p1[1] - p0[1], dx2 = p2[0] - p0[0], dy2 = p2[1] - p0[1];
  const a = (dx1 * dv2 - dx2 * dv1) / det, b = (dy1 * dv2 - dy2 * dv1) / det;
  const c = (dx2 * du1 - dx1 * du2) / det, d = (dy2 * du1 - dy1 * du2) / det;
  ctx.save();
  ctx.beginPath(); ctx.moveTo(...p0); ctx.lineTo(...p1); ctx.lineTo(...p2); ctx.closePath(); ctx.clip();
  ctx.transform(a, b, c, d, p0[0] - a * t0[0] - c * t0[1], p0[1] - b * t0[0] - d * t0[1]);
  ctx.drawImage(image, 0, 0);
  ctx.restore();
}

function pointStats() {
  const { data } = p3, water = Scenario.levelMsl();
  if (!data) return;
  const n = data.ground_msl_m.length;
  let flooded = 0;
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) if (water != null && data.spill_msl_m[r][c] != null && data.spill_msl_m[r][c] < water) flooded++;
  const { row, col } = data.point;
  const s = data.spill_msl_m[row][col];
  const depthHere = water != null && s != null && s < water ? water - data.ground_msl_m[row][col] : 0;
  updatePointMetrics(depthHere, flooded / (n * n));
}

function drawPoint() {
  pointStats();
  cancelAnimationFrame(p3.frame);
  p3.frame = requestAnimationFrame(renderPoint);
}

function renderPoint() {
  const { canvas, ctx, data } = p3;
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(rect.width * ratio); canvas.height = Math.round(rect.height * ratio);
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  const width = rect.width, height = rect.height;
  const sky = ctx.createLinearGradient(0, 0, 0, height);
  sky.addColorStop(0, "#dceef2"); sky.addColorStop(1, "#f7f6ef");
  ctx.fillStyle = sky; ctx.fillRect(0, 0, width, height);
  if (!data) return;
  const ground = data.ground_msl_m, spill = data.spill_msl_m, n = ground.length;
  const water = Scenario.levelMsl();
  const angle = Number(document.getElementById("point-angle").value) * Math.PI / 180;
  const exaggeration = Number(document.getElementById("point-exaggeration").value);
  const cs = Math.cos(angle), sn = Math.sin(angle);
  const scale = Math.min(width * .36, height * .62);
  const flat = ground.flat();
  const zMin = Math.min(...flat, water ?? Infinity);
  const zPerMeter = scale / (n * data.cell_m / 2) * exaggeration;
  const project = (r, c, z) => {
    const x = c / (n - 1) * 2 - 1, y = r / (n - 1) * 2 - 1;
    return [width / 2 + (x * cs - y * sn) * scale, height * .62 + (x * sn + y * cs) * scale * .52 - (z - zMin) * zPerMeter];
  };
  const wet = (r, c) => water != null && spill[r][c] != null && spill[r][c] < water;
  const step = 2, cells = [];
  for (let r = 0; r + step < n; r += step) for (let c = 0; c + step < n; c += step) {
    const x = (c + step / 2) / (n - 1) * 2 - 1, y = (r + step / 2) / (n - 1) * 2 - 1;
    cells.push({ r, c, order: x * sn + y * cs });
  }
  cells.sort((a, b) => a.order - b.order);
  const texSize = 600 / (n - 1);
  let flooded = 0;
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) if (wet(r, c)) flooded++;
  if (!rect.width) return;
  for (const { r, c } of cells) {
    const corners = [[r, c], [r, c + step], [r + step, c + step], [r + step, c]];
    const screen = corners.map(([rr, cc]) => project(rr, cc, ground[rr][cc]));
    if (p3.texture) {
      const tex = corners.map(([rr, cc]) => [cc * texSize, rr * texSize]);
      texturedTriangle(ctx, p3.texture, screen[0], screen[1], screen[2], tex[0], tex[1], tex[2]);
      texturedTriangle(ctx, p3.texture, screen[0], screen[2], screen[3], tex[0], tex[2], tex[3]);
    } else {
      const mean = corners.reduce((sum, [rr, cc]) => sum + ground[rr][cc], 0) / 4;
      ctx.beginPath(); screen.forEach((p, i) => i ? ctx.lineTo(...p) : ctx.moveTo(...p)); ctx.closePath();
      ctx.fillStyle = `hsl(${120 - Math.min(80, mean * 2)}, 25%, ${55 + Math.min(20, mean / 2)}%)`; ctx.fill();
    }
    // Sombreamento leve pela inclinação, para o relevo aparecer sob o mapa.
    const slope = (ground[r][c + step] + ground[r + step][c + step] - ground[r][c] - ground[r + step][c]) * cs
      - (ground[r + step][c] + ground[r + step][c + step] - ground[r][c] - ground[r][c + step]) * sn;
    if (Math.abs(slope) > .2) {
      ctx.beginPath(); screen.forEach((p, i) => i ? ctx.lineTo(...p) : ctx.moveTo(...p)); ctx.closePath();
      ctx.fillStyle = slope > 0 ? `rgba(0,0,0,${Math.min(.28, slope / 30)})` : `rgba(255,255,255,${Math.min(.2, -slope / 30)})`;
      ctx.fill();
    }
    const centerR = r + step / 2, centerC = c + step / 2;
    if (wet(centerR, centerC)) {
      const depth = water - ground[centerR][centerC];
      const top = corners.map(([rr, cc]) => project(rr, cc, Math.max(water, Math.min(ground[rr][cc], water))));
      ctx.beginPath(); top.forEach((p, i) => i ? ctx.lineTo(...p) : ctx.moveTo(...p)); ctx.closePath();
      ctx.fillStyle = `rgba(28,112,178,${Math.min(.7, .34 + depth / 10)})`; ctx.fill();
    }
  }
  // Marcador do ponto escolhido.
  const pr = data.point.row, pc = data.point.col, pg = ground[pr][pc];
  const base = project(pr, pc, wet(pr, pc) ? water : pg), tip = [base[0], base[1] - 46];
  ctx.strokeStyle = "#7a3b1e"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(...base); ctx.lineTo(...tip); ctx.stroke();
  ctx.fillStyle = "#c0703f"; ctx.beginPath(); ctx.arc(tip[0], tip[1], 7, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = "#fff"; ctx.stroke();
  const depthHere = wet(pr, pc) ? water - pg : 0;
  const label = water == null ? "sem nível" : depthHere > 0 ? `${fmt(depthHere, 1)} m de água` : "seco";
  ctx.font = "600 12px Inter, sans-serif"; ctx.fillStyle = "#3b2416";
  ctx.fillText(label, tip[0] + 11, tip[1] + 4);
  document.getElementById("point-status").textContent = water == null ? "Escolha um nível para ver a água"
    : `Cenário ${fmt(Scenario.state.level)} m · ${fmt(100 * flooded / (n * n), 0)}% do recorte com água`;
}

function updatePointMetrics(depthHere, fraction) {
  const { data } = p3, state = Scenario.state, water = Scenario.levelMsl();
  if (!data) return;
  const g = data.point.ground_msl_m, s = data.point.spill_msl_m;
  const arrives = s == null ? null : s + REGUA_OFFSET;
  const arrivalText = arrives == null ? "A água do lago não chega a este ponto no modelo." : arrives > 12
    ? "A água do lago só chegaria aqui acima de 12 m na régua."
    : `A água do lago chega a este ponto com o Guaíba a <strong>${fmt(Math.max(arrives, 0))} m</strong> na régua.`;
  const now = water == null ? "Sem nível escolhido." : depthHere > 0
    ? `No cenário de ${fmt(state.level)} m: <strong>${fmt(depthHere, 1)} m de água</strong> no ponto.`
    : `No cenário de ${fmt(state.level)} m: <strong>ponto seco</strong>.`;
  document.getElementById("point-metrics").innerHTML = `<strong class="point-name">${state.point.label}</strong><span>${now}</span><span>${arrivalText}</span><span>Chão estimado: ${fmt(g, 1)} m acima do nível médio do mar · ${fmt(100 * fraction, 0)}% do recorte com água.</span>`;
  document.getElementById("kpi-point").textContent = water == null ? "—" : depthHere > 0 ? `${fmt(depthHere, 1)} m` : "Seco";
  document.getElementById("kpi-point-label").textContent = state.point.label;
}

async function loadPoint() {
  const serial = ++p3.request, { lat, lon } = Scenario.state.point;
  document.getElementById("point-status").textContent = "Carregando terreno...";
  try {
    const response = await fetch(`/api/water/point?lat=${lat}&lon=${lon}`);
    if (!response.ok) throw new Error(response.status === 422 ? "Ponto fora da área do modelo (Porto Alegre)." : "Terreno indisponível.");
    const data = await response.json();
    if (serial !== p3.request) return;
    p3.data = data;
    p3.texture = null;
    const [w, s, e, n] = data.bbox;
    p3.box?.setBounds([[s, w], [n, e]]);
    drawPoint();
    const texture = await loadTexture(data.bbox);
    if (serial !== p3.request) return;
    p3.texture = texture;
    drawPoint();
    const v = data.validation.validation.find((row) => row.date === "2024-05-04");
    const v10 = data.validation.validation.find((row) => row.date === "2024-05-10");
    if (v && v10) document.getElementById("point-validation").textContent = `Validação contra a mancha observada pelo Copernicus: concordância (IoU) de ${fmt(v.iou * 100, 0)}% em 04/05 e ${fmt(v10.iou * 100, 0)}% em 10/05/2024; o modelo é mais preciso na subida do rio e subestima a água que ficou represada atrás dos diques.`;
  } catch (error) {
    if (serial === p3.request) { p3.data = null; drawPoint(); document.getElementById("point-status").textContent = error.message; }
  }
}

function startPointPicker() {
  p3.picker = L.map("point-picker", { scrollWheelZoom: false, zoomControl: true }).setView([Scenario.state.point.lat, Scenario.state.point.lon], 12);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap", maxZoom: 18 }).addTo(p3.picker);
  p3.marker = L.circleMarker([Scenario.state.point.lat, Scenario.state.point.lon], { radius: 6, color: "#fff", weight: 2, fillColor: "#c0703f", fillOpacity: 1 }).addTo(p3.picker);
  p3.box = L.rectangle([[0, 0], [0, 0]], { color: "#c0703f", weight: 1.5, fill: false, dashArray: "4 3" }).addTo(p3.picker);
  p3.picker.on("click", (event) => Scenario.setPoint(event.latlng.lat, event.latlng.lng, `Ponto ${event.latlng.lat.toFixed(4)}, ${event.latlng.lng.toFixed(4)}`));
}

for (const id of ["point-angle", "point-exaggeration"]) document.getElementById(id).addEventListener("input", drawPoint);
new ResizeObserver(drawPoint).observe(p3.canvas);
(() => {
  let dragging = null;
  p3.canvas.addEventListener("pointerdown", (event) => { dragging = { x: event.clientX, angle: Number(document.getElementById("point-angle").value) }; p3.canvas.setPointerCapture(event.pointerId); });
  p3.canvas.addEventListener("pointermove", (event) => {
    if (!dragging) return;
    const slider = document.getElementById("point-angle");
    slider.value = ((dragging.angle + (event.clientX - dragging.x) * .6) % 360 + 360) % 360;
    drawPoint();
  });
  p3.canvas.addEventListener("pointerup", () => { dragging = null; });
})();
window.addEventListener("maptab", (event) => {
  if (event.detail === "point") setTimeout(() => { p3.picker.invalidateSize(); p3.picker.setView([Scenario.state.point.lat, Scenario.state.point.lon], 14); drawPoint(); }, 0);
});

startPointPicker();
Scenario.subscribe((state, kind) => {
  if (kind === "init" || kind === "point") {
    p3.marker.setLatLng([state.point.lat, state.point.lon]);
    if (!document.getElementById("pane-point").hidden) p3.picker.panTo([state.point.lat, state.point.lon]);
    loadPoint();
  }
  if (kind === "level") drawPoint();
});
