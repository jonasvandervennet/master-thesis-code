import networkx as nx

# args
import sys
target_filename = sys.argv[1]

G = nx.DiGraph()  # make undirected at the very end

source = 0
G.add_node(source, server=False)

layer1 = []  # 8
for i in range(8):
    node = len(G.nodes)
    layer1.append(node)
    G.add_node(node, server=False)
    G.add_edge(source, node, bandwidth=80)

layer2 = []  # 64
for switch in layer1:
    for i in range(8):
        node = len(G.nodes)
        layer2.append(node)
        G.add_node(node, server=False)
        G.add_edge(switch, node, bandwidth=40)

servers = []  # 1024
for switch in layer2:
    for i in range(16):
        node = len(G.nodes)
        servers.append(node)
        G.add_node(node, server=True)
        G.add_edge(switch, node, bandwidth=10)


# Write result to file
with open(f"{target_filename}.json", "w") as ofp:
    dump = nx.jit_data(G.to_undirected(), indent=2)
    ofp.write(dump)
