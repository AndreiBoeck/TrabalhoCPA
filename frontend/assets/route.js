// Aba "Rotas a pé": ruas da área que alagou em 2024 coloridas pela água do modelo no nível do cenário,
// a água por baixo e a rota de saída até o ponto seco mais próximo (ou de A para B).
const $ = (id) => document.getElementById(id);
const map = L.map("route-map", { preferCanvas: true, scrollWheelZoom: false, zoomSnap: .25 }).setView([-30.0225, -51.2190], 15);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap contributors", maxZoom: 19 }).addTo(map);
new ResizeObserver(() => map.invalidateSize()).observe($("route-map"));

const BANDS = [
  { max: 0, style: { color: "#5f7f89", weight: 1.8, opacity: .6 } },
  { max: .3, style: { color: "#f2b04a", weight: 3.5, opacity: .95 } },
  { max: 1, style: { color: "#e0603e", weight: 4, opacity: .95 } },
  { max: Infinity, style: { color: "#9e1f2c", weight: 4.5, opacity: .95 } },
];
const R = {
  streets: null, depths: null, level: undefined, mode: "exit", areaBounds: null,
  overlay: null, observed: null, bandLayers: [], unknownLayer: null, area: null,
  route: [], markers: [], a: null, b: null, serial: 0, depthSerial: 0, routeBounds: null,
};
const routeLevel = () => Scenario.state.level == null ? null : Math.round(Math.min(12, Math.max(0, Scenario.state.level)) * 100) / 100;
const km = (m) => m >= 1000 ? `${fmt(m / 1000, 1)} km` : `${fmtInt(Math.round(m / 10) * 10)} m`;
const paneVisible = () => !$("pane-route").hidden && map.getSize().x > 0;
const setResult = (html, kind = "") => { $("route-result").innerHTML = html; $("route-result").className = `route-result ${kind}`; };
const inArea = (lat, lon) => R.areaBounds && R.areaBounds.contains([lat, lon]);

function frame() {
  if (!paneVisible()) return;
  map.invalidateSize();
  const { lat, lon } = Scenario.state.point;
  if (R.routeBounds) map.fitBounds(R.routeBounds, { padding: [40, 40], maxZoom: 17 });
  else if (R.mode === "exit" && inArea(lat, lon)) map.setView([lat, lon], 15.5);
  else if (R.areaBounds) map.fitBounds(R.areaBounds);
}
window.addEventListener("maptab", (event) => {
  if (event.detail === "route") requestAnimationFrame(() => requestAnimationFrame(frame));
});

function clearRoute() {
  R.serial++;
  [...R.route, ...R.markers].forEach((layer) => map.removeLayer(layer));
  R.route = []; R.markers = []; R.routeBounds = null;
  $("legend-normal").hidden = true;
}

function pin(lat, lon, color, label, letter = "") {
  const icon = L.divIcon({ className: "route-pin", html: `<span style="background:${color}">${letter}</span>`, iconSize: [26, 26], iconAnchor: [13, 13] });
  const marker = L.marker([lat, lon], { icon, keyboard: false }).bindTooltip(label, { direction: "top", offset: [0, -12] }).addTo(map);
  R.markers.push(marker);
  return marker;
}

function drawRoute(coords, dashed = false) {
  if (dashed) {
    R.route.push(L.polyline(coords, { color: "#4f6168", weight: 4, opacity: .8, dashArray: "7 7", interactive: false }).addTo(map));
    return;
  }
  R.route.push(L.polyline(coords, { color: "#fff", weight: 10, opacity: .95, interactive: false }).addTo(map));
  R.route.push(L.polyline(coords, { color: "#11845b", weight: 5.5, opacity: 1, interactive: false }).addTo(map));
}

function drawStreets() {
  R.bandLayers.forEach((layer) => map.removeLayer(layer));
  if (R.unknownLayer) map.removeLayer(R.unknownLayer);
  const groups = BANDS.map(() => []), unknown = [];
  R.streets.edges.forEach((edge, i) => {
    const d = R.depths?.edge_depth_m[i];
    if (d == null) { if (R.depths) unknown.push(edge.coords); else groups[0].push(edge.coords); return; }
    groups[BANDS.findIndex((band) => d <= band.max)].push(edge.coords);
  });
  R.bandLayers = groups.map((lines, i) => L.polyline(lines, { ...BANDS[i].style, interactive: false }).addTo(map));
  R.unknownLayer = L.polyline(unknown, { color: "#7f949a", weight: 1.4, opacity: .5, dashArray: "3 4", interactive: false }).addTo(map);
  R.route.forEach((layer) => layer.bringToFront());
}

async function loadDepths() {
  const level = routeLevel();
  if (!R.streets || level === R.level) return;
  R.level = level;
  if (level == null) { setResult("Escolha um nível no controle acima para ver a água nas ruas.", "unavailable"); return; }
  const serial = ++R.depthSerial;
  R.overlay.setUrl(`/api/water/overlay.png?level=${level}`);
  try {
    const response = await fetch(`/api/routing/depths?level=${level}`);
    if (!response.ok) throw new Error();
    const depths = await response.json();
    if (serial !== R.depthSerial) return;
    R.depths = depths;
    drawStreets();
    $("kpi-streets").textContent = km(depths.wet_length_m);
    $("kpi-streets-label").textContent = `de ${fmtInt(Math.round(depths.total_length_m / 1000))} km na área das rotas · modelo`;
    const banner = $("route-banner");
    banner.hidden = depths.wet_length_m >= 200;
    if (!banner.hidden) banner.innerHTML = `Com ${fmt(level)} m na régua, o modelo não põe água nas ruas desta área. <button type="button" id="banner-record">Ver no recorde de 2024 (5,35 m)</button>`;
    $("banner-record")?.addEventListener("click", () => Scenario.setLevel(5.35, { label: "Recorde de 05/05/2024 (5,35 m na régua)", source: "record" }));
    calculate();
  } catch { setResult("<strong>Ruas indisponíveis</strong>Não foi possível calcular a água nas ruas agora.", "unavailable"); }
}

const MESSAGES = {
  point_too_far_from_network: "O ponto está fora da área das rotas (Centro, 4º Distrito, Menino Deus e Cidade Baixa) ou longe de uma rua. Use um dos exemplos abaixo ou clique numa rua.",
  unknown_depth_at_point: "Não há profundidade conhecida nesse trecho; escolha outra rua.",
  destination_flooded: "O destino B está alagado neste cenário; escolha um destino seco.",
  no_verified_path: "Não há caminho pelas ruas desta área até um ponto seco neste cenário.",
};

async function calculate() {
  if (!R.depths || R.level == null) return;
  const level = R.level;
  let origin, destination = null;
  if (R.mode === "exit") {
    const { lat, lon } = Scenario.state.point;
    origin = { lat, lon };
  } else {
    if (!R.a) { clearRoute(); setResult("Clique no mapa para marcar a origem A."); return; }
    origin = R.a;
    if (!R.b) { clearRoute(); pin(R.a.lat, R.a.lon, "#197e99", "Origem A", "A"); setResult("Agora clique no destino B."); return; }
    destination = R.b;
  }
  const serial = ++R.serial;
  setResult("Calculando rota...");
  try {
    const response = await fetch("/api/routing/plan", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ origin, destination, level_regua_m: level }) });
    if (!response.ok) throw new Error(`Falha ao calcular (${response.status})`);
    const result = await response.json();
    if (serial !== R.serial) return;
    clearRoute();
    R.serial = serial;
    const levelText = `<small>Cenário de ${fmt(level)} m</small>`;
    if (R.mode === "exit") pin(origin.lat, origin.lon, "#c0703f", Scenario.state.point.label);
    else { pin(R.a.lat, R.a.lon, "#197e99", "Origem A", "A"); pin(R.b.lat, R.b.lon, "#bb6c43", "Destino B", "B"); }
    if (result.status === "already_safe") {
      setResult(`<strong>Ponto seco neste cenário</strong>${result.margin_m == null ? "A água do lago não chega aqui no modelo." : `O rio teria de subir mais ${fmt(result.margin_m, 1)} m para a água chegar aqui.`} Não é preciso sair.<br>${levelText}`, "safe");
    } else if (result.status !== "ok") {
      setResult(`<strong>Sem rota</strong>${MESSAGES[result.reason] || "Não foi possível traçar um caminho."}<br>${levelText}`, "unavailable");
    } else {
      if (result.normal_route) { drawRoute(result.normal_route.coordinates, true); $("legend-normal").hidden = false; }
      drawRoute(result.coordinates);
      const wet = result.route_type === "minimum_exposure";
      const water = wet ? `<span class="route-warn">${km(result.flooded_length_m)} dentro da água, com até <b>${fmt(result.max_depth_m, 2)} m</b> de profundidade.</span>` : `<span>Nenhum trecho com água no caminho.</span>`;
      let head, detail = "";
      if (result.safe_point) {
        const sp = result.safe_point;
        pin(sp.lat, sp.lon, "#11845b", "Ponto seco", "✓");
        head = `${wet ? "Saída com menos água" : "Saída a pé"}: ${km(result.length_m)} (≈ ${result.walk_min} min)`;
        detail = `Até ${sp.street ? `<b>${sp.street}</b>` : "o ponto verde"}, ${sp.margin_m == null ? "fora do alcance da água no modelo" : `onde o rio teria de subir mais ${fmt(sp.margin_m, 1)} m`}.`;
      } else {
        head = `${wet ? "Rota com menos água" : "Caminho seco"}: ${km(result.length_m)} (≈ ${result.walk_min} min)`;
        if (result.normal_route) detail = `Sem alagamento seriam ${km(result.normal_route.length_m)}${result.length_m - result.normal_route.length_m > 20 ? ` (desvio de ${km(result.length_m - result.normal_route.length_m)})` : ""}.`;
      }
      setResult(`<strong>${head}</strong>${detail}<br>${water}<br>${levelText}`, wet ? "wet" : "ok");
      R.routeBounds = L.latLngBounds(result.coordinates).extend([origin.lat, origin.lon]);
      frame();
    }
  } catch (error) { if (serial === R.serial) setResult(`<strong>Erro</strong>${error.message}`, "unavailable"); }
}

function setMode(mode) {
  R.mode = mode;
  $("mode-exit").classList.toggle("active", mode === "exit");
  $("mode-ab").classList.toggle("active", mode === "ab");
  $("route-ab").hidden = mode !== "ab";
  $("route-examples").hidden = mode !== "exit";
  $("route-title").textContent = mode === "exit" ? "Saída até o ponto seco mais próximo" : "Rota entre dois pontos";
  $("route-help").textContent = mode === "exit" ? "Clique no mapa para escolher de onde sair."
    : "Clique na origem A e depois no destino B.";
  R.a = R.b = null;
  $("origin-label").textContent = "Clique no mapa";
  $("destination-label").textContent = "—";
  calculate();
}
$("mode-exit").addEventListener("click", () => setMode("exit"));
$("mode-ab").addEventListener("click", () => setMode("ab"));
$("clear-route").addEventListener("click", () => setMode("ab"));
document.querySelectorAll("#route-examples button").forEach((button) => button.addEventListener("click", () => {
  Scenario.setPoint(Number(button.dataset.lat), Number(button.dataset.lon), button.dataset.label);
}));

map.on("click", (event) => {
  const { lat, lng } = event.latlng;
  if (R.mode === "exit") { Scenario.setPoint(lat, lng, `Ponto ${lat.toFixed(4)}, ${lng.toFixed(4)}`); return; }
  if (!R.a || R.b) { R.a = { lat, lon: lng }; R.b = null; $("origin-label").textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)}`; $("destination-label").textContent = "Clique no destino"; }
  else { R.b = { lat, lon: lng }; $("destination-label").textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)}`; }
  calculate();
});

$("show-observed").addEventListener("change", (event) => {
  if (!R.observed) return;
  if (event.target.checked) R.observed.addTo(map); else map.removeLayer(R.observed);
});

async function start() {
  try {
    const response = await fetch("/api/routing/streets");
    if (!response.ok) throw new Error(`Ruas indisponíveis (${response.status})`);
    R.streets = await response.json();
    const [w, s, e, n] = R.streets.metadata.bbox;
    R.areaBounds = L.latLngBounds([s, w], [n, e]);
    R.area = L.rectangle(R.areaBounds, { color: "#c0703f", weight: 1.5, dashArray: "6 5", fill: false, interactive: false }).addTo(map);
    R.overlay = L.imageOverlay("data:image/gif;base64,R0lGODlhAQABAAAAACw=", R.streets.overlay_bounds, { opacity: 1, interactive: false }).addTo(map);
    R.observed = L.geoJSON(R.streets.flood_extent, { style: { color: "#3d6fb0", weight: 1, dashArray: "4 3", fillColor: "#3d6fb0", fillOpacity: .12 }, interactive: false });
    $("collection-date").insertAdjacentHTML("afterbegin", `Ruas coletadas em ${new Date(R.streets.metadata.collected_at_utc).toLocaleDateString("pt-BR")} (${fmtInt(R.streets.edges.length)} trechos, ${fmtInt(Math.round(R.streets.total_length_m / 1000))} km). `);
    drawStreets();
    frame();
    loadDepths();
  } catch (error) { setResult(`<strong>Mapa indisponível</strong>${error.message}`, "unavailable"); }
}

let depthTimer;
Scenario.subscribe((state, kind) => {
  if (kind === "init") return;
  if (kind === "level") { clearTimeout(depthTimer); depthTimer = setTimeout(loadDepths, 200); }
  if (kind === "point" && R.mode === "exit") { R.routeBounds = null; calculate(); frame(); }
});
start();
