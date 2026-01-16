"""
Foreign Key Graph

Represents foreign key relationships as a graph for 
table expansion during schema refinement.
"""

from collections import defaultdict, deque
from typing import Dict, Set, List


class FKGraph:
    """
    Represents foreign key relationships as a graph.
    Used to expand relevant tables based on FK relationships.
    """

    def __init__(self, schema: dict):
        self.schema = schema
        self.graph = self._build_graph()

    def _build_graph(self) -> Dict[str, Set[str]]:
        """
        Builds an undirected graph of table relationships
        based on foreign keys.
        
        Returns:
            dict: Graph where keys are table names and values are sets of related tables
        """
        graph = defaultdict(set)

        for table, info in self.schema.items():
            fks = info.get("foreign_keys", [])
            
            # Handle both list and dict formats for backward compatibility
            if isinstance(fks, list):
                # New format: list of dicts with 'from', 'to_table', 'to_column'
                for fk in fks:
                    if isinstance(fk, dict):
                        ref_table = fk.get("to_table")
                        if ref_table:
                            graph[table].add(ref_table)
                            graph[ref_table].add(table)
            elif isinstance(fks, dict):
                # Old format: dict with column -> "table.column" mapping
                for _, ref in fks.items():
                    if isinstance(ref, str) and "." in ref:
                        ref_table = ref.split(".")[0]
                        graph[table].add(ref_table)
                        graph[ref_table].add(table)

        return graph

    def expand_tables(self, seed_tables: List[str], hops: int = 1) -> Set[str]:
        """
        Expands a set of tables by following FK relationships.

        Args:
            seed_tables: Initial relevant tables
            hops: Number of FK hops to expand

        Returns:
            set: Expanded table set including original seed tables
        """
        
        # Ensure seed tables exist in schema
        valid_seeds = [t for t in seed_tables if t in self.schema]
        
        if not valid_seeds:
            # No valid seeds, return all tables up to a limit
            return set(list(self.schema.keys())[:3])

        visited = set(valid_seeds)
        queue = deque([(t, 0) for t in valid_seeds])

        while queue:
            table, depth = queue.popleft()

            if depth >= hops:
                continue

            for neighbor in self.graph.get(table, set()):
                if neighbor not in visited and neighbor in self.schema:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))

        return visited

    def get_path(self, from_table: str, to_table: str) -> List[str]:
        """
        Finds the shortest path between two tables via FK relationships.
        
        Args:
            from_table: Starting table
            to_table: Target table
        
        Returns:
            list: Path of table names, or empty list if no path exists
        """
        if from_table not in self.schema or to_table not in self.schema:
            return []
        
        if from_table == to_table:
            return [from_table]
        
        visited = {from_table}
        queue = deque([(from_table, [from_table])])
        
        while queue:
            current, path = queue.popleft()
            
            for neighbor in self.graph.get(current, set()):
                if neighbor == to_table:
                    return path + [neighbor]
                
                if neighbor not in visited and neighbor in self.schema:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return []

    def get_related_tables(self, table: str) -> Set[str]:
        """
        Gets all tables directly related to the given table via FKs.
        
        Args:
            table: Table name
        
        Returns:
            set: Related table names
        """
        return self.graph.get(table, set())
