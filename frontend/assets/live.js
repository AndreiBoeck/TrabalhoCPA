// Leitura atual da ANA, controle do cenário e gráfico de previsão.
const liveEl = (id) => document.getElementById(id);
const scenarioRange = liveEl("scenario-range");

async function refreshLive() {
  try {
    const response = await fetch("/api/live");
    if (!response.ok) throw new Error("Consulta indisponível");
    Scenario.setLive(await response.json());
  } catch (error) {
    Scenario.setLive({ status: "unavailable", reason: "source_unavailable", recent: [], forecast: { status: "unavailable" } });
  }
}
refreshLive();
setInterval(refreshLive, 300000);

function renderCurrent(live) {
  const card = liveEl("current-card");
  if (!live) return;
  card.classList.toggle("stale", live.status !== "recent");
  liveEl("current-level-query").textContent = live.queried_at ? new Date(live.queried_at).toLocaleString("pt-BR") : "—";
  if (live.status === "unavailable") {
    liveEl("current-level-value").textContent = "Sem dado recente";
    liveEl("current-level-msl").textContent = "—";
    liveEl("current-level-status").textContent = "Não foi possível obter leitura da ANA agora.";
    return;
  }
  liveEl("current-level-value").textContent = `${fmt(live.level_regua_m)} m`;
  liveEl("current-level-msl").textContent = `régua do Cais Mauá · ${fmt(live.level_m)} m no referencial corrigido da ANA`;
  liveEl("current-level-time").textContent = `Medição ${live.measurement_at.replace("T", " ").slice(0, 16)} · estação ${live.station_code} · ${live.station_name}`;
  liveEl("current-level-status").textContent = live.source_error
    ? "O serviço da ANA não respondeu agora; mostrando a última leitura obtida. Nova tentativa em 5 min."
    : live.status === "recent" ? "Leitura recente (até 2 h). Atualiza a cada 5 min."
    : "Leitura com mais de 2 h: pode não representar o nível atual.";
}

function renderScenario(state) {
  const manual = !state.sync;
  liveEl("sync-pill").className = `sync-pill ${manual ? "manual" : state.source === "live" ? "live" : "stale"}`;
  liveEl("sync-text").textContent = manual ? "Cenário manual" : state.source === "live" ? "Tempo real" : "Tempo real · sem leitura recente";
  liveEl("sync-button").hidden = !manual;
  liveEl("scenario-card").classList.toggle("manual", manual);
  liveEl("scenario-level").textContent = state.level == null ? "—" : `${fmt(state.level)} m`;
  liveEl("scenario-label").textContent = state.label;
  if (state.level != null && document.activeElement !== scenarioRange) scenarioRange.value = Math.min(10, state.level);
  const forecastOk = state.live?.forecast?.status === "ok";
  document.querySelectorAll("[data-forecast]").forEach((button) => { button.disabled = !forecastOk; });
}

scenarioRange.addEventListener("input", () => {
  Scenario.setLevel(Number(scenarioRange.value), { label: "Nível escolhido no controle" });
});
liveEl("sync-button").addEventListener("click", () => { Scenario.resync(); toast("Tela sincronizada com a leitura atual da ANA."); });
liveEl("record-button").addEventListener("click", () => Scenario.setLevel(5.35, { label: "Recorde de 05/05/2024 (5,35 m na régua)", source: "record" }));
document.querySelectorAll("[data-forecast]").forEach((button) => {
  button.addEventListener("click", () => {
    const point = Scenario.state.live?.forecast?.points?.find((p) => p.hours === Number(button.dataset.forecast));
    if (point) useForecastPoint(point);
  });
});

function useForecastPoint(point) {
  Scenario.setLevel(point.regua_m, {
    label: `Previsão para ${fmtDateTime(point.time)} (+${point.hours} h) · faixa ${fmt(point.low_regua_m)}–${fmt(point.high_regua_m)} m`,
    time: point.time, source: "forecast",
  });
}

function renderForecast(state) {
  const svg = liveEl("forecast-chart");
  const live = state.live;
  const forecast = live?.forecast;
  const recent = (live?.recent || []).map(([t, v]) => [t, v + REGUA_OFFSET]);
  if (!recent.length) {
    svg.innerHTML = '<text x="40" y="140" fill="#80949b" font-size="13">Sem leituras recentes da ANA para desenhar o gráfico.</text>';
    liveEl("forecast-badge").textContent = "Indisponível";
    liveEl("forecast-note").textContent = "A previsão depende da série recente da ANA.";
    return;
  }
  const points = forecast?.status === "ok" ? forecast.points : [];
  const left = 52, right = 884, top = 16, bottom = 240;
  const t0 = new Date(recent[0][0]).getTime();
  const tEnd = points.length ? new Date(points[points.length - 1].time).getTime() : new Date(recent[recent.length - 1][0]).getTime();
  const values = [...recent.map((r) => r[1]), ...points.flatMap((p) => [p.low_regua_m, p.high_regua_m])];
  const low = Math.floor(Math.min(...values) * 2) / 2 - 0.25, high = Math.ceil(Math.max(...values) * 2) / 2 + 0.25;
  const x = (iso) => left + (new Date(iso).getTime() - t0) / (tEnd - t0) * (right - left);
  const y = (v) => bottom - (v - low) / (high - low) * (bottom - top);
  const ticks = Array.from({ length: 5 }, (_, i) => low + (high - low) * i / 4)
    .map((v) => `<line x1="${left}" y1="${y(v)}" x2="${right}" y2="${y(v)}" stroke="#e5eff1"/><text x="${left - 8}" y="${y(v) + 4}" text-anchor="end" font-size="11" fill="#81969c">${fmt(v, 1)} m</text>`).join("");
  const days = [];
  for (let d = new Date(t0); d.setHours(24, 0, 0, 0) <= tEnd;) {
    const px = left + (d.getTime() - t0) / (tEnd - t0) * (right - left);
    days.push(`<line x1="${px}" x2="${px}" y1="${bottom}" y2="${bottom + 4}" stroke="#b9c8cc"/><text x="${px}" y="262" text-anchor="middle" font-size="10" fill="#81969c">${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}</text>`);
  }
  const obsPath = recent.map((r, i) => `${i ? "L" : "M"}${x(r[0]).toFixed(1)},${y(r[1]).toFixed(1)}`).join(" ");
  const last = recent[recent.length - 1];
  let forecastSvg = "";
  if (points.length) {
    const start = { time: last[0], regua_m: last[1], low_regua_m: last[1], high_regua_m: last[1] };
    const series = [start, ...points];
    const band = series.map((p, i) => `${i ? "L" : "M"}${x(p.time).toFixed(1)},${y(p.high_regua_m).toFixed(1)}`).join(" ")
      + " " + [...series].reverse().map((p) => `L${x(p.time).toFixed(1)},${y(p.low_regua_m).toFixed(1)}`).join(" ") + " Z";
    const line = series.map((p, i) => `${i ? "L" : "M"}${x(p.time).toFixed(1)},${y(p.regua_m).toFixed(1)}`).join(" ");
    const dots = points.map((p, i) => `<circle class="fc-dot${state.time === p.time ? " active" : ""}" data-index="${i}" cx="${x(p.time)}" cy="${y(p.regua_m)}" r="6"><title>+${p.hours} h · ${fmtDateTime(p.time)} · ${fmt(p.regua_m)} m (faixa ${fmt(p.low_regua_m)}–${fmt(p.high_regua_m)} m)</title></circle>`).join("");
    forecastSvg = `<path d="${band}" fill="#f1c9a4" opacity=".45"/><path d="${line}" fill="none" stroke="#c0703f" stroke-width="2.4" stroke-dasharray="6 4"/>${dots}`;
  }
  const nowX = x(last[0]);
  let selected = "";
  if (state.level != null && state.level >= low && state.level <= high) {
    selected = `<line x1="${left}" x2="${right}" y1="${y(state.level)}" y2="${y(state.level)}" stroke="#155f86" stroke-width="1.6" stroke-dasharray="3 4"/><text x="${right - 4}" y="${y(state.level) - 6}" text-anchor="end" font-size="11" fill="#155f86">cenário ${fmt(state.level)} m</text>`;
  } else if (state.level != null) {
    const above = state.level > high;
    selected = `<text x="${left + 8}" y="${above ? top + 12 : bottom - 6}" font-size="11" font-weight="700" fill="#155f86">${above ? "↑" : "↓"} cenário em uso: ${fmt(state.level)} m (fora da escala)</text>`;
  }
  svg.innerHTML = `${ticks}${days.join("")}<line x1="${nowX}" x2="${nowX}" y1="${top}" y2="${bottom}" stroke="#9fb4ba" stroke-dasharray="2 3"/><text x="${nowX + 5}" y="${top + 10}" font-size="10" fill="#6d858d">última leitura</text><path d="${obsPath}" fill="none" stroke="#267f98" stroke-width="2.2"/>${forecastSvg}${selected}`;
  svg.querySelectorAll(".fc-dot").forEach((dot) => dot.addEventListener("click", () => useForecastPoint(points[Number(dot.dataset.index)])));
  if (points.length) {
    const p72 = points[points.length - 1];
    liveEl("forecast-badge").innerHTML = `Em 72 h: <strong>${fmt(p72.regua_m)} m</strong> <span>(${fmt(p72.low_regua_m)}–${fmt(p72.high_regua_m)})</span>`;
    liveEl("forecast-note").innerHTML = `${forecast.method} Emitida a partir da leitura de ${fmtDateTime(forecast.issued_from)}. No teste com 12 meses que o modelo não viu, o erro médio em 72 h foi de ${fmt(p72.mae_m * 100, 0)} cm, contra ${fmt(p72.mae_persistence_m * 100, 0)} cm de simplesmente repetir o último nível. <strong>Modelo estatístico experimental</strong>: não usa chuva prevista, vento nem vazão dos rios e não substitui os <a href="https://sace.sgb.gov.br/guaiba/" target="_blank" rel="noopener noreferrer">boletins do SGB</a>. <a href="/api/forecast/model" target="_blank" rel="noopener noreferrer">Coeficientes e validação</a>.`;
  } else {
    liveEl("forecast-badge").textContent = "Previsão indisponível";
    liveEl("forecast-note").textContent = "Sem série recente suficiente (20 dias com poucas lacunas) para calcular a previsão.";
  }
}

Scenario.subscribe((state, kind) => {
  if (kind === "init" || kind === "level" || kind === "live") {
    renderCurrent(state.live);
    renderScenario(state);
    renderForecast(state);
  }
});
