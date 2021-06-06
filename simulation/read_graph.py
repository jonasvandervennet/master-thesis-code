import sys

from graphlib import (
    extract_graph_via_nx,
    draw_graph
)

if __name__ == "__main__":
    filename = sys.argv[1]
    draw_kind = sys.argv[2]
    
    graph = extract_graph_via_nx(f"{filename}.json")
    draw_graph(graph, filename=f"{filename}.png", kind=draw_kind)
    
    # DANGEROUS: CAN DESTROY GRAPH DEFINITION FILE!
    # graph=graph.to_undirected()
    # with open(f"{filename}.json", "w") as ofp:
    #     dump = nx.jit_data(graph, indent=2)
    #     ofp.write(dump)
