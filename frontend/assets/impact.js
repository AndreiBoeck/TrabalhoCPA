const impactMap = L.map("impact-map", { preferCanvas: true, scrollWheelZoom: false }).setView([-30.075, -51.19], 11);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap contributors", maxZoom: 18 }).addTo(impactMap);
new ResizeObserver(() => impactMap.invalidateSize()).observe(document.getElementById("impact-map"));
const impactSlider = document.getElementById("impact-level");
let impactLayer = null, impactRows = new Map(), selectedImpactName = null, impactRequest = 0;
const impactPalette = ["#dce7e8", "#c1e2e6", "#8bc9d4", "#55a7bf", "#287eaa", "#164b7c"];

function impactColor(value) {
  if (value <= 0) return impactPalette[0];
  if (value < 10) return impactPalette[1];
  if (value < 25) return impactPalette[2];
  if (value < 50) return impactPalette[3];
  if (value < 75) return impactPalette[4];
  return impactPalette[5];
}
function showImpactBairro(name) {
  selectedImpactName = name;
  const row = impactRows.get(name);
  const target = document.getElementById("impact-selected");
  if (!row) { target.textContent = "Toque em um bairro no mapa para ver seus valores."; return; }
  const percent = row.percentage_exact.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
  target.innerHTML = `<strong>${name.replaceAll("&", "&amp;").replaceAll("<", "&lt;")}</strong><span>${percent}% dos prédios · ${row.affected_buildings.toLocaleString("pt-BR")} de ${row.total_buildings.toLocaleString("pt-BR")}</span><span>${row.affected_population.toLocaleString("pt-BR")} pessoas estimadas</span>`;
}
async function updateImpact() {
  const serial = ++impactRequest;
  const level = Number(impactSlider.value).toFixed(1);
  document.getElementById("impact-level-value").textContent = `${level.replace(".", ",")} m`;
  try {
    const response = await fetch(`/api/scenario?level=${level}`);
    if (!response.ok) throw new Error("Cenário indisponível");
    const scenario = await response.json();
    if (serial !== impactRequest) return;
    impactRows = new Map(scenario.neighborhoods.map(row => [row.bairro, row]));
    document.getElementById("impact-summary").textContent = `${scenario.totals.bairros_atingidos} bairros com prédios afetados`;
    if (impactLayer) impactLayer.setStyle(feature => ({ fillColor: impactColor(impactRows.get(feature.properties.bairro)?.percentage_exact ?? 0), color: "#356072", weight: .7, fillOpacity: .8 }));
    showImpactBairro(selectedImpactName);
  } catch (error) { document.getElementById("impact-summary").textContent = error.message; }
}
let impactTimer;
impactSlider.addEventListener("input", () => {
  document.getElementById("impact-level-value").textContent = `${Number(impactSlider.value).toFixed(1).replace(".", ",")} m`;
  clearTimeout(impactTimer);
  impactTimer = setTimeout(updateImpact, 80);
});

async function startImpact() {
  try {
    const response = await fetch("/api/bairros/geometry");
    if (!response.ok) throw new Error("Limites dos bairros indisponíveis");
    const geometry = await response.json();
    document.getElementById("impact-collected").textContent = new Date(geometry.metadata.collected_at).toLocaleDateString("pt-BR");
    impactLayer = L.geoJSON(geometry, {
      style: feature => ({ fillColor: impactColor(impactRows.get(feature.properties.bairro)?.percentage_exact ?? 0), color: "#356072", weight: .7, fillOpacity: .8 }),
      onEachFeature: (feature, layer) => {
        layer.bindTooltip(feature.properties.bairro, { sticky: true });
        layer.on("click", () => showImpactBairro(feature.properties.bairro));
      },
    }).addTo(impactMap);
    impactMap.fitBounds(impactLayer.getBounds(), { padding: [12, 12] });
    await updateImpact();
  } catch (error) { document.getElementById("impact-summary").textContent = error.message; }
}
startImpact();
