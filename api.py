"""
NL → SQL API Server

FastAPI backend with:
- Session management
- Ambiguity detection & clarification
- Meta-query handling (schema introspection)
- Self-correction (retry on failure)
- SQL generation with detailed reasoning
- Comprehensive error handling
"""

import os
import uuid
import traceback
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Any

# ----------------------------
# Core system imports
# ----------------------------
from db.validator import validate_sqlite_db
from db.schema_extractor import extract_schema
from db.schema_cache import SchemaCache
from session.session_manager import Session

from nlp.context_builder import build_context
from nlp.ambiguity_detector import detect_ambiguity
from nlp.intent_merger import merge_intent
from nlp.meta_handler import detect_meta_query, handle_meta_query
from schema.refiner import refine_schema
from nlp.planner import create_plan

from llm.client import GroqClient
from llm.sql_generator import generate_sql_with_reasoning, SQLGenerationError
from llm.self_correction import QueryCorrector, generate_retry_prompt

from validation.sql_validator import validate_sql, SQLValidationError
from db.executor import execute_sql, SQLExecutionError
from response.interpreter import interpret


# ----------------------------
# App & global state
# ----------------------------
app = FastAPI(
    title="NL → SQL Assistant",
    description="Natural Language to SQL query system with reasoning and self-correction",
    version="2.0.0"
)

# Enable CORS for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploaded_dbs")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory session store
SESSIONS: dict[str, Session] = {}

# Single shared LLM client
llm = GroqClient()

# Maximum retry attempts for self-correction
MAX_RETRIES = 2


# ----------------------------
# Request/Response models
# ----------------------------
class QuestionRequest(BaseModel):
    session_id: str
    question: str
    is_clarification: bool = False


class UploadResponse(BaseModel):
    session_id: str
    tables: List[str]
    table_count: int
    message: str


# ============================================================
# 1️⃣ DB UPLOAD (ONCE PER SESSION)
# ============================================================
@app.post("/upload-db", response_model=UploadResponse)
async def upload_db(file: UploadFile = File(...)):
    """
    Upload a SQLite database and create a new session.
    """

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    
    if not file.filename.lower().endswith((".db", ".sqlite", ".sqlite3")):
        raise HTTPException(
            status_code=400,
            detail="Only SQLite (.db, .sqlite, .sqlite3) files are allowed."
        )

    session_id = str(uuid.uuid4())
    db_path = os.path.join(UPLOAD_DIR, f"{session_id}.sqlite")

    try:
        content = await file.read()
        with open(db_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    try:
        validate_sqlite_db(db_path)
    except Exception as e:
        if os.path.exists(db_path):
            os.remove(db_path)
        raise HTTPException(status_code=400, detail=f"Invalid database: {str(e)}")

    try:
        schema = extract_schema(db_path)
    except Exception as e:
        if os.path.exists(db_path):
            os.remove(db_path)
        raise HTTPException(status_code=400, detail=f"Schema extraction failed: {str(e)}")
    
    cache = SchemaCache()
    cache.load(schema)

    session = Session(db_path=db_path, schema=cache.get())
    SESSIONS[session_id] = session

    return UploadResponse(
        session_id=session_id,
        tables=list(schema.keys()),
        table_count=len(schema),
        message="Database uploaded and session created successfully."
    )


# ============================================================
# 2️⃣ ASK QUESTIONS (CHAT LOOP)
# ============================================================
@app.post("/ask")
def ask_question(req: QuestionRequest):
    """
    Process a natural language question.
    
    Pipeline:
    1. Check for meta-queries (schema introspection)
    2. Check for clarification state
    3. Detect ambiguity
    4. Refine schema
    5. Generate plan
    6. Generate SQL with reasoning
    7. Validate SQL
    8. Execute (with retry on failure)
    9. Interpret results
    """

    session = SESSIONS.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid session_id")

    user_input = req.question.strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        # Build reasoning trace
        reasoning_steps = []
        
        # ------------------------------------------------
        # STEP 0: Check for Meta-Queries
        # ------------------------------------------------
        is_meta, meta_type, target_table = detect_meta_query(user_input)
        
        if is_meta:
            reasoning_steps.append(f"🔍 Detected meta-query: {meta_type}")
            
            result = handle_meta_query(
                meta_type=meta_type,
                schema=session.full_schema,
                target_table=target_table
            )
            
            session.add_user_message(user_input)
            session.add_system_message(result["answer"])
            
            return {
                "answer": result["answer"],
                "reasoning": result.get("reasoning", ""),
                "sql": result.get("sql", "-- Meta-query"),
                "columns": result.get("columns", []),
                "rows": result.get("rows", []),
                "row_count": result.get("row_count", 0),
                "is_meta_query": True
            }
        
        # ------------------------------------------------
        # STEP 1: Handle Clarification Response
        # ------------------------------------------------
        resolving_clarification = False

        if session.clarification_state:
            reasoning_steps.append("📝 Processing clarification response")
            
            user_query = merge_intent(
                original_query=session.clarification_state["original_query"],
                clarification_response=user_input,
                clarification_state=session.clarification_state
            )
            session.clear_clarification()
            resolving_clarification = True
            
            reasoning_steps.append(f"✅ Merged intent: '{user_query[:50]}...'")
        else:
            user_query = user_input

        session.add_user_message(user_query)

        # ------------------------------------------------
        # STEP 2: Build Conversational Context
        # ------------------------------------------------
        context = build_context(session.get_chat_history())
        enriched_query = f"""
Conversation context:
{context}

Current question:
{user_query}
        """.strip()

        # ------------------------------------------------
        # STEP 3: Ambiguity Detection
        # ------------------------------------------------
        if not resolving_clarification:
            ambiguous, data = detect_ambiguity(enriched_query)
            if ambiguous:
                reasoning_steps.append(f"⚠️ Detected ambiguous term: '{data['term']}'")
                
                data["original_query"] = enriched_query
                session.clarification_state = data
                session.add_system_message(data["question"])
                
                return {
                    "clarification": data["question"],
                    "term": data.get("term"),
                    "options": data.get("options", []),
                    "reasoning": "\n".join(reasoning_steps)
                }

        # ------------------------------------------------
        # STEP 4: Schema Exploration & Refinement
        # ------------------------------------------------
        reasoning_steps.append("📊 Analyzing database schema...")
        
        refined_schema = refine_schema(session.full_schema, enriched_query)
        
        tables_used = list(refined_schema.keys())
        reasoning_steps.append(f"📋 Selected relevant tables: {', '.join(tables_used)}")

        # ------------------------------------------------
        # STEP 5: Query Planning
        # ------------------------------------------------
        reasoning_steps.append("🎯 Creating query plan...")
        
        plan = create_plan(user_query, refined_schema)
        
        if plan.get("aggregation"):
            reasoning_steps.append(f"📈 Detected aggregation: {plan['aggregation']}")
        if plan.get("needs_join"):
            reasoning_steps.append("🔗 JOIN operation required")
        if plan.get("filters_detected"):
            reasoning_steps.append(f"🔍 Filters detected: {', '.join(plan.get('filter_hints', [])[:2])}")

        # ------------------------------------------------
        # STEP 6: SQL Generation with Reasoning
        # ------------------------------------------------
        reasoning_steps.append("⚙️ Generating SQL query...")
        
        try:
            generation_result = generate_sql_with_reasoning(
                llm_client=llm,
                plan=plan,
                schema=refined_schema,
                question=enriched_query
            )
            
            sql = generation_result["sql"]
            llm_reasoning = generation_result["reasoning"]
            
            reasoning_steps.append("✅ SQL generated successfully")
            
        except SQLGenerationError as e:
            return {
                "answer": "I couldn't generate a SQL query for your question.",
                "error": str(e),
                "reasoning": "\n".join(reasoning_steps) + f"\n❌ Generation failed: {str(e)}"
            }

        # ------------------------------------------------
        # STEP 7: SQL Validation
        # ------------------------------------------------
        reasoning_steps.append("🔒 Validating SQL for safety...")
        
        try:
            validate_sql(sql)
            reasoning_steps.append("✅ SQL passed security validation")
        except SQLValidationError as e:
            return {
                "answer": "The generated query failed safety validation.",
                "error": str(e),
                "reasoning": "\n".join(reasoning_steps) + f"\n❌ Validation failed: {str(e)}",
                "sql": sql
            }

        # ------------------------------------------------
        # STEP 8: Query Execution (with Self-Correction)
        # ------------------------------------------------
        reasoning_steps.append("🚀 Executing query...")
        
        corrector = QueryCorrector(session.full_schema)
        attempts = []
        exec_result = None
        current_sql = sql
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                exec_result = execute_sql(session.db_path, current_sql)
                reasoning_steps.append(f"✅ Query executed successfully (attempt {attempt + 1})")
                break
                
            except SQLExecutionError as e:
                error_msg = str(e)
                attempts.append({"sql": current_sql, "error": error_msg})
                
                if attempt < MAX_RETRIES:
                    reasoning_steps.append(f"⚠️ Execution failed (attempt {attempt + 1}): {error_msg}")
                    reasoning_steps.append("🔄 Attempting self-correction...")
                    
                    # Analyze error and try to fix
                    fix_info = corrector.analyze_error(error_msg, current_sql)
                    
                    if fix_info.get("can_retry"):
                        # Try to apply direct fix
                        fixed_sql = corrector.apply_fix(current_sql, fix_info)
                        
                        if fixed_sql:
                            current_sql = fixed_sql
                            reasoning_steps.append(f"🔧 Applied fix: {fix_info.get('fix_hint', 'Auto-corrected')}")
                        else:
                            # Regenerate with error context
                            retry_prompt = generate_retry_prompt(
                                user_query, current_sql, error_msg, fix_info, refined_schema
                            )
                            
                            try:
                                retry_result = generate_sql_with_reasoning(
                                    llm_client=llm,
                                    plan=plan,
                                    schema=refined_schema,
                                    question=retry_prompt
                                )
                                current_sql = retry_result["sql"]
                                reasoning_steps.append("🔧 Regenerated SQL with corrections")
                            except:
                                pass
                    else:
                        # Cannot retry
                        break
                else:
                    reasoning_steps.append(f"❌ Execution failed after {MAX_RETRIES + 1} attempts")
                    
                    return {
                        "answer": "The query couldn't be executed successfully.",
                        "error": error_msg,
                        "reasoning": "\n".join(reasoning_steps),
                        "sql": sql,
                        "attempts": len(attempts)
                    }

        if not exec_result:
            return {
                "answer": "Query execution failed after multiple attempts.",
                "error": "Unknown execution error",
                "reasoning": "\n".join(reasoning_steps),
                "sql": sql
            }

        # ------------------------------------------------
        # STEP 9: Result Interpretation
        # ------------------------------------------------
        reasoning_steps.append("📊 Interpreting results...")
        
        interpreted = interpret(exec_result, question=user_query)
        
        # Handle empty results gracefully
        if exec_result.get("row_count", 0) == 0:
            reasoning_steps.append("ℹ️ Query returned no results")
            
            # Generate a meaningful empty result message
            empty_context = _generate_empty_result_message(user_query, sql)
            interpreted["answer"] = empty_context
        
        session.add_system_message(interpreted["answer"])

        # ------------------------------------------------
        # FINAL: Compile Full Response
        # ------------------------------------------------
        full_reasoning = "\n".join(reasoning_steps)
        if llm_reasoning:
            full_reasoning += f"\n\n**LLM Reasoning:**\n{llm_reasoning}"

        return {
            "answer": interpreted["answer"],
            "reasoning": full_reasoning,
            "sql": current_sql,
            "columns": interpreted.get("columns", []),
            "rows": interpreted.get("preview_rows", []),
            "row_count": interpreted.get("total_count", 0),
            "truncated": exec_result.get("truncated", False),
            "retries": len(attempts)
        }

    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}"
        print(f"[ERROR] {traceback.format_exc()}")
        
        return {
            "answer": "An unexpected error occurred while processing your request.",
            "error": error_detail
        }


def _generate_empty_result_message(question: str, sql: str) -> str:
    """
    Generates a meaningful message for empty query results.
    """
    q_lower = question.lower()
    
    # Common patterns for empty result interpretation
    if "never" in q_lower or "without" in q_lower or "no " in q_lower:
        return "The query found **no matching records**. This means the condition you specified doesn't match any data in the database."
    
    if "who" in q_lower or "which" in q_lower:
        return "**No records found** matching your criteria. This could mean all records satisfy the opposite condition."
    
    if "exist" in q_lower or "are there" in q_lower:
        return "**No matching records exist** in the database for your query."
    
    return "The query executed successfully but returned **no results**. The data you're looking for may not exist in the database."


# ============================================================
# 3️⃣ SESSION INFO
# ============================================================
@app.get("/session/{session_id}")
def get_session_info(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "tables": list(session.full_schema.keys()),
        "chat_history_length": len(session.get_chat_history()),
        "has_pending_clarification": session.clarification_state is not None
    }


# ============================================================
# 4️⃣ CLEAR SESSION
# ============================================================
@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    session = SESSIONS.pop(session_id, None)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if os.path.exists(session.db_path):
        try:
            os.remove(session.db_path)
        except:
            pass
    
    return {"message": "Session deleted successfully"}


# ============================================================
# 5️⃣ HEALTH CHECK
# ============================================================
@app.get("/health")
def health():
    return {
        "status": "ok",
        "active_sessions": len(SESSIONS),
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# 6️⃣ SCHEMA PREVIEW
# ============================================================
@app.get("/schema/{session_id}")
def get_schema(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"schema": session.full_schema}
