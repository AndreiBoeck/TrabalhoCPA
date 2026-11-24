const $ = (id) => document.getElementById(id);
const map = L.map("route-map", { preferCanvas: true }).setView([-30.030, -51.230], 15);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap contributors", maxZoom: 19 }).addTo(map);
const roads = L.layerGroup().addTo(map);
new ResizeObserver(() => map.invalidateSize()).observe($("route-map"));
let origin = null, destination = null, originMarker = null, destinationMarker = null, routeLine = null, normalLine = null, requestSerial = 0;

function coordinates(point) { return `${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}`; }
function setResult(message, unavailable = false) {
  $("route-result").innerHTML = message;
  $("route-result").classList.toggle("unavailable", unavailable);
}
function clearRoute() {
  requestSerial++;
  origin = destination = null;
  if (originMarker) map.removeLayer(originMarker);
  if (destinationMarker) map.removeLayer(destinationMarker);
  if (routeLine) map.removeLayer(routeLine);
  if (normalLine) map.removeLayer(normalLine);
  originMarker = destinationMarker = routeLine = normalLine = null;
  $("origin-label").textContent = "Não escolhida";
  $("destination-label").textContent = "Não escolhido";
  $("instruction").textContent = "Clique sobre uma linha de rua para marcar a origem A.";
  setResult("Aguardando origem e destino.");
}
async function calculate() {
  const request = ++requestSerial;
  setResult("Calculando rota...");
  try {
    const response = await fetch("/api/routing/plan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ origin: { lat: origin.lat, lon: origin.lng }, destination: { lat: destination.lat, lon: destination.lng } }) });
    if (!response.ok) throw new Error(`Falha ao calcular (${response.status})`);
    const result = await response.json();
    if (request !== requestSerial) return;
    if (result.status !== "ok") {
      const messages = { destination_flooded: "O destino está em área alagada neste cenário.", point_too_far_from_network: "Escolha pontos sobre as linhas de rua destacadas no mapa (até 25 m).", unknown_depth_at_point: "A profundidade nesse trecho é desconhecida; escolha outra rua destacada.", no_verified_path: "Não há caminho verificável entre esses pontos neste cenário." };
      setResult(`<strong>Sem rota verificada</strong>${messages[result.reason] || "Não foi possível traçar um caminho."}`, true);
      return;
    }
    if (result.normal_route) normalLine = L.polyline(result.normal_route.coordinates, { color: "#5a6a71", weight: 5, opacity: .85, dashArray: "8 7" }).addTo(map);
    routeLine = L.polyline(result.coordinates, { color: "#176aab", weight: 6, opacity: .95 }).addTo(map);
    map.fitBounds(routeLine.getBounds().pad(.2));
    const km = (result.length_m / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 2 });
    const depth = result.max_depth_m.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
    const wet = result.route_type === "minimum_exposure";
    const baseline = result.normal_route ? `<br>Sem alagamento (hipótese): ${(result.normal_route.length_m / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} km. Desvio: +${Math.max(0, Math.round(result.length_m - result.normal_route.length_m))} m.` : "";
    setResult(`<strong>${wet ? "Saída de menor exposição estimada" : "Caminho seco mais curto"}</strong>${km} km pela rede de ruas.${baseline}${wet ? `<br>Maior profundidade estimada após a origem: ${depth} m. Trecho na água: ${Math.round(result.flooded_length_m)} m.<br><b>Cenário histórico; não indica passagem segura hoje.</b>` : "<br>Nenhum trecho alagado na rota."}<br><small>Os pontos foram ajustados à rua mais próxima (${result.snapped.origin.distance_m} m e ${result.snapped.destination.distance_m} m).</small>`);
  } catch (error) { if (request === requestSerial) setResult(`<strong>Erro</strong>${error.message}`, true); }
}
map.on("click", (event) => {
  if (origin && destination) clearRoute();
  if (!origin) {
    origin = event.latlng;
    originMarker = L.marker(origin).addTo(map).bindTooltip("A · origem", { permanent: true, direction: "top" });
    $("origin-label").textContent = coordinates(origin);
    $("instruction").textContent = "Agora clique sobre uma linha de rua para marcar o destino B.";
  } else {
    destination = event.latlng;
    destinationMarker = L.marker(destination).addTo(map).bindTooltip("B · destino", { permanent: true, direction: "top" });
    $("destination-label").textContent = coordinates(destination);
    $("instruction").textContent = "Clique novamente para começar uma nova rota.";
    calculate();
  }
});
$("clear-route").addEventListener("click", clearRoute);

function showExample(start, end) {
  clearRoute();
  origin = L.latLng(start[0], start[1]);
  destination = L.latLng(end[0], end[1]);
  originMarker = L.marker(origin).addTo(map).bindTooltip("A · origem", { permanent: true, direction: "top" });
  destinationMarker = L.marker(destination).addTo(map).bindTooltip("B · destino", { permanent: true, direction: "top" });
  $("origin-label").textContent = coordinates(origin);
  $("destination-label").textContent = coordinates(destination);
  $("instruction").textContent = "Exemplo carregado. Clique no mapa para começar outra rota.";
  calculate();
}
$("example-detour").addEventListener("click", () => showExample([-30.0273335, -51.227312], [-30.0297283, -51.2277399]));
$("example-flooded").addEventListener("click", () => showExample([-30.02637925, -51.2269302], [-30.03048905, -51.2339254]));

async function start() {
  try {
    const response = await fetch("/api/routing/network");
    if (!response.ok) throw new Error(`Rede indisponível (${response.status})`);
    const network = await response.json();
    const nodes = new Map(network.nodes.map((node) => [node.id, node]));
    if (network.flood_extent) {
      L.geoJSON(network.flood_extent, { style: { color: "#5598b2", weight: 1, fillColor: "#58a5c8", fillOpacity: .28 }, interactive: false }).addTo(map);
    }
    network.edges.forEach((edge) => {
      const a = nodes.get(edge.source), b = nodes.get(edge.target);
      if (!a || !b) return;
      const wet = edge.depth_m !== null && edge.depth_m > 0;
      L.polyline([[a.lat, a.lon], [b.lat, b.lon]], { color: edge.depth_m === null ? "#9ca8ad" : wet ? "#d86b56" : "#9cb5bb", weight: wet ? 4 : 2, opacity: wet ? .8 : .6, dashArray: edge.depth_m === null ? "4 4" : null, interactive: false }).addTo(roads);
    });
    const bbox = network.metadata.bbox;
    map.invalidateSize();
    map.fitBounds([[bbox[1], bbox[0]], [bbox[3], bbox[2]]]);
    $("collection-date").textContent = `Dados coletados em ${new Date(network.metadata.collected_at_utc).toLocaleString("pt-BR")}. Área: centro de Porto Alegre.`;
  } catch (error) { setResult(`<strong>Mapa indisponível</strong>${error.message}`, true); }
}
start();
