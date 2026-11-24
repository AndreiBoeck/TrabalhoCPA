const terrainCanvas = document.getElementById("terrain-canvas");
const terrainContext = terrainCanvas.getContext("2d");
let terrainData = null;

function drawTerrain() {
  if (!terrainData) return;
  const region = terrainData.regions[document.getElementById("terrain-region").value];
  const rect = terrainCanvas.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  terrainCanvas.width = Math.round(rect.width * ratio);
  terrainCanvas.height = Math.round(rect.height * ratio);
  terrainContext.setTransform(ratio, 0, 0, ratio, 0, 0);
  const width = rect.width, height = rect.height;
  const background = terrainContext.createLinearGradient(0, 0, 0, height);
  background.addColorStop(0, "#dbeef2"); background.addColorStop(1, "#f8f7ee");
  terrainContext.fillStyle = background;
  terrainContext.fillRect(0, 0, width, height);
  const elevation = region.elevation_m, water = region.water_depth_m, n = elevation.length;
  const angle = Number(document.getElementById("terrain-angle").value) * Math.PI / 180;
  const exaggeration = Number(document.getElementById("terrain-exaggeration").value);
  const showWater = document.getElementById("terrain-water").checked;
  const cs = Math.cos(angle), sn = Math.sin(angle), scale = Math.min(width * .31, height * .40);
  const valid = elevation.flat().filter(value => value !== null);
  const min = Math.min(...valid), max = Math.max(...valid);
  const project = (r, c, z) => {
    const x = c / (n - 1) * 2 - 1, y = r / (n - 1) * 2 - 1;
    return [width / 2 + (x * cs - y * sn) * scale,
            height * .69 + (x * sn + y * cs) * scale * .57 - (z - min) * exaggeration * 1.25];
  };
  const cells = [];
  for (let r = 0; r < n - 1; r++) for (let c = 0; c < n - 1; c++) {
    const heights = [elevation[r][c], elevation[r][c + 1], elevation[r + 1][c + 1], elevation[r + 1][c]];
    if (heights.some(value => value === null)) continue;
    const depths = [water[r][c], water[r][c + 1], water[r + 1][c + 1], water[r + 1][c]];
    const x = (c + .5) / (n - 1) * 2 - 1, y = (r + .5) / (n - 1) * 2 - 1;
    cells.push({ r, c, heights, depths, order: x * sn + y * cs });
  }
  cells.sort((a, b) => a.order - b.order);
  const corners = [[0, 0], [0, 1], [1, 1], [1, 0]];
  const polygon = (cell, surface) => {
    terrainContext.beginPath();
    corners.forEach(([dr, dc], i) => {
      const point = project(cell.r + dr, cell.c + dc, cell.heights[i] + (surface ? cell.depths[i] + .25 : 0));
      if (i === 0) terrainContext.moveTo(...point); else terrainContext.lineTo(...point);
    });
    terrainContext.closePath();
  };
  for (const cell of cells) {
    const mean = cell.heights.reduce((a, b) => a + b, 0) / 4;
    const t = Math.max(0, Math.min(1, (mean - min) / Math.max(1, max - min)));
    polygon(cell, false);
    terrainContext.fillStyle = `hsl(${154 - 99 * t}, ${28 + 6 * t}%, ${62 - 15 * t}%)`;
    terrainContext.fill();
    terrainContext.strokeStyle = "rgba(37,69,66,.08)";
    terrainContext.lineWidth = .6;
    terrainContext.stroke();
    if (showWater && cell.depths.some(value => value > .05)) {
      polygon(cell, true);
      terrainContext.fillStyle = "rgba(37,132,190,.78)";
      terrainContext.fill();
      terrainContext.strokeStyle = "rgba(15,77,127,.24)";
      terrainContext.stroke();
    }
  }
  const wet = water.flat().filter(value => value > .05);
  document.getElementById("terrain-metrics").textContent = `${region.label} · relevo amostrado: ${min.toFixed(0)}–${max.toFixed(0)} m · maior profundidade modelada na malha: ${Math.max(...wet).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} m.`;
  document.getElementById("terrain-status").textContent = showWater ? "Azul: água modelada em 06/05/2024" : "Camada de água oculta";
}

for (const id of ["terrain-region", "terrain-angle", "terrain-exaggeration", "terrain-water"]) {
  document.getElementById(id).addEventListener("input", drawTerrain);
}
new ResizeObserver(drawTerrain).observe(terrainCanvas);
async function startTerrain() {
  try {
    const response = await fetch("/api/terrain/historical");
    if (!response.ok) throw new Error("Dados do relevo indisponíveis");
    terrainData = await response.json();
    document.getElementById("terrain-collected").textContent = new Date(terrainData.metadata.collected_at_utc).toLocaleDateString("pt-BR");
    drawTerrain();
  } catch (error) { document.getElementById("terrain-status").textContent = error.message; }
}
startTerrain();
