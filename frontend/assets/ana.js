const anaById = (id) => document.getElementById(id);
const anaNumber = (value, digits = 0) => Number(value).toLocaleString("pt-BR", { maximumFractionDigits: digits, minimumFractionDigits: digits });
const shortDate = (date) => `${date.slice(8, 10)}/${date.slice(5, 7)}`;
let anaData = null;

function axis(width, height, left, right, top, bottom, min, max, unit) {
  const plotHeight = bottom - top;
  return Array.from({ length: 5 }, (_, i) => {
    const value = min + (max - min) * i / 4;
    const y = bottom - plotHeight * i / 4;
    return `<line x1="${left}" y1="${y}" x2="${right}" y2="${y}" stroke="#e5eff1"/><text x="${left - 9}" y="${y + 4}" text-anchor="end" font-size="10" fill="#81969c">${anaNumber(value, unit === "%" ? 0 : 1)}${unit}</text>`;
  }).join("");
}

function drawSeries(rows, days) {
  const svg = anaById("ana-series");
  const valid = rows.filter((row) => row[1] !== null);
  if (!valid.length) { svg.innerHTML = '<text x="40" y="100" fill="#80949b">Sem medição no período.</text>'; return; }
  const left = 50, right = 704, top = 18, bottom = 211;
  const low = Math.floor(Math.min(...valid.map((row) => row[1])) * 2) / 2;
  const high = Math.ceil(Math.max(...valid.map((row) => row[1])) * 2) / 2 + .1;
  const x = (index) => left + index / Math.max(1, rows.length - 1) * (right - left);
  const y = (level) => bottom - (level - low) / (high - low) * (bottom - top);
  let previous = false;
  const path = rows.map((row, index) => {
    if (row[1] === null) { previous = false; return ""; }
    const instruction = `${previous ? "L" : "M"}${x(index).toFixed(2)},${y(row[1]).toFixed(2)}`;
    previous = true;
    return instruction;
  }).join(" ");
  const peak = valid.reduce((best, row) => row[1] > best[1] ? row : best);
  const peakIndex = rows.indexOf(peak);
  svg.innerHTML = `${axis(720, 250, left, right, top, bottom, low, high, " m")}<path d="${path}" fill="none" stroke="#267f98" stroke-width="2"/><circle cx="${x(peakIndex)}" cy="${y(peak[1])}" r="5" fill="#b85f43" stroke="white" stroke-width="1.5"/><text x="${Math.max(left + 3, Math.min(right - 75, x(peakIndex) + 8))}" y="${Math.max(15, y(peak[1]) - 7)}" font-size="10" fill="#a7553c">pico ${anaNumber(peak[1], 2)} m</text><text x="${left}" y="237" font-size="10" fill="#81969c">${shortDate(days[0].date)}</text><text x="${right}" y="237" text-anchor="end" font-size="10" fill="#81969c">${shortDate(days[days.length - 1].date)}</text>`;
  svg.setAttribute("aria-label", `Nível observado entre ${days[0].date} e ${days[days.length - 1].date}; pico de ${anaNumber(peak[1], 2)} metros. Lacunas não interpoladas.`);
}

function drawRange(days) {
  const svg = anaById("ana-range");
  const valid = days.filter((day) => day.min !== null);
  if (!valid.length) { svg.innerHTML = '<text x="40" y="100" fill="#80949b">Sem medição no período.</text>'; return; }
  const left = 47, right = 505, top = 18, bottom = 188;
  const low = Math.floor(Math.min(...valid.map((day) => day.min)) * 2) / 2;
  const high = Math.ceil(Math.max(...valid.map((day) => day.max)) * 2) / 2 + .1;
  const x = (index) => left + (index + .5) / days.length * (right - left);
  const y = (level) => bottom - (level - low) / (high - low) * (bottom - top);
  const bars = days.map((day, index) => day.min === null ? "" : `<line x1="${x(index)}" y1="${y(day.min)}" x2="${x(index)}" y2="${y(day.max)}" stroke="#287e97" stroke-width="${Math.max(2, Math.min(8, (right - left) / days.length * .65))}" stroke-linecap="round"/>`).join("");
  svg.innerHTML = `${axis(520, 230, left, right, top, bottom, low, high, " m")}${bars}<text x="${left}" y="215" font-size="10" fill="#81969c">${shortDate(days[0].date)}</text><text x="${right}" y="215" text-anchor="end" font-size="10" fill="#81969c">${shortDate(days[days.length - 1].date)}</text>`;
  svg.setAttribute("aria-label", `Faixa diária de níveis entre ${days[0].date} e ${days[days.length - 1].date}.`);
}

function drawCompleteness(days) {
  const svg = anaById("ana-completeness");
  const left = 45, right = 505, top = 18, bottom = 188;
  const x = (index) => left + index / days.length * (right - left);
  const width = Math.max(2, (right - left) / days.length - 1);
  const bars = days.map((day, index) => {
    const percent = day.available / day.expected * 100;
    const y = bottom - percent / 100 * (bottom - top);
    return `<rect x="${x(index)}" y="${y}" width="${width}" height="${bottom - y}" fill="${percent < 50 ? "#cd7862" : "#32869c"}"/>`;
  }).join("");
  svg.innerHTML = `${axis(520, 230, left, right, top, bottom, 0, 100, "%")}${bars}<text x="${left}" y="215" font-size="10" fill="#81969c">${shortDate(days[0].date)}</text><text x="${right}" y="215" text-anchor="end" font-size="10" fill="#81969c">${shortDate(days[days.length - 1].date)}</text>`;
  svg.setAttribute("aria-label", `Completude diária das medições entre ${days[0].date} e ${days[days.length - 1].date}.`);
}

function clearAna(message) {
  for (const id of ["ana-peak", "ana-peak-date", "ana-available", "ana-coverage", "ana-days"]) anaById(id).textContent = "—";
  for (const id of ["ana-series", "ana-range", "ana-completeness"]) anaById(id).replaceChildren();
  anaById("ana-note").textContent = message;
}

function renderAna() {
  if (!anaData) return;
  const start = anaById("date-start").value, end = anaById("date-end").value;
  if (start > end) { clearAna("A data inicial deve ser anterior ou igual à final."); return; }
  const days = anaData.daily.filter((day) => day.date >= start && day.date <= end);
  const rows = anaData.observations.filter((row) => row[0].slice(0, 10) >= start && row[0].slice(0, 10) <= end);
  if (!days.length) { clearAna("Não há dados neste período."); return; }
  const available = days.reduce((sum, day) => sum + day.available, 0);
  const expected = days.reduce((sum, day) => sum + day.expected, 0);
  const valid = rows.filter((row) => row[1] !== null);
  const peak = valid.length ? valid.reduce((best, row) => row[1] > best[1] ? row : best) : null;
  anaById("ana-peak").textContent = peak ? `${anaNumber(peak[1], 2)} m` : "Sem leitura";
  anaById("ana-peak-date").textContent = peak ? `${peak[0].slice(8, 10)}/${peak[0].slice(5, 7)}/${peak[0].slice(0, 4)} ${peak[0].slice(11, 16)}` : "—";
  anaById("ana-available").textContent = anaNumber(available);
  anaById("ana-coverage").textContent = `${anaNumber(100 * available / expected, 1)}% dos ${anaNumber(expected)} horários`;
  anaById("ana-days").textContent = anaNumber(days.length);
  drawSeries(rows, days);
  drawRange(days);
  drawCompleteness(days);
  anaById("ana-note").textContent = `${anaData.metadata.time_note} As lacunas são mantidas; nenhum nível ausente foi tratado como zero.`;
}

async function startAna() {
  try {
    const response = await fetch("/api/ana/history");
    if (!response.ok) throw new Error(`Falha ao carregar a série ANA (${response.status})`);
    anaData = await response.json();
    const { first_date: first, last_date: last, collected_at: collected } = anaData.metadata;
    for (const id of ["date-start", "date-end"]) { anaById(id).min = first; anaById(id).max = last; anaById(id).addEventListener("change", renderAna); }
    anaById("date-start").value = first;
    anaById("date-end").value = last;
    document.querySelectorAll(".ana-collected").forEach((element) => { element.textContent = collected.slice(0, 10).split("-").reverse().join("/"); });
    const valid = anaData.observations.filter((row) => row[1] !== null);
    const eventPeak = valid.reduce((best, row) => row[1] > best[1] ? row : best);
    anaById("ana-event-peak").textContent = `${anaNumber(eventPeak[1], 2)} m`;
    renderAna();
    const [low, high] = await Promise.all([fetch("/api/scenario?level=5.3"), fetch("/api/scenario?level=5.4")]);
    if (low.ok && high.ok) {
      const a = await low.json(), b = await high.json();
      anaById("inct-event-impact").textContent = `${anaNumber(a.city_totals.affected_population)} / ${anaNumber(b.city_totals.affected_population)}`;
    }
  } catch (error) { anaById("ana-note").textContent = error.message || "Série histórica indisponível."; }
}
startAna();

async function updateCurrentLevel() {
  const card = document.querySelector(".current-level");
  try {
    const response = await fetch("/api/ana/latest");
    if (!response.ok) throw new Error("Consulta indisponível");
    const data = await response.json();
    card.classList.toggle("stale", data.status !== "recent");
    anaById("current-level-query").textContent = new Date(data.queried_at).toLocaleString("pt-BR");
    if (data.status === "recent") {
      anaById("current-level-value").textContent = `${anaNumber(data.level_m, 2)} m`;
      anaById("current-level-time").textContent = `Medição: ${data.measurement_at.replace("T", " ")} · estação ${data.station_code}`;
      anaById("current-level-status").textContent = "Leitura recente · horário da fonte sem fuso explícito.";
    } else {
      anaById("current-level-value").textContent = "Sem dado recente";
      anaById("current-level-time").textContent = data.measurement_at ? `Última medição: ${data.measurement_at.replace("T", " ")} · estação ${data.station_code}` : `Estação ${data.station_code} · Usina do Gasômetro`;
      anaById("current-level-status").textContent = "O último valor não foi usado como nível atual.";
    }
  } catch (error) {
    card.classList.add("stale");
    anaById("current-level-value").textContent = "Sem dado recente";
    anaById("current-level-time").textContent = "Estação 87450020 · Usina do Gasômetro";
    anaById("current-level-query").textContent = "—";
    anaById("current-level-status").textContent = "Não foi possível consultar a ANA.";
  }
}
updateCurrentLevel();
setInterval(updateCurrentLevel, 300000);
