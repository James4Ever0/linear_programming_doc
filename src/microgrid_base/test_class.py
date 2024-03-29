from log_utils import logger_print


class A:
    def __init__(self):
        ...

    def B(self):
        return B(self)


class B:
    def __init__(self, a: A):
        self.a = a
        logger_print("CLASS NAME?", self.__class__.__name__)
        logger_print("CREATING B")


a = A()
b = a.B()

import json
import networkx as nx
import rich

graph_data = {"a": 1, "b": 2}
G = nx.Graph(**graph_data)

G.add_node(1, **{"val": 1, "val2": 2})
G.add_node(2, **{"val": 1, "val2": 2})
G.add_node(3, **{"val": 1, "val2": 2})

G.add_edge(1, 2)
G.add_edge(2, 3)

G.add_node(4)
G.add_node(5)

G.add_edge(4, 5)
# G.neighbors(node_id)
for n_with_items in G.nodes.items():
    n, d = n_with_items
    logger_print("NODE", n, type(n))
    logger_print("DATA", d, type(d))
    # G.nodes[n]

logger_print()
G.nodes[2]["attr2"] = 2

logger_print(G.nodes[2])  # attrs of this node.

logger_print()
# logger_print(list(G.neighbors(1)))
components = list(nx.connected_components(G))
logger_print(components)

logger_print()
logger_print(G.graph, type(G.graph))  # this is dict.

from networkx.readwrite import json_graph

data = json_graph.node_link_data(G)

logger_print()
logger_print(data)

G0 = json_graph.node_link_graph(data)

logger_print("GRAPH DATA?", G0.graph)

# attribute just do not collide with id.

from pydantic import BaseModel


class BM(BaseModel):
    a: float


new_bm = BM.parse_obj(dict(a=1))
logger_print(new_bm)

from typing import Dict

a: Dict[int, dict] = {1: {}}
