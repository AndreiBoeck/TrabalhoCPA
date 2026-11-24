// Aba "Água no ponto · 3D": mapa 3D (MapLibre GL) com prédios do OpenStreetMap em altura real e a água do
// modelo do projeto, em blocos com a profundidade de cada célula de 20 m, no nível do cenário.
const p3 = { map: null, data: null, request: 0, ready: false, marker: null, bearing: -20 };
const WATER_HALF_CELLS = 50; // 100 × 100 células de 20 m = 2 km × 2 km
const DEPTH_COLORS = ["#9fd3ea", "#5aaed8", "#2b7fbd", "#17508f"];

function depthColor(depth) {
  return depth < 0.5 ? DEPTH_COLORS[0] : depth < 1 ? DEPTH_COLORS[1] : depth < 2 ? DEPTH_COLORS[2] : DEPTH_COLORS[3];
}

function waterFeatures() {
  // Junta, em cada linha da grade, células vizinhas alagadas da mesma faixa de profundidade (menos polígonos).
  const { data } = p3, water = Scenario.levelMsl();
  const features = [];
  if (!data || water == null) return { type: "FeatureCollection", features };
  const ground = data.ground_msl_m, spill = data.spill_msl_m, n = ground.length;
  const [west, south, east, north] = data.bbox;
  const lon = (c) => west + (east - west) * c / n, lat = (r) => north - (north - south) * r / n;
  for (let r = 0; r < n; r++) {
    let start = null, bucket = null, sum = 0, count = 0;
    const flush = (endC) => {
      if (start === null) return;
      const depth = sum / count;
      features.push({ type: "Feature", properties: { h: Math.max(0.15, depth), color: depthColor(depth) },
        geometry: { type: "Polygon", coordinates: [[[lon(start), lat(r)], [lon(endC), lat(r)], [lon(endC), lat(r + 1)], [lon(start), lat(r + 1)], [lon(start), lat(r)]]] } });
      start = null; sum = 0; count = 0;
    };
    for (let c = 0; c < n; c++) {
      const s = spill[r][c];
      const depth = s != null && s < water ? water - Math.max(ground[r][c], 0) : 0;
      const b = depth > 0 ? Math.min(3, Math.floor(depth * 2) / 2) : null;
      if (b !== bucket) { flush(c); bucket = b; if (b !== null) start = c; }
      if (b !== null) { sum += depth; count++; }
    }
    flush(n);
  }
  return { type: "FeatureCollection", features };
}

function pointDepth() {
  const { data } = p3, water = Scenario.levelMsl();
  if (!data || water == null) return 0;
  const { row, col } = data.point, s = data.spill_msl_m[row][col];
  return s != null && s < water ? water - data.ground_msl_m[row][col] : 0;
}

function setRecorte() {
  if (!p3.ready || !p3.data) return;
  const [w, s, e, n] = p3.data.bbox;
  p3.map.getSource("recorte").setData({ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] } });
}

function updateWater() {
  if (p3.ready) p3.map.getSource("agua").setData(waterFeatures());
  const n = p3.data ? p3.data.ground_msl_m.length : 1;
  const water = Scenario.levelMsl();
  let cells = 0;
  if (p3.data && water != null) for (const row of p3.data.spill_msl_m) for (const s of row) if (s != null && s < water) cells++;
  updatePointMetrics(pointDepth(), cells / (n * n));
  if (p3.data) document.getElementById("point-status").textContent = Scenario.state.level == null ? "Escolha um nível para ver a água"
    : `Cenário ${fmt(Scenario.state.level)} m · ${fmt(100 * cells / (n * n), 0)}% da área com água`;
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
  document.getElementById("point-metrics").innerHTML = `<strong class="point-name">${state.point.label}</strong><span>${now}</span><span>${arrivalText}</span><span>Chão estimado: ${fmt(g, 1)} m acima do nível médio do mar · ${fmt(100 * fraction, 0)}% da área com água.</span>`;
  document.getElementById("kpi-point").textContent = water == null ? "—" : depthHere > 0 ? `${fmt(depthHere, 1)} m` : "Seco";
  document.getElementById("kpi-point-label").textContent = state.point.label;
}

async function loadPoint() {
  const serial = ++p3.request, { lat, lon } = Scenario.state.point;
  document.getElementById("point-status").textContent = "Calculando a água em volta do ponto...";
  try {
    const response = await fetch(`/api/water/point?lat=${lat}&lon=${lon}&half_cells=${WATER_HALF_CELLS}`);
    if (!response.ok) throw new Error(response.status === 422 ? "Ponto fora da área do modelo (Porto Alegre)." : "Terreno indisponível.");
    const data = await response.json();
    if (serial !== p3.request) return;
    p3.data = data;
    setRecorte();
    updateWater();
    const v = data.validation.validation.find((row) => row.date === "2024-05-04");
    const v10 = data.validation.validation.find((row) => row.date === "2024-05-10");
    if (v && v10) document.getElementById("point-validation").textContent = `Validação contra a mancha observada pelo Copernicus: concordância (IoU) de ${fmt(v.iou * 100, 0)}% em 04/05 e ${fmt(v10.iou * 100, 0)}% em 10/05/2024; o modelo é mais preciso na subida do rio e subestima a água que ficou represada atrás dos diques.`;
  } catch (error) {
    if (serial === p3.request) { p3.data = null; updateWater(); document.getElementById("point-status").textContent = error.message; }
  }
}

function startPointMap() {
  if (typeof maplibregl === "undefined") {
    document.getElementById("point-status").textContent = "Mapa 3D indisponível neste navegador.";
    return;
  }
  const { lat, lon } = Scenario.state.point;
  p3.map = new maplibregl.Map({
    container: "point-map", style: "https://tiles.openfreemap.org/styles/liberty",
    center: [lon, lat], zoom: 15.6, pitch: 60, bearing: p3.bearing, maxPitch: 80, attributionControl: { compact: true },
  });
  p3.map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
  p3.marker = new maplibregl.Marker({ color: "#c0703f" }).setLngLat([lon, lat]).addTo(p3.map);
  p3.map.once("style.load", () => {
    const before = p3.map.getLayer("building-3d") ? "building-3d" : undefined;
    p3.map.addSource("agua", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    p3.map.addLayer({ id: "agua-3d", type: "fill-extrusion", source: "agua",
      paint: { "fill-extrusion-color": ["get", "color"], "fill-extrusion-height": ["get", "h"], "fill-extrusion-base": 0, "fill-extrusion-opacity": .75 } }, before);
    p3.map.addSource("recorte", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    p3.map.addLayer({ id: "recorte-linha", type: "line", source: "recorte", paint: { "line-color": "#c0703f", "line-width": 1.5, "line-dasharray": [3, 2] } });
    if (p3.map.getLayer("building-3d")) p3.map.setLayerZoomRange("building-3d", 13, 24);
    p3.ready = true;
    setRecorte();
    updateWater();
  });
  p3.map.on("click", (event) => Scenario.setPoint(event.lngLat.lat, event.lngLat.lng, `Ponto ${event.lngLat.lat.toFixed(4)}, ${event.lngLat.lng.toFixed(4)}`));
  p3.map.on("error", (event) => {
    if (!p3.ready) document.getElementById("point-status").textContent = "Não foi possível carregar o mapa base (sem internet?). A água continua calculada ao lado.";
    console.warn(event.error?.message || event);
  });
  new ResizeObserver(() => p3.map.resize()).observe(document.getElementById("point-map"));
}

function setView(mode) {
  if (!p3.map) return;
  if (mode === "rotate") { p3.map.easeTo({ bearing: (p3.map.getBearing() + 90) % 360, duration: 900 }); return; }
  document.getElementById("view-3d").classList.toggle("active", mode === "3d");
  document.getElementById("view-top").classList.toggle("active", mode === "top");
  p3.map.easeTo({ pitch: mode === "3d" ? 60 : 0, duration: 800 });
}
document.getElementById("view-3d").addEventListener("click", () => setView("3d"));
document.getElementById("view-top").addEventListener("click", () => setView("top"));
document.getElementById("view-rotate").addEventListener("click", () => setView("rotate"));
window.addEventListener("maptab", (event) => {
  if (event.detail === "point" && p3.map) setTimeout(() => { p3.map.resize(); p3.map.jumpTo({ center: [Scenario.state.point.lon, Scenario.state.point.lat] }); }, 0);
});

startPointMap();
Scenario.subscribe((state, kind) => {
  if (kind === "init" || kind === "point") {
    p3.marker?.setLngLat([state.point.lon, state.point.lat]);
    if (p3.map && kind === "point" && !document.getElementById("pane-point").hidden) p3.map.easeTo({ center: [state.point.lon, state.point.lat], duration: 700 });
    loadPoint();
  }
  if (kind === "level") updateWater();
});
