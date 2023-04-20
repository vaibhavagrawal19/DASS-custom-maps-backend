import heapq

def dijkistra(map, source, dest):

    print(map)

    # initialise the distance from the source with infinity for each node
    distances = {node: float("inf") for node in map["nodes"]}

    # distance of the source from the source is zero
    distances[source] = 0

    # maintain a list of nodes that we have visited (or relaxed)
    visited = {node: False for node in map["nodes"]}

    prev_nodes = {node: False for node in map["nodes"]}

    # initialize a priority queue
    queue = [(0, source)]


    while queue:
        # get the node in queue with the lowest distance from the source
        curr_dist, curr_node = heapq.heappop(queue)

        if curr_node == dest:
            break

        if not visited[curr_node]:
            visited[curr_node] = True

        print("currently relaxing " + curr_node)    

        for edge in map["edges"]:
            if edge["node1"] != curr_node and edge["node2"] != curr_node:
                continue

            # the node adjacent to curr_node
            node = None

            if edge["node1"] == curr_node:
                node = edge["node2"]
            else:
                node = edge["node1"]

            print("about to check " + node)

            if not visited[node]:
                if distances[node] > int(curr_dist) + int(edge["travel-time"]):
                    # we are updating the distance value for the node
                    prev_nodes[node] = curr_node
                    distances[node] = int(curr_dist) + int(edge["travel-time"])
                    print("here")
                    heapq.heappush(queue, (int(curr_dist) + int(edge["travel-time"]), node))
                else:
                    print("here instead")
                    heapq.heappush(queue, (distances[node], node))


    path = []
    curr_node = dest
    dist = 0
    while True:
        next_node = prev_nodes[curr_node]
        for e in map["edges"]:
            subpath = {}
            subpath["head"] = [next_node, curr_node]
            subpath["directions"] = []
            if e["node1"] == curr_node and e["node2"] == next_node:
                subpath["directions"] = subpath["directions"] + e["desc21"]
                dist += int(e["travel-time"])
                break
            elif e["node2"] == curr_node and e["node1"] == next_node:
                subpath["directions"] = subpath["directions"] + e["desc12"]
                dist += int(e["travel-time"])
                break
        path.append(subpath)
        curr_node = next_node
        if curr_node == source:
            break

    return list([dist, path[::-1]])
        
    
