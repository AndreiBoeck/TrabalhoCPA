// Worker que encaminha todo o tráfego de cpa.lambari.dev.br para o container do dashboard (FastAPI).
import { Container, getContainer } from "@cloudflare/containers";

export class Dashboard extends Container {
  defaultPort = 8000;
  sleepAfter = "30m";
}

export default {
  async fetch(request, env) {
    return getContainer(env.DASHBOARD).fetch(request);
  },
};
