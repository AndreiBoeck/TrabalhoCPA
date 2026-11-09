const state = { level: 5.3, curve: [], request: 0 };
const $ = (id) => document.getElementById(id);
const numberBR = (value, digits = 0) => Number(value).toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits });

function showStatus(message) {
  $("status").textContent = message;
  $("status").classList.toggle("visible", Boolean(message));
}

async function readJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Falha ao carregar os dados (${response.status})`);
  return response.json();
}

function formatPercent(value) {
  return `${numberBR(value, value > 0 && value < 0.1 ? 2 : 1)}%`;
}

function renderBars(rows) {
  const affected = rows.filter((row) => row.affected_buildings > 0)
    .sort((a, b) => b.percentage_exact - a.percentage_exact || a.bairro.localeCompare(b.bairro, "pt-BR"));
  $("bar-count").textContent = `${affected.length} bairros`;
  const bars = $("bars");
  bars.replaceChildren();
  if (!affected.length) {
    const empty = document.createElement("p"); empty.className = "empty"; empty.textContent = "Nenhum bairro atingido neste nível."; bars.append(empty);
    return;
  }
  affected.forEach((row) => {
    const item = document.createElement("div"); item.className = "bar-row"; item.setAttribute("role", "listitem");
    const name = document.createElement("span"); name.className = "bar-name"; name.textContent = row.bairro; name.title = row.bairro;
    const track = document.createElement("div"); track.className = "bar-track";
    const fill = document.createElement("div"); fill.className = "bar-fill"; fill.style.width = `${Math.min(100, row.percentage_exact)}%`; track.append(fill);
    const value = document.createElement("strong"); value.className = "bar-value"; value.textContent = formatPercent(row.percentage_exact);
    item.append(name, track, value); bars.append(item);
  });
  bars.setAttribute("aria-label", `Gráfico de barras: ${affected.length} bairros atingidos no nível de ${numberBR(state.level, 1)} metros`);
}

function renderRanking(rows) {
  const ranking = $("ranking"); ranking.replaceChildren();
  rows.filter((row) => row.affected_population > 0).forEach((row, index) => {
    const item = document.createElement("li");
    const position = document.createElement("span"); position.className = "rank-position"; position.textContent = String(index + 1).padStart(2, "0");
    const name = document.createElement("span"); name.className = "rank-name"; name.textContent = row.bairro;
    const value = document.createElement("strong"); value.className = "rank-value"; value.textContent = numberBR(row.affected_population);
    item.append(position, name, value); ranking.append(item);
  });
}

function drawCurve() {
  const svg = $("curve");
  if (!state.curve.length) return;
  const left = 57, right = 583, top = 21, bottom = 207;
  const maximum = Math.ceil(Math.max(...state.curve.map((row) => row.affected_population)) / 50000) * 50000;
  const x = (level) => left + (level - 3) / 7 * (right - left);
  const y = (population) => bottom - population / maximum * (bottom - top);
  const line = state.curve.map((row, index) => `${index ? "L" : "M"}${x(row.level).toFixed(2)},${y(row.affected_population).toFixed(2)}`).join(" ");
  const area = `${line} L${right},${bottom} L${left},${bottom} Z`;
  const current = state.curve.find((row) => row.level === state.level);
  const grid = [0, .25, .5, .75, 1].map((fraction) => {
    const value = maximum * fraction;
    return `<line x1="${left}" y1="${y(value)}" x2="${right}" y2="${y(value)}" stroke="#e7eef0"/><text x="${left - 8}" y="${y(value) + 4}" text-anchor="end" font-size="11" fill="#81949c">${Math.round(value / 1000)} mil</text>`;
  }).join("");
  const ticks = [3, 4, 5, 6, 7, 8, 9, 10].map((level) => `<text x="${x(level)}" y="${bottom + 20}" text-anchor="middle" font-size="11" fill="#81949c">${level}</text>`).join("");
  svg.innerHTML = `${grid}<path d="${area}" fill="#dcedf1"/><path d="${line}" fill="none" stroke="#267f98" stroke-width="3" stroke-linejoin="round"/><line x1="${x(5.35)}" y1="${top}" x2="${x(5.35)}" y2="${bottom}" stroke="#c17b50" stroke-width="2" stroke-dasharray="5 4"/><text x="${x(5.35) + 6}" y="${top + 5}" font-size="10" fill="#a7653e">5,35 m</text><line x1="${left}" y1="${bottom}" x2="${right}" y2="${bottom}" stroke="#a5b7be"/>${ticks}${current ? `<circle cx="${x(current.level)}" cy="${y(current.affected_population)}" r="6" fill="#145e76" stroke="white" stroke-width="2"/>` : ""}`;
  svg.setAttribute("aria-label", `Curva de população afetada entre 3 e 10 metros. Nível selecionado: ${numberBR(state.level, 1)} metros. Recorde de maio de 2024 marcado em 5,35 metros.`);
}

function renderScenario(data) {
  $("affected-population").textContent = numberBR(data.city_totals.affected_population);
  $("affected-buildings").textContent = numberBR(data.city_totals.affected_buildings);
  $("affected-neighborhoods").textContent = numberBR(data.city_totals.bairros_atingidos);
  renderBars(data.neighborhoods);
  renderRanking(data.ranking);
}

async function setLevel(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 3 || parsed > 10) return;
  state.level = Math.round(parsed * 10) / 10;
  const formatted = `${numberBR(state.level, 1)} m`;
  $("level-output").textContent = formatted;
  $("title-level").textContent = formatted;
  drawCurve();
  const request = ++state.request;
  try {
    const data = await readJson(`/api/scenario?level=${state.level.toFixed(1)}`);
    if (request !== state.request) return;
    renderScenario(data);
    showStatus("");
  } catch (error) {
    if (request === state.request) showStatus(error.message || "Não foi possível carregar o cenário.");
  }
}

async function start() {
  try {
    state.curve = await readJson("/api/curve");
    $("level-range").addEventListener("input", (event) => setLevel(event.target.value));
    await setLevel($("level-range").value);
  } catch (error) {
    showStatus(error.message || "Não foi possível iniciar a página.");
  }
}

start();
