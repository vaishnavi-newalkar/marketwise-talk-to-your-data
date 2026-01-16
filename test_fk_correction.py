"""
Test the enhanced foreign key detection in error correction
"""

from llm.self_correction import QueryCorrector

# Mock schema matching the Chinook database structure
schema = {
    "Track": {
        "columns": ["TrackId", "Name", "AlbumId", "MediaTypeId", "GenreId", "Composer", "Milliseconds", "Bytes", "UnitPrice"],
        "column_types": {},
        "primary_key": ["TrackId"],
        "foreign_keys": [
            {"from": "GenreId", "to_table": "Genre", "to_column": "GenreId"}
        ]
    },
    "Genre": {
        "columns": ["GenreId", "Name"],
        "column_types": {},
        "primary_key": ["GenreId"],
        "foreign_keys": []
    },
    "InvoiceLine": {
        "columns": ["InvoiceLineId", "InvoiceId", "TrackId", "UnitPrice", "Quantity"],
        "column_types": {},
        "primary_key": ["InvoiceLineId"],
        "foreign_keys": []
    }
}

corrector = QueryCorrector(schema)

# Test the error that occurred: "no such column: t.Genre"
test_sql = "SELECT DISTINCT t.Genre FROM Track t LEFT JOIN InvoiceLine il ON t.TrackId = il.TrackId WHERE il.InvoiceLineId IS NULL"
error_message = "SQL execution failed: no such column: t.Genre"

print("=" * 70)
print("TESTING FOREIGN KEY ERROR DETECTION")
print("=" * 70)

print(f"\nFailed SQL:\n{test_sql}\n")
print(f"Error: {error_message}\n")

# Analyze the error
fix_info = corrector.analyze_error(error_message, test_sql)

print("ANALYSIS RESULT:")
print(f"  Error Type: {fix_info['error_type']}")
print(f"  Suggestion: {fix_info['suggestion']}")
print(f"  Can Retry: {fix_info['can_retry']}")
print(f"  Fix Hint: {fix_info['fix_hint']}")
print(f"  Requires Join: {fix_info.get('requires_join', False)}")
print(f"  Join Table: {fix_info.get('join_table', 'N/A')}")

print("\n" + "=" * 70)

# Expected behavior:
# - Should detect that "Genre" is a table name
# - Should suggest using GenreId FK and joining with Genre table
# - Should NOT suggest replacing with "Title" or other random columns
