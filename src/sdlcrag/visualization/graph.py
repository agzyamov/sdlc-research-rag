"""Knowledge graph data for the web (rendered with Sigma.js + graphology in `web/`).

NetworkX merges triples into one node per entity; `node_link_data` serializes it. Labels are
untrusted (arXiv titles, LLM-extracted names): Sigma draws them on a canvas, never as HTML.
"""

import networkx as nx

from sdlcrag.core.models import SdlcPhase, Triple
from sdlcrag.visualization.charts import phase_label


def build_graph(triples: list[Triple]) -> nx.DiGraph:
    g = nx.DiGraph()
    for t in triples:
        g.add_node(t.subject, type=t.subject_type, name=t.subject_label or t.subject)
        g.add_node(t.object, type=t.object_type)
        g.add_edge(t.subject, t.object, label=t.predicate)
    return g


def _display_label(node: str, data: dict) -> str:
    """Papers show their title; phases their numbered lifecycle name ("4. Testing")."""
    if data.get("type") == "phase" and node in SdlcPhase._value2member_map_:
        return phase_label(SdlcPhase(node))
    return str(data.get("name") or node)


def graph_json(triples: list[Triple]) -> dict:
    """{"nodes": [{"id", "type", "label", "degree"}], "edges": [{"source", "target", "label"}]}."""
    g = build_graph(triples)
    nx.set_node_attributes(g, dict(g.degree()), "degree")
    nx.set_node_attributes(g, {n: _display_label(n, d) for n, d in g.nodes(data=True)}, "label")
    data = nx.node_link_data(g, edges="edges")
    for node in data["nodes"]:
        node.pop("name", None)
    return data
