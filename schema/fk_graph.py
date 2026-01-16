from collections import defaultdict, deque


class FKGraph:
    """
    Represents foreign key relationships as a graph.
    """

    def __init__(self, schema: dict):
        self.schema = schema
        self.graph = self._build_graph()

    def _build_graph(self):
        """
        Builds an undirected graph of table relationships
        based on foreign keys.
        """
        graph = defaultdict(set)

        for table, info in self.schema.items():
            fks = info.get("foreign_keys", {})

            for _, ref in fks.items():
                # ref format: "other_table.other_column"
                ref_table = ref.split(".")[0]

                graph[table].add(ref_table)
                graph[ref_table].add(table)

        return graph

    def expand_tables(self, seed_tables, hops=1):
        """
        Expands a set of tables by following FK relationships.

        Args:
            seed_tables (list[str]): Initial relevant tables
            hops (int): Number of FK hops to expand

        Returns:
            set[str]: Expanded table set
        """

        visited = set(seed_tables)
        queue = deque([(t, 0) for t in seed_tables])

        while queue:
            table, depth = queue.popleft()

            if depth >= hops:
                continue

            for neighbor in self.graph.get(table, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))

        return visited
