// Aba "Bairros": porcentagem de prédios afetados por bairro (simulação INCT) no nível do cenário.
const impactMap = L.map("impact-map", { preferCanvas: true, scrollWheelZoom: false }).setView([-30.075, -51.19], 11);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap contributors", maxZoom: 18 }).addTo(impactMap);
new ResizeObserver(() => impactMap.invalidateSize()).observe(document.getElementById("impact-map"));
window.addEventListener("maptab", (event) => { if (event.detail === "impact") setTimeout(() => impactMap.invalidateSize(), 0); });
let impactLayer = null, impactRows = new Map(), selectedImpactName = null, impactRequest = 0, impactKey = undefined;
const impactPalette = ["#dce7e8", "#c1e2e6", "#8bc9d4", "#55a7bf", "#287eaa", "#164b7c"];
const pointMarkerImpact = L.circleMarker([0, 0], { radius: 6, color: "#fff", weight: 2, fillColor: "#c0703f", fillOpacity: 1 });

function impactColor(value) {
  if (value <= 0) return impactPalette[0];
  if (value < 10) return impactPalette[1];
  if (value < 25) return impactPalette[2];
  if (value < 50) return impactPalette[3];
  if (value < 75) return impactPalette[4];
  return impactPalette[5];
}
const escapeHtml = (text) => text.replaceAll("&", "&amp;").replaceAll("<", "&lt;");
function styleImpact() {
  if (impactLayer) impactLayer.setStyle((feature) => ({ fillColor: impactColor(impactRows.get(feature.properties.bairro)?.percentage_exact ?? 0), color: "#356072", weight: feature.properties.bairro === selectedImpactName ? 2.4 : .7, fillOpacity: .8 }));
}
function showImpactBairro(name) {
  selectedImpactName = name;
  const target = document.getElementById("impact-selected");
  const row = impactRows.get(name);
  if (!name) { target.textContent = "Clique em um bairro: ele mostra os valores e leva o ponto do 3D para lá."; styleImpact(); return; }
  if (!row) { target.innerHTML = `<strong>${escapeHtml(name)}</strong><span>Sem prédios afetados neste nível na simulação.</span>`; styleImpact(); return; }
  const percent = row.percentage_exact.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
  target.innerHTML = `<strong>${escapeHtml(name)}</strong><span>${percent}% dos prédios · ${fmtInt(row.affected_buildings)} de ${fmtInt(row.total_buildings)}</span><span>${fmtInt(row.affected_population)} pessoas estimadas</span><button type="button" class="link-button" id="impact-to-3d">Ver o terreno em 3D →</button>`;
  document.getElementById("impact-to-3d").addEventListener("click", () => showMapTab("point"));
  styleImpact();
}

async function updateImpact() {
  const key = Scenario.inctLevel();
  const state = Scenario.state;
  const cacheKey = key ?? `abaixo:${state.level}`;
  if (cacheKey === impactKey) return;
  impactKey = cacheKey;
  const serial = ++impactRequest;
  if (key === null) {
    impactRows = new Map();
    const below = state.level != null;
    document.getElementById("impact-summary").textContent = below ? `${fmt(state.level)} m: abaixo de 3,0 m, a simulação do INCT não indica prédios afetados` : "Aguardando um nível";
    document.getElementById("kpi-people").textContent = below ? "0" : "—";
    document.getElementById("kpi-bairros").textContent = below ? "0" : "—";
    styleImpact(); showImpactBairro(selectedImpactName);
    return;
  }
  try {
    const response = await fetch(`/api/scenario?level=${key}`);
    if (!response.ok) throw new Error("Cenário indisponível");
    const scenario = await response.json();
    if (serial !== impactRequest) return;
    impactRows = new Map(scenario.neighborhoods.filter((row) => row.affected_buildings > 0).map((row) => [row.bairro, row]));
    const note = state.level > 10 ? " (limite da simulação: 10,0 m)" : Number(key) !== state.level ? ` (grade do INCT: ${key.replace(".", ",")} m)` : "";
    document.getElementById("impact-summary").textContent = `${scenario.totals.bairros_atingidos} bairros com prédios afetados${note}`;
    document.getElementById("kpi-people").textContent = fmtInt(scenario.totals.affected_population);
    document.getElementById("kpi-bairros").textContent = fmtInt(scenario.totals.bairros_atingidos);
    const relation = document.getElementById("relation-impact");
    if (relation) relation.textContent = `INCT em ${key.replace(".", ",")} m: ${fmtInt(scenario.totals.affected_population)} pessoas e ${scenario.totals.bairros_atingidos} bairros (estimativa)`;
    styleImpact(); showImpactBairro(selectedImpactName);
  } catch (error) { document.getElementById("impact-summary").textContent = error.message; }
}

async function startImpact() {
  try {
    const response = await fetch("/api/bairros/geometry");
    if (!response.ok) throw new Error("Limites dos bairros indisponíveis");
    const geometry = await response.json();
    document.getElementById("impact-collected").textContent = new Date(geometry.metadata.collected_at).toLocaleDateString("pt-BR");
    impactLayer = L.geoJSON(geometry, {
      style: () => ({ fillColor: impactPalette[0], color: "#356072", weight: .7, fillOpacity: .8 }),
      onEachFeature: (feature, layer) => {
        layer.bindTooltip(feature.properties.bairro, { sticky: true });
        layer.on("click", (event) => {
          showImpactBairro(feature.properties.bairro);
          Scenario.setPoint(event.latlng.lat, event.latlng.lng, feature.properties.bairro);
        });
      },
    }).addTo(impactMap);
    impactMap.fitBounds(impactLayer.getBounds(), { padding: [12, 12] });
    pointMarkerImpact.addTo(impactMap);
    impactKey = undefined;
    await updateImpact();
  } catch (error) { document.getElementById("impact-summary").textContent = error.message; }
}

Scenario.subscribe((state, kind) => {
  if (kind === "level" || kind === "init") updateImpact();
  if (kind === "point" || kind === "init") pointMarkerImpact.setLatLng([state.point.lat, state.point.lon]);
});
startImpact();
