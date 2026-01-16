"""
Quick test for ambiguity detection on temporal terms like "recent"
"""

from nlp.ambiguity_detector import detect_ambiguity

# Test cases
test_queries = [
    "Show me recent orders",
    "Get the latest customers",
    "Find new products",
    "Show top 5 customers",  # Should NOT trigger (clear context)
    "Conversation context:\nPrevious: What products do you have?\n\nCurrent question:\nShow me recent orders"  # Enriched query
]

output = []
output.append("=" * 60)
output.append("AMBIGUITY DETECTION TEST")
output.append("=" * 60)

for query in test_queries:
    output.append(f"\nQuery: {query[:80]}...")
    is_ambiguous, data = detect_ambiguity(query)
    
    if is_ambiguous:
        output.append(f"  STATUS: AMBIGUOUS")
        output.append(f"  Term: '{data['term']}'")
        output.append(f"  Category: {data['category']}")
        output.append(f"  Question:")
        output.append(f"  {data['question']}")
    else:
        output.append("  STATUS: NOT AMBIGUOUS")

output.append("\n" + "=" * 60)

# Write to file
with open("test_output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print("Test complete! Results written to test_output.txt")
