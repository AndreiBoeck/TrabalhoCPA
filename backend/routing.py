"""Cálculo de caminhos em uma rede com profundidade estimada por trecho.

O módulo não infere profundidade do JSON agregado do INCT. A rede e as
profundidades devem vir de uma fonte geográfica validada antes de uso real.
"""

from __future__ import annotations

from collections import defaultdict
from heapq import heappop, heappush
from math import isfinite
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class Node(BaseModel):
    id: str = Field(min_length=1)
    depth_m: float = Field(ge=0)


class Edge(BaseModel):
    source: str
    target: str
    length_m: float = Field(gt=0)
    depth_m: Optional[float] = Field(default=None, ge=0)
    bidirectional: bool = True


class RouteRequest(BaseModel):
    nodes: List[Node] = Field(min_length=1, max_length=20000)
    edges: List[Edge] = Field(max_length=40000)
    origin: str
    destination: str


def best_exit(depths, neighbors, origin, goals) -> dict:
    """Busca em grafo genérico: caminho seco mais curto ou, da origem alagada, a menor exposição.

    ``depths[n]`` é a profundidade no nó; ``neighbors(n)`` devolve (destino, comprimento,
    profundidade do trecho ou None, referência do trecho). ``goals`` é o conjunto de destinos
    aceitos (o primeiro alcançado vence). Compara caminhos por (maior profundidade depois da
    origem, distância na água, distância total). Após sair da água, não permite voltar a trechos
    alagados. Profundidade desconhecida (None) nunca é atravessada.
    """
    flooded_origin = depths[origin] > 0
    start = (origin, not flooded_origin)

    def expand(state):
        current, dry = state
        for target, length, edge_depth, ref in neighbors(current):
            if edge_depth is None or depths[target] is None:
                continue
            water_depth = max(edge_depth, depths[target])
            if dry and water_depth > 0:
                continue
            yield (target, dry or depths[target] == 0), length, water_depth, ref

    is_goal = lambda state: state[1] and state[0] in goals
    # Primeiro encontra a menor profundidade máxima possível. Uma única busca
    # lexicográfica não basta: um gargalo futuro pode empatar dois máximos antes
    # distintos e inverter a preferência pela distância na água.
    minimum_max = {start: 0.0}
    queue = [(0.0, 0, start)]
    counter = 0
    depth_limit = None
    while queue:
        maximum, _, state = heappop(queue)
        if maximum != minimum_max[state]:
            continue
        if is_goal(state):
            depth_limit = maximum
            break
        for next_state, _, water_depth, _ in expand(state):
            candidate = max(maximum, water_depth)
            if candidate < minimum_max.get(next_state, float("inf")):
                minimum_max[next_state] = candidate
                counter += 1
                heappush(queue, (candidate, counter, next_state))
    if depth_limit is None:
        return {"status": "no_route", "reason": "no_verified_path"}

    best = {start: (0.0, 0.0)}
    previous = {}
    queue = [((0.0, 0.0), 0, start)]
    while queue:
        cost, _, state = heappop(queue)
        if cost != best[state]:
            continue
        if is_goal(state):
            path, refs = [state[0]], []
            while state in previous:
                state, ref = previous[state]
                path.append(state[0])
                refs.append(ref)
            path.reverse()
            refs.reverse()
            return {
                "status": "ok",
                "route_type": "minimum_exposure" if flooded_origin else "shortest_dry",
                "node_ids": path,
                "edge_refs": refs,
                "length_m": cost[1],
                "flooded_length_m": cost[0],
                "max_depth_m": depth_limit,
            }
        for next_state, length, water_depth, ref in expand(state):
            if water_depth > depth_limit:
                continue
            next_cost = (cost[0] + (length if water_depth > 0 else 0), cost[1] + length)
            if next_cost < best.get(next_state, (float("inf"),) * 2):
                best[next_state] = next_cost
                previous[next_state] = (state, ref)
                counter += 1
                heappush(queue, (next_cost, counter, next_state))
    raise RuntimeError("A busca de rota perdeu um caminho alcançável")


def calculate_route(request: RouteRequest) -> dict:
    """Valida a rede recebida e calcula a rota entre dois nós (veja ``best_exit``)."""
    depths: Dict[str, float] = {}
    for node in request.nodes:
        if node.id in depths:
            raise ValueError(f"Nó duplicado: {node.id}")
        if not isfinite(node.depth_m):
            raise ValueError("Profundidade de nó inválida")
        depths[node.id] = node.depth_m
    if request.origin not in depths or request.destination not in depths:
        raise ValueError("Origem ou destino ausente da rede")
    if depths[request.destination] > 0:
        return {"status": "no_route", "reason": "destination_flooded"}

    adjacency: Dict[str, List[Tuple[str, float, Optional[float], None]]] = defaultdict(list)
    for edge in request.edges:
        if edge.source not in depths or edge.target not in depths:
            raise ValueError("Trecho referencia nó ausente")
        if edge.source == edge.target or not isfinite(edge.length_m):
            raise ValueError("Trecho inválido")
        if edge.depth_m is not None and not isfinite(edge.depth_m):
            raise ValueError("Profundidade de trecho inválida")
        adjacency[edge.source].append((edge.target, edge.length_m, edge.depth_m, None))
        if edge.bidirectional:
            adjacency[edge.target].append((edge.source, edge.length_m, edge.depth_m, None))
    result = best_exit(depths, lambda node: adjacency[node], request.origin, {request.destination})
    result.pop("edge_refs", None)
    return result
