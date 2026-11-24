const mockScreenButtons = [...document.querySelectorAll("[data-screen]")];
const mockPanelButtons = [...document.querySelectorAll("[data-panel]")];
const mockScreen1 = document.getElementById("mock-screen-1");
const mockScreen2 = document.getElementById("mock-screen-2");

function refreshVisibleMap(panel) {
  requestAnimationFrame(() => {
    if (panel === "impact" && typeof impactMap !== "undefined") impactMap.invalidateSize();
    if (panel === "route" && typeof map !== "undefined") {
      map.invalidateSize();
      if (typeof routeLine === "undefined" || !routeLine) map.fitBounds([[-30.041, -51.247], [-30.020, -51.217]]);
    }
    if (panel === "terrain" && typeof drawTerrain === "function") drawTerrain();
  });
}

function showMockScreen(screen, updateAddress = true) {
  const isFirst = screen === "1";
  mockScreen1.hidden = !isFirst;
  mockScreen2.hidden = isFirst;
  document.getElementById("mock-breadcrumb-current").textContent = `Tela ${screen}`;
  mockScreenButtons.forEach(button => {
    const active = button.dataset.screen === screen;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  if (!isFirst) refreshVisibleMap(document.querySelector("[data-panel].active")?.dataset.panel || "impact");
  if (updateAddress) history.replaceState(null, "", `/mockup?tela=${screen}`);
  window.scrollTo({ top: 0, behavior: "instant" });
}

function showMockPanel(panel) {
  mockPanelButtons.forEach(button => {
    const active = button.dataset.panel === panel;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
    button.tabIndex = active ? 0 : -1;
  });
  document.querySelectorAll(".mock-map-pane").forEach(pane => {
    const active = pane.id === `mock-panel-${panel}`;
    pane.hidden = !active;
    pane.classList.toggle("active", active);
  });
  document.querySelector(".mock-section-count").textContent = `${String(mockPanelButtons.findIndex(button => button.dataset.panel === panel) + 1).padStart(2, "0")} / 03`;
  refreshVisibleMap(panel);
}

mockScreenButtons.forEach(button => button.addEventListener("click", () => showMockScreen(button.dataset.screen)));
mockPanelButtons.forEach(button => button.addEventListener("click", () => showMockPanel(button.dataset.panel)));
document.querySelector(".mock-map-toolbar").addEventListener("keydown", event => {
  if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
  event.preventDefault();
  const current = mockPanelButtons.findIndex(button => button.classList.contains("active"));
  const next = (current + (event.key === "ArrowRight" ? 1 : -1) + mockPanelButtons.length) % mockPanelButtons.length;
  mockPanelButtons[next].focus();
  showMockPanel(mockPanelButtons[next].dataset.panel);
});

showMockScreen(new URLSearchParams(location.search).get("tela") === "1" ? "1" : "2", false);
