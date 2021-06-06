import networkx as nx
import math

# args
import sys
target_filename = sys.argv[1]

N = 2048
BLOCKSIZE = 64
G = nx.DiGraph()

# STAGE 1: factor
source = 0
G.add_node(source, memory=256, time=1)

n_operations = math.ceil(N/BLOCKSIZE)**2
transfer_size = int(BLOCKSIZE*BLOCKSIZE*4)  # in bytes

base = len(G.nodes)
factor_nodes = list(range(base, base+n_operations))

for i in factor_nodes:
    G.add_node(i, memory=256, time=1)
    G.add_edge(source, i, size=transfer_size)

# STAGE 2: factor_tree
transfer_size = int(BLOCKSIZE*BLOCKSIZE*4/2)  # in bytes (upper triangle)

stepsize = 1
while True:
    indices = list(range(stepsize-1, len(factor_nodes), stepsize))
    if len(indices) == 1:
        break
    for i in range(0, len(indices), 2):
        node = len(G.nodes)
        G.add_node(node, memory=256, time=1)
        G.add_edge(factor_nodes[indices[i]], node, size=transfer_size)
        G.add_edge(factor_nodes[indices[i+1]], node, size=transfer_size)
        factor_nodes[indices[i+1]] = node
    stepsize *= 2


# STAGE 3: apply_qt_h
horizontal_transfer_size = int(BLOCKSIZE*BLOCKSIZE*4/2)  # in bytes (lower triangle)
vertical_transfer_size = int(BLOCKSIZE*BLOCKSIZE)  # need to update entire block
size = math.ceil(N/BLOCKSIZE)
for i in range(size):
    for j in range(size):
        node = len(G.nodes)
        G.add_node(node, memory=256, time=1)
        G.add_edge(factor_nodes[i*size], node, size=horizontal_transfer_size)
        G.add_edge(factor_nodes[i*size+j], node, size=vertical_transfer_size)
        factor_nodes[i*size+j] = node


# STAGE 4: apply_qt_tree
transfer_size = int(BLOCKSIZE*BLOCKSIZE*4/2)  # in bytes (upper half)

stepsize = 1
while True:
    indices = list(range(stepsize-1, len(factor_nodes), stepsize))
    if len(indices) == 1:
        break
    for i in range(0, len(indices), 2):
        node = len(G.nodes)
        G.add_node(node, memory=256, time=1)
        G.add_edge(factor_nodes[indices[i]], node, size=transfer_size)
        G.add_edge(factor_nodes[indices[i+1]], node, size=transfer_size)
        factor_nodes[indices[i+1]] = node
    stepsize *= 2



# Write result to file
with open(f"{target_filename}.json", "w") as ofp:
    dump = nx.jit_data(G, indent=2)
    ofp.write(dump)
