# Ambiguity Detection Fix - Summary

## Issue
The system was **not asking for clarification** when users asked vague questions like "Show me recent orders" - it was directly executing the query instead of asking what "recent" means (last 7 days? 30 days? most recent 10 orders?).

## Root Cause Investigation

### ✅ Ambiguity Detector (nlp/ambiguity_detector.py)
**Status: WORKING CORRECTLY**

The ambiguity detector was already properly configured and functioning:
- Has "recent", "latest", "old", "new" defined with high priority
- Generates proper clarification questions with multiple options
- Correctly extracts the user query from enriched context
- Test results confirmed it detects all temporal terms

**Test Results:**
```
✅ "Show me recent orders" → AMBIGUOUS
✅ "Get the latest customers" → AMBIGUOUS  
✅ "Find new products" → AMBIGUOUS
✅ "Show top 5 customers" → NOT AMBIGUOUS (correctly ignored - specific number)
```

### 🔧 API (api.py)
**Status: WORKING CORRECTLY**

Line 226 properly calls:
```python
ambiguous, data = detect_ambiguity(enriched_query)
```

And returns the clarification on lines 227-232:
```python
if ambiguous:
    return {
        "clarification": data["question"], 
        "term": data.get("term"), 
        "options": data.get("options", []), 
        "reasoning_steps": reasoning_steps
    }
```

### ❌ UI (ui.py)
**Status: FIXED**

**Problem 1: Incomplete Data Storage**
- Line 559 was saving clarification with empty dict: `add_message_to_chat(..., {})`
- This lost the term, options, and reasoning_steps from the API response

**Fix:**
```python
clarification_data = {
    "clarification": res.get("clarification"),
    "term": res.get("term"),
    "options": res.get("options", []),
    "reasoning_steps": res.get("reasoning_steps", [])
}
add_message_to_chat(..., clarification_data)
```

**Problem 2: No Clarification Rendering**
- The `render_message` function had no special handling for clarification messages
- Clarifications were displayed as regular messages without highlighting

**Fix:**
Added clarification-specific rendering in `render_message` (lines 322-335):
```python
# Handle Clarification Display
if extra_data.get("clarification"):
    if extra_data.get("reasoning_steps"):
        render_reasoning_tree(extra_data["reasoning_steps"])
        st.markdown("---")
    
    st.warning(f"⚠️ **Clarification Needed**")
    st.markdown(content)
    
    if extra_data.get("options"):
        st.markdown("**Suggested options:**")
        for opt in extra_data["options"]:
            st.markdown(f"• {opt}")
    return  # Don't proceed with normal rendering
```

## Testing

### 1. Unit Test (Standalone)
```bash
cd d:\marketwisePS2
python test_ambiguity.py
cat test_output.txt
```

Expected output shows "recent", "latest", "new" detected as ambiguous with proper clarification questions.

### 2. Full System Test

**Setup:**
1. Ensure API is running: `uvicorn api:app --reload --port 8000`
2. Start UI: `streamlit run ui.py`
3. Upload a database with an orders table

**Test Cases:**

| Query | Expected Behavior |
|-------|------------------|
| "Show me recent orders" | ⚠️ System asks: "What does 'recent' mean to you?<br>• Last 7 days?<br>• Last 30 days?<br>• Most recent 10 orders?" |
| "Get latest customers" | ⚠️ System asks: "When you say 'latest', do you mean:<br>• Most recent 10 records?<br>• Last 7 days?<br>• Last 30 days?" |
| "Show top 5 orders" | ✅ Executes directly (not ambiguous - specific number) |
| "Find best products" | ⚠️ System asks what "best" means (highest revenue, highest quantity, etc.) |

### 3. User Flow Test

1. **Ask ambiguous question**: "Show me recent orders"
2. **See clarification**: Warning box with options
3. **Provide clarification**: "Orders from the last 30 days"
4. **Get result**: SQL query executed for last 30 days

## Files Modified

1. **ui.py** (2 changes)
   - Lines 558-568: Fixed clarification data storage
   - Lines 322-335: Added clarification rendering

## Expected UI Behavior

### Before Fix:
- User: "Show me recent orders"
- System: *Directly generates SQL for orders* (no clarification)
- Result: Arbitrary interpretation of "recent"

### After Fix:
- User: "Show me recent orders"
- System: *Shows warning box*
  ```
  ⚠️ Clarification Needed
  
  What does 'recent' mean to you?
  • Orders from the last 7 days?
  • Orders from the last 30 days?
  • The most recent 10 orders?
  
  Suggested options:
  • last 7 days
  • last 30 days
  • most recent 10 orders
  ```
- User: "last 30 days"
- System: *Merges intent and generates SQL for orders from last 30 days*

## Additional Improvements Made

### Ambiguity Patterns Enhanced
The detector now covers:
- **Time**: recent, latest, old, new (HIGH PRIORITY)
- **Ranking**: top, best, highest, lowest, most, least
- **Quantity**: few, many, some
- **Comparison**: better, worse, similar
- **Status**: active, popular

### Context Awareness
- Skips ambiguity for clear contexts: "top 5", "last 7", "first 10"
- Considers schema columns to avoid false positives
- Extracts current question from conversation history

## Next Steps

1. **Test thoroughly** with various ambiguous queries
2. **Monitor logs** to ensure clarifications are being triggered
3. **Gather user feedback** on clarification quality
4. **Consider adding** interactive buttons for quick clarification selection (future enhancement)

## Debug Commands

Check if ambiguity detector is working:
```bash
python test_ambiguity.py
```

Check API logs for ambiguity detection:
```bash
# Look for log entries showing "Ambiguity: 'recent'" in uvicorn output
```

Verify UI is saving clarification data:
```bash
# Check chat_history.json for clarification entries with term/options
```
