// Abas do componente de mapas. Mapas Leaflet em abas ocultas precisam recalcular o tamanho ao aparecer.
document.querySelectorAll(".map-tabs [data-tab]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".map-tabs [data-tab]").forEach((other) => {
      const active = other === button;
      other.classList.toggle("active", active);
      other.setAttribute("aria-selected", String(active));
      const pane = document.getElementById(other.getAttribute("aria-controls"));
      pane.hidden = !active;
      pane.classList.toggle("active", active);
    });
    window.dispatchEvent(new CustomEvent("maptab", { detail: button.dataset.tab }));
  });
});
function showMapTab(tab) { document.querySelector(`.map-tabs [data-tab="${tab}"]`)?.click(); }

// Endereço com #aba=point|route|impact&nivel=5.35&ponto=-30.0012,-51.1994 abre a tela já na aba, no cenário e no ponto indicados.
window.addEventListener("load", () => {
  const params = new URLSearchParams(location.hash.slice(1));
  if (params.get("aba")) showMapTab(params.get("aba"));
  const level = Number(params.get("nivel"));
  if (params.get("nivel") && Number.isFinite(level)) Scenario.setLevel(level, { label: `Cenário ${fmt(level)} m (link)` });
  const [lat, lon] = (params.get("ponto") || "").split(",").map(Number);
  if (Number.isFinite(lat) && Number.isFinite(lon) && params.get("ponto")) Scenario.setPoint(lat, lon, `Ponto ${lat.toFixed(4)}, ${lon.toFixed(4)} (link)`);
});
