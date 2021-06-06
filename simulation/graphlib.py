import json
from math import ceil
from collections import deque

import networkx as nx
import matplotlib.pyplot as plt

from networkx.algorithms.shortest_paths.generic import shortest_path
from networkx.drawing.nx_agraph import graphviz_layout


def extract_graph(filename: str):
    with open(filename) as ifp:
        data = json.loads(ifp.read())
    graph = nx.DiGraph()
    queue = deque([(None, data)])
    i = 1  # node identifier (for creating edges)
    while len(queue) > 0:
        parent, current = queue.popleft()
        attributes = {k:v for k,v in current.items() if k != "children"}
        graph.add_node(i, **attributes)
        if parent is not None:
            graph.add_edge(parent, i)
        queue.extend([(i, child) for child in current['children']])
        i += 1
    return graph

def extract_graph_via_nx(filename: str):
    with open(filename) as ifp:
        data = json.loads(ifp.read())
    graph = nx.jit_graph(data, create_using=nx.DiGraph())
    return graph

def draw_graph(G, filename='nx_test.png', kind="default"):
    pos = graphviz_layout(G, prog='dot')
    if kind == "color":
        max_edge_weight = max([attr["size"] for _,attr in G.edges.items()])
        edge_color = ['red' if attr["size"] == max_edge_weight else 'blue' for _,attr in G.edges.items()]
        nx.draw(G, pos, node_color="lightgray", with_labels=True, arrows=True, edge_color=edge_color)
    elif kind == "time":
        max_edge_weight = max([attr["size"] for _,attr in G.edges.items()])
        edge_color = ['red' if attr["size"] == max_edge_weight else 'blue' for _,attr in G.edges.items()]
        labels = {n: f'{G.nodes[n]["time"]}ms' for n in G.nodes}
        nx.draw(G, pos, node_color="lightgray", with_labels=True, labels=labels, arrows=True, edge_color=edge_color, font_size=10)
    elif kind == "bandwidth":
        # max_edge_weight = max([attr["bandwidth"] for _,attr in G.edges.items()])
        # edge_color = ['red' if attr["bandwidth"] == max_edge_weight else 'blue' for _,attr in G.edges.items()]
        nx.draw(G, pos, node_color="lightgray", with_labels=False, arrows=False, node_size=100, alpha=0.7)
    elif kind =="caqr":
        pos = graphviz_layout(G, prog='dot', args="-Gsplines=true -Gnodesep=0.6 -Goverlap=false")
        nx.draw(G, pos, node_color="lightgray", arrows=True)
    else:
        print("default")
        nx.draw(G, pos, node_color="lightgray", with_labels=True, arrows=True)
    plt.savefig(filename)

def transfer_size_to_time_in_ms(network_G, source, target, transfer_size_in_MB):
    path = shortest_path(network_G, source=source, target=target, weight="transfer_ms_per_MB")
    transfer_ms_per_MB = 0
    for i,start in enumerate(path[:-1]):
        end = path[i+1]
        edge = network_G.edges[start,end]
        transfer_ms_per_MB += edge["transfer_ms_per_MB"]
    return transfer_ms_per_MB * transfer_size_in_MB

def mark_transfer_ms_per_MB(network_G):
    assert all(["bandwidth" in datadict for _,datadict in network_G.edges.items()]), "bandwidth was not defined in network graph!"
    for i in network_G.edges:
        edge = network_G.edges[i]
        bandwidth = edge["bandwidth"]  # in Gbps
        edge["transfer_ms_per_MB"] = 8 / bandwidth
    return network_G
         
def mark_potential_cold_start(node, server_load, start_time):
    """
    This function checks whether there is a function active before the provided start_time (inclusive!).
    if there is no previously active function, a cold start is marked on the node for future reference.

    (The inclusive bound ensures that a cold start that makes the runtime available at the proposed
    start time but was initiated by another (previous) function is counter correctly.)
    """
    for load in server_load[:start_time+1]:
        if len(load) > 0:
            node["cold_start"] = False
            return False
    # no previous function in flight found, so mark cold start
    node["cold_start"] = True
    return True


def analyse_timing_components(composition_G, network_G, global_server_load, cs_penalty, base_time, accuracy):
    for node in composition_G.nodes:
        for forbidden, default in [("start_time", 0), ("end_time", 0), ("cold_start", False)]:
            composition_G.nodes[node][forbidden] = default  # add default value
        assert "server" in composition_G.nodes[node].keys(), "server should be defined, as it is used here!"
    
    current_highest_cost = 0
    components = {}
    n_func = len(composition_G.nodes)
    for path in nx.all_simple_paths(composition_G, source=0, target=n_func-1):
        # clean up path markings before using it
        for node in path:
            composition_G.nodes[node]["cold_start"] = False
        warm_servers_this_path = set()
        
        # print("Current path: ", path)
        cost_breakdown = {
            "cold_start_time": 0,
            "execution_time": 0,
            "transfer_time": 0
        }
        for i,start in enumerate(path):
            start_node = composition_G.nodes[start]

            proposed_start_time = int((base_time + sum(cost_breakdown.values())) * accuracy)
            if start_node["server"] not in warm_servers_this_path and \
                mark_potential_cold_start(start_node, global_server_load[start_node["server"]], proposed_start_time):
                # print(f"Node {start} incurred a cold start cost of {cs_penalty}ms")
                cost_breakdown["cold_start_time"] += cs_penalty
                warm_servers_this_path.add(start_node["server"])
            
            # mark only the latest start time with corresponding end time
            if (new_cost := sum(cost_breakdown.values())) > start_node["start_time"]:
                start_node["start_time"] = new_cost
                start_node["end_time"] = new_cost + start_node["time"]

            cost_breakdown["execution_time"] += start_node["time"]

            if i != len(path) - 1:
                # not final node in the path, look at next link
                end = path[i+1]
                end_node = composition_G.nodes[end]
                edge = composition_G.edges[start, end]
                
                if start_node["server"] != end_node["server"]:
                    time_cost = transfer_size_to_time_in_ms(
                        network_G,
                        source=start_node["server"],
                        target=end_node["server"],
                        transfer_size_in_MB=edge["size"])

                    cost_breakdown["transfer_time"] += time_cost
        cost = sum(cost_breakdown.values())

        if cost > current_highest_cost:
            current_highest_cost = cost
            components = cost_breakdown
    return components


def insert_schedule_into_composition_graph(G, schedule):
    for node in G.nodes:
        for forbidden in ["server"]:
            assert forbidden not in G.nodes[node].keys(), \
                f"{forbidden} should be undefined, otherwise data may be overwritten!"
    for i, placement in enumerate(schedule):
        # nodes are numbered starting with 1
        G.nodes[i]["server"] = placement.index(1)
    return G


def get_functions_in_flight_every_ms(G, accuracy=10, base_time=0):
    total_duration = base_time+ max([G.nodes[node]["end_time"] for node in G.nodes])
    in_flight_per_ms = [[] for _ in range(10*(ceil(total_duration)+1))]  # notation [[]] * X results in aliasing between all sublists!
    for node in G.nodes:
        node = G.nodes[node]
        # if node timing is accurate on 1/10th of a millisecond, multiplying by 10 will give an integer as index
        for i in range(int((base_time+node["start_time"])*accuracy), int((base_time+node["end_time"])*accuracy)):
            in_flight_per_ms[i].append(node)
    return in_flight_per_ms
