"""
Test schema-aware value inference
"""

from llm.sql_generator import infer_semantic_flag_values

# Test schema with different types
test_schema = {
    "products": {
        "columns": ["product_id", "name", "discontinued", "active", "status"],
        "column_types": {
            "product_id": "INTEGER",
            "name": "TEXT",
            "discontinued": "INTEGER",  # Should infer 0/1
            "active": "BOOLEAN",  # Should infer TRUE/FALSE
            "status": "VARCHAR(20)"  # Should infer text values
        }
    },
    "orders": {
        "columns": ["order_id", "shipped", "completed"],
        "column_types": {
            "order_id": "INTEGER",
            "shipped": "TINYINT",  # Should infer 0/1
            "completed": "INTEGER"  # Should infer 0/1
        }
    },
    "customers": {
        "columns": ["customer_id", "name", "email"],
        "column_types": {
            "customer_id": "INTEGER",
            "name": "TEXT",
            "email": "TEXT"
        }
    }
}

print("="*70)
print("TESTING SCHEMA-AWARE VALUE INFERENCE")
print("="*70)

result = infer_semantic_flag_values(test_schema, "test question")

if result:
    print("\n✅ Value inference detected semantic flags:\n")
    print(result)
else:
    print("\n❌ No semantic flags detected")

print("\n" + "="*70)
print("VERIFICATION")
print("="*70)

# Verify expected flags were found
expected_flags = [
    "discontinued",
    "active",
    "status",
    "shipped",
    "completed"
]

found = []
for flag in expected_flags:
    if flag.lower() in result.lower():
        found.append(flag)
        print(f"  ✅ {flag} - Detected")
    else:
        print(f"  ❌ {flag} - NOT detected")

print(f"\n✅ Total: {len(found)}/{len(expected_flags)} flags detected correctly")

# Verify inference guidance is provided
if "INTEGER flag" in result:
    print("✅ INTEGER inference guidance provided")
else:
    print("❌ No INTEGER guidance")

if "BOOLEAN flag" in result:
    print("✅ BOOLEAN inference guidance provided")
else:
    print("❌ No BOOLEAN guidance")

if "TEXT flag" in result:
    print("✅ TEXT inference guidance provided")
else:
    print("❌ No TEXT guidance")

print("\n" + "="*70)
