import networkx as nx
import metis

from graphlib import (
    extract_graph_via_nx,
    mark_transfer_ms_per_MB,
    get_functions_in_flight_every_ms,
    analyse_timing_components
)

dijkstra_pairs = None

def get_dijkstra_pairs(network_G, weight_function):
    global dijkstra_pairs
    if dijkstra_pairs is None:
        dijkstra_pairs = list(nx.all_pairs_dijkstra_path_length(network_G, weight=weight_function))
    return dijkstra_pairs

def allocate_servers(composition_G, parts, servers):
    for i, partition in enumerate(parts):
        composition_G.nodes[i]["server"] = servers[partition]
    return composition_G


def transfer_weight(u,v,uv_edge_attr):
    return network_G[u].get("transfer_ms_per_MB",0) + network_G[v].get("transfer_ms_per_MB",0) + uv_edge_attr["transfer_ms_per_MB"]

def schedule_according_to_partitioning(network_G, partitioning, to_schedule_ctx, to_schedule_graph, global_state, CONCURRENCY):
    best_score = None
    best_servers =[]
    final_timing = {}

    current_load = {
        server:[len(x) for x in load] for server,load in global_state.items()
    }

    num_servers_required = max(partitioning)+1

    for origin, dist_dict in get_dijkstra_pairs(network_G, transfer_weight):
        if not network_G.nodes[origin]["server"]:  # filter switches
            continue
        
        server_distances = [x for x in dist_dict.items() if network_G.nodes[x[0]]["server"]]
        ordered_targets = sorted(server_distances, key=lambda x: x[1])[1:]  # skip zero-distance to origin itself
        servers = [origin] + [t for t,cost in ordered_targets[:num_servers_required-1]]

        to_schedule_graph = allocate_servers(to_schedule_graph, partitioning, servers)
        timing = analyse_timing_components(to_schedule_graph, network_G, global_server_load=global_state, accuracy=1, cs_penalty=0, base_time=to_schedule_ctx)
        to_schedule_in_flight = get_functions_in_flight_every_ms(to_schedule_graph, accuracy=1, base_time=to_schedule_ctx)

        valid = True
        for i,entries in enumerate(to_schedule_in_flight):
            if len(entries) > 0:
                for server in servers:
                    extra_load = len(list(filter(lambda x: x["server"] == server, entries)))
                    base_load = current_load[server][i] if i < len(current_load[server]) else 0
                    if extra_load + base_load > CONCURRENCY:
                        valid = False
                        break
                if not valid:
                    break
        if not valid:
            continue
        score = sum([cost for t,cost in ordered_targets[:num_servers_required-1]])
        if best_score is None or score < best_score:
            best_score = score
            best_servers = servers
            final_timing = timing
        else:
            print(f"not an improvement of the current {best_score}..")
    
    if len(best_servers) > 0:
        # actually perform decided allocation
        to_schedule_graph = allocate_servers(to_schedule_graph, partitioning, best_servers)
        # bookkeep global context
        for time, nodelist in enumerate(to_schedule_in_flight):
            for node in nodelist:
                server_state = global_state[node["server"]]
                if len(server_state) <= time:  # global_state time axis has to extend for all servers
                    for _,v in global_state.items():
                        v.extend([[] for _ in range(len(to_schedule_in_flight) - len(v))])
                server_state[time].append(node)
    return len(best_servers) > 0, best_servers, final_timing


def num_servers_in_graph(network_G):
    return len([1 for node in network_G.nodes if network_G.nodes[node]["server"]])


if __name__ == "__main__":
    composition_G = extract_graph_via_nx("example_graph_nx.json")
    for node in composition_G.nodes:
        composition_G.nodes[node]["node_id"] = node

    composition_G_METIS = composition_G.to_undirected()  # partitioning is done on undirected graphs
    composition_G_METIS.graph["edge_weight_attr"] = "size"  # metric for METIS

    network_G = extract_graph_via_nx("network_graph.json")
    network_G = mark_transfer_ms_per_MB(network_G)
    network_servers = num_servers_in_graph(network_G)
    assert network_servers >= 2, "# servers too low"

    CONCURRENCY = 2
    REPEAT_COMPOSITION = 1
    time_offsets = [0,0,0,50,100,200, 200, 200]
    metric = 0
    partitioning = None

    global_ctx = {server:[] for server in range(len(network_G.nodes))}
    total_to_schedule = [(time_offsets[i],composition_G.copy()) for i in range(REPEAT_COMPOSITION)]
    for comp_id, (_, composition) in enumerate(total_to_schedule):
        composition["comp_id"] = comp_id
    print(f"STARTING analysis for {network_servers} servers in a {len(network_G.nodes)} node data centre")
    print(f"The scheduled graph has {len(composition_G.nodes)} functions to invoke")
    for to_schedule_ctx, to_schedule_graph in total_to_schedule:
        for i in range(2,network_servers+1):
            edgecuts,parts = metis.part_graph(composition_G_METIS, i, objtype="cut", minconn=True)#, dbglvl=3)

            num_servers_required = max(parts)+1
            valid, servers_acquired, timing = schedule_according_to_partitioning(
                network_G, parts, to_schedule_ctx, to_schedule_graph, global_ctx, CONCURRENCY
            )
            if valid:
                print("servers: ", servers_acquired, "timing report: ", timing)
                break  # done
            else:
                print(f"could not manage to schedule with only {i} servers..")
    
    # y = [0 for _ in range(len(global_ctx[0]))]
    # for _,server_load in global_ctx.items():
    #     for i,load in enumerate(server_load):
    #         y[i] += len(load)
    # x = range(len(y))
    # # y = [sum([len(server_load[i])]) for i in range(global_ctx_timeline)]
    # plt.bar(x, y)
    # plt.xticks(
    #     ticks=range(0,len(x), 1),
    #     # labels=xlabels,
    #     rotation=45
    # )
    # plt.savefig('plot_metis_in_flight.png')