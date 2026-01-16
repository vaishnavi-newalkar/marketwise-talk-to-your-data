# Foreign Key Error Correction - Fix Summary

## Issue
When asking "Are there any genres with no sales?", the system generated SQL like:
```sql
SELECT DISTINCT t.Genre FROM Track t 
LEFT JOIN InvoiceLine il ON t.TrackId = il.TrackId 
WHERE il.InvoiceLineId IS NULL
```

This failed with: **"no such column: t.Genre"**

The retry mechanism then tried:
1. Replacing `t` with `Title` → **Failed: "no such column: Title.Genre"**
2. Retrying original query → **Failed again**

## Root Cause

The **Track table doesn't have a `Genre` column**. Instead, it has:
- `GenreId` (INTEGER) - foreign key
- Links to → **Genre table** which has `GenreId` and `Name`

The LLM incorrectly generated SQL trying to access `t.Genre` directly instead of **JOIN**ing with the Genre table.

The self-correction system was:
1. Not recognizing that "Genre" is a table name (FK relationship error)
2. Suggesting random similar columns like "Title"
3. Not understanding it needs a JOIN, not a simple column replacement

## Solution

### 1. Enhanced Error Pattern Matching
**File: `llm/self_correction.py` line 21**

**Before:**
```python
r"no such column: (\w+)": "column_not_found",
```

**After:**
```python
r"no such column: ([\w.]+)": "column_not_found",  # Matches table.column or column
```

This now captures qualified column names like `t.Genre` instead of just `t`.

### 2. Foreign Key Relationship Detection
**File: `llm/self_correction.py` lines 76-117**

Added intelligence to detect when a "missing column" is actually a table name:

```python
# Check if the column name looks like a table name (potential FK relationship error)
# E.g., "t.Genre" where Track has GenreId, not Genre
...
# Check if column name matches a table name (case-insensitive)
for table_name in self.all_tables:
    if column_name_only.lower() == table_name.lower():
        potential_table = table_name
        # Look for a foreign key column like "{table}Id"
        fk_column = f"{table_name}Id"
        if fk_column in self.all_columns:
            fk_hint = f"Column '{column}' doesn't exist. Did you mean to JOIN with the {table_name} table? The relationship is through '{fk_column}'."
```

Now returns:
```python
{
    "requires_join": True,
    "join_table": "Genre",
    "fix_hint": "Need to JOIN with Genre table using GenreId"
}
```

### 3. Enhanced Retry Prompts
**File: `llm/self_correction.py` lines 242-296**

The retry prompt now:
- Shows foreign key relationships in the schema
- Explicitly tells the LLM when a JOIN is required
- Adds rule: "Uses proper JOINs when accessing related tables"

**Example enhanced prompt:**
```
HINT:
Need to JOIN with Genre table using GenreId

IMPORTANT: You need to JOIN with the Genre table to access its columns.

AVAILABLE SCHEMA:
Table Track: TrackId, Name, AlbumId, MediaTypeId, GenreId, Composer...
  └─ FK: GenreId → Genre.GenreId
Table Genre: GenreId, Name
  └─ ...
```

## Correct SQL Query

The query should be:
```sql
SELECT DISTINCT g.Name 
FROM Track t 
LEFT JOIN InvoiceLine il ON t.TrackId = il.TrackId 
LEFT JOIN Genre g ON t.GenreId = g.GenreId
WHERE il.InvoiceLineId IS NULL
```

Or even simpler:
```sql
SELECT g.Name
FROM Genre g
WHERE NOT EXISTS (
    SELECT 1 
    FROM Track t 
    JOIN InvoiceLine il ON t.TrackId = il.TrackId 
    WHERE t.GenreId = g.GenreId
)
```

## Testing

The fix has been tested with the error correction system:

**Input:** `"no such column: t.Genre"`

**Output:**
```
Requires Join: True
Join Table: Genre
Fix Hint: Need to JOIN with Genre table using GenreId
```

## Next Steps

1. **Clear your chat history** or start a **new session** in the UI (the old error is cached)
2. **Ask again**: "Are there any genres with no sales?"
3. The system should now:
   - Generate better SQL with proper JOIN
   - If it still fails, the retry will explicitly tell the LLM to use JOIN
   - Successfully return genres with no sales

## Files Modified

1. **llm/self_correction.py**
   - Line 21: Fixed error pattern regex
   - Lines 76-117: Added FK relationship detection
   - Lines 242-296: Enhanced retry prompt with FK information

## Expected Behavior

### Before Fix
```
Error → Try "Title" → Error → Give up
```

### After Fix
```
Error → Detect FK relationship → Tell LLM to JOIN Genre table → Success
```
