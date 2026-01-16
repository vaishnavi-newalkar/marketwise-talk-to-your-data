class SchemaCache:
    """
    In-memory cache for database schema metadata.
    Stores schema once per session to avoid repeated DB introspection.
    """

    def __init__(self):
        self._schema = None
        self._loaded = False

    def load(self, schema: dict):
        """
        Loads schema into cache. Can be called only once per session.
        """
        if self._loaded:
            raise RuntimeError("Schema is already loaded into cache.")

        self._schema = schema
        self._loaded = True

    def get(self) -> dict:
        """
        Returns cached schema.
        """
        if not self._loaded:
            raise RuntimeError("Schema cache not initialized.")
        return self._schema

    def is_loaded(self) -> bool:
        """
        Checks whether schema is cached.
        """
        return self._loaded

    def summary(self) -> dict:
        """
        Returns lightweight schema summary (for debugging / logging).
        """
        if not self._loaded:
            return {}

        return {
            "tables": len(self._schema),
            "total_columns": sum(
                len(info.get("columns", []))
                for info in self._schema.values()
            )
        }
