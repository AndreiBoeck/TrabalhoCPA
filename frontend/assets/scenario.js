// Estado compartilhado da Tela 2: um único nível do Guaíba (régua do Cais Mauá) usado por todos os componentes.
// Em "tempo real" o nível segue a leitura mais recente da ANA; qualquer escolha do usuário passa para "manual"
// até que ele clique em "Voltar ao tempo real".
const REGUA_OFFSET = 1.18; // régua = referencial corrigido da ANA + 1,18 m (pico de 05/05/2024: 5,35 m ↔ 4,17 m)
const fmt = (value, digits = 2) => Number(value).toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
const fmtInt = (value) => Number(value).toLocaleString("pt-BR");
const fmtDateTime = (iso) => `${iso.slice(8, 10)}/${iso.slice(5, 7)} ${iso.slice(11, 16)}`;

const Scenario = (() => {
  const listeners = new Set();
  const state = {
    sync: true, level: null, label: "Aguardando leitura da ANA", source: "loading", time: null, live: null,
    point: { lat: -30.0225, lon: -51.2190, label: "Rodoviária · Centro/Floresta" },
  };
  const emit = (kind) => listeners.forEach((fn) => fn(state, kind));
  function applyLive() {
    const live = state.live;
    if (live && live.level_regua_m != null && live.status !== "unavailable") {
      state.level = live.level_regua_m;
      state.time = live.measurement_at;
      state.source = live.status === "recent" ? "live" : "stale";
      state.label = live.status === "recent" ? `Tempo real · leitura de ${fmtDateTime(live.measurement_at)}`
        : `Última leitura disponível (${fmtDateTime(live.measurement_at)}) · desatualizada`;
    } else {
      state.level = null; state.time = null; state.source = "unavailable";
      state.label = "Sem leitura da ANA no momento · escolha um nível";
    }
  }
  return {
    state,
    subscribe(fn) { listeners.add(fn); fn(state, "init"); },
    setLive(live) { state.live = live; if (state.sync) applyLive(); emit(state.sync ? "level" : "live"); },
    setLevel(level, { label = "Cenário escolhido manualmente", time = null, source = "manual" } = {}) {
      state.sync = false; state.level = Math.round(Number(level) * 100) / 100;
      state.label = label; state.time = time; state.source = source; emit("level");
    },
    resync() { state.sync = true; applyLive(); emit("level"); },
    setPoint(lat, lon, label) { state.point = { lat, lon, label }; emit("point"); },
    // Nível no referencial da ANA (metros acima do nível médio do mar), usado pelo modelo de água.
    levelMsl() { return state.level == null ? null : state.level - REGUA_OFFSET; },
    // Nível válido para a grade do INCT (3,0 a 10,0 m em passos de 0,1 m).
    inctLevel() {
      if (state.level == null || state.level < 2.95) return null;
      return Math.min(10, Math.round(state.level * 10) / 10).toFixed(1);
    },
  };
})();

function toast(message) {
  const element = document.getElementById("toast");
  element.textContent = message;
  element.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => element.classList.remove("show"), 2600);
}
