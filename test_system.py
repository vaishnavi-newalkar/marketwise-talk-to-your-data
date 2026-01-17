"""
System Test - Validates all components are working correctly
"""

import sys
import traceback

def test_imports():
    """Test all critical imports"""
    print("=" * 60)
    print("TESTING IMPORTS")
    print("=" * 60)
    
    tests = [
        ("Planner", "from nlp.planner import create_plan"),
        ("SQL Generator", "from llm.sql_generator import generate_sql_with_reasoning"),
        ("SQL Validator", "from validation.sql_validator import validate_sql"),
        ("CTE Validator", "from validation.sql_validator import validate_cte_structure"),
        ("Prompt Templates", "from llm.prompt_templates import intent_aware_sql_prompt"),
    ]
    
    passed = 0
    failed = 0
    
    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"✅ {name}: OK")
            passed += 1
        except Exception as e:
            print(f"❌ {name}: FAILED - {e}")
            failed += 1
    
    print(f"\nImport Tests: {passed} passed, {failed} failed\n")
    return failed == 0


def test_intent_classification():
    """Test intent classification"""
    print("=" * 60)
    print("TESTING INTENT CLASSIFICATION")
    print("=" * 60)
    
    from nlp.planner import create_plan
    
    test_cases = [
        ("Show me customers who have orders", "EXISTENTIAL"),
        ("Customers who ordered only Rock music", "UNIVERSAL"),
        ("Customers who never placed an order", "ABSENCE"),
        ("Customers who bought both Rock and Jazz", "SET_INTERSECTION"),
        ("Top 5 customers by revenue", "AGGREGATION"),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_intent in test_cases:
        try:
            plan = create_plan(query, {"Customer": {"columns": ["CustomerId"]}})
            actual_intent = plan.get("intent_type", "UNKNOWN")
            
            if actual_intent == expected_intent:
                print(f"✅ '{query[:40]}...' → {actual_intent}")
                passed += 1
            else:
                print(f"❌ '{query[:40]}...' → Expected {expected_intent}, got {actual_intent}")
                failed += 1
        except Exception as e:
            print(f"❌ '{query[:40]}...' → Error: {e}")
            failed += 1
    
    print(f"\nIntent Tests: {passed} passed, {failed} failed\n")
    return failed == 0


def test_cte_validation():
    """Test CTE validation"""
    print("=" * 60)
    print("TESTING CTE VALIDATION")
    print("=" * 60)
    
    from validation.sql_validator import validate_cte_structure
    
    test_cases = [
        ("WITH cte AS (SELECT 1) SELECT * FROM cte", True),
        ("WITH cte AS (SELECT * FROM t WHERE x = 1) SELECT a, b FROM cte", True),
        ("WITH c1 AS (SELECT 1), c2 AS (SELECT 2) SELECT * FROM c1, c2", True),
        ("SELECT * FROM table", False),  # Not a CTE
        ("WITH cte AS SELECT 1", False),  # Missing parentheses
    ]
    
    passed = 0
    failed = 0
    
    for sql, expected_valid in test_cases:
        try:
            is_valid = validate_cte_structure(sql.lower())
            
            if is_valid == expected_valid:
                status = "✅" if expected_valid else "✅ (correctly rejected)"
                print(f"{status} '{sql[:50]}...'")
                passed += 1
            else:
                print(f"❌ '{sql[:50]}...' → Expected {expected_valid}, got {is_valid}")
                failed += 1
        except Exception as e:
            print(f"❌ '{sql[:50]}...' → Error: {e}")
            failed += 1
    
    print(f"\nCTE Tests: {passed} passed, {failed} failed\n")
    return failed == 0


def test_optimization_strategy():
    """Test optimization strategy determination"""
    print("=" * 60)
    print("TESTING OPTIMIZATION STRATEGY")
    print("=" * 60)
    
    from nlp.planner import create_plan
    
    test_cases = [
        ("Customers who ordered only discontinued products", "UNIVERSAL"),
        ("Customers who bought both Rock and Jazz", "SET_INTERSECTION"),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_intent in test_cases:
        try:
            plan = create_plan(query, {"Customer": {"columns": ["CustomerId"]}})
            intent_type = plan.get("intent_type")
            optimization = plan.get("optimization_strategy", "None")
            
            print(f"Query: '{query[:50]}...'")
            print(f"  Intent: {intent_type}")
            print(f"  Optimization: {optimization}")
            
            if intent_type == expected_intent and optimization:
                print(f"  ✅ PASS\n")
                passed += 1
            else:
                print(f"  ❌ FAIL\n")
                failed += 1
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
            traceback.print_exc()
            failed += 1
    
    print(f"Optimization Tests: {passed} passed, {failed} failed\n")
    return failed == 0


def test_prompt_templates():
    """Test new prompt template function"""
    print("=" * 60)
    print("TESTING PROMPT TEMPLATES")
    print("=" * 60)
    
    try:
        from llm.prompt_templates import intent_aware_sql_prompt
        
        schema = "Table: Customer\n  Columns: CustomerId, Name"
        plan = "Intent Type: UNIVERSAL\nOptimization: NOT EXISTS"
        question = "Customers who ordered only Rock music"
        
        prompt = intent_aware_sql_prompt(schema, plan, question, "UNIVERSAL")
        
        if "UNIVERSAL INTENT DETECTED" in prompt and "NOT EXISTS" in prompt:
            print("✅ Intent-aware prompt generated correctly")
            print(f"  Contains UNIVERSAL warning: Yes")
            print(f"  Contains NOT EXISTS instruction: Yes")
            return True
        else:
            print("❌ Prompt missing expected content")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("SYSTEM VALIDATION TEST")
    print("=" * 60 + "\n")
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Intent Classification", test_intent_classification()))
    results.append(("CTE Validation", test_cte_validation()))
    results.append(("Optimization Strategy", test_optimization_strategy()))
    results.append(("Prompt Templates", test_prompt_templates()))
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:12} {name}")
    
    print(f"\nOverall: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED - System is ready!")
        return 0
    else:
        print(f"\n❌ {total - passed} test suite(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
