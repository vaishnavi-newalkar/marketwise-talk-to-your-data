"""
NL → SQL API Server

FastAPI backend with:
- Session management
- Ambiguity detection & clarification
- Meta-query handling (schema introspection)
- Intent classification (SQL vs General)
- Self-correction (retry on failure)
- SQL generation with detailed reasoning
- LLM-based final answer generation
- Smart suggestions (Initial & Follow-up)
- Comprehensive error handling
"""

import os
import uuid
import traceback
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
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
from nlp.classifier import classify_intent
from schema.refiner import refine_schema
from nlp.planner import create_plan
from nlp.suggestion_generator import generate_initial_questions, generate_related_questions

from llm.client import GroqClient
from llm.sql_generator import generate_sql_with_reasoning, SQLGenerationError
from llm.self_correction import QueryCorrector, generate_retry_prompt

from validation.sql_validator import validate_sql, SQLValidationError
from db.executor import execute_sql, SQLExecutionError
from response.interpreter import interpret
from response.answer_generator import generate_final_answer
from response.general_chat import handle_general_chat


# ----------------------------
# App & global state
# ----------------------------
app = FastAPI(
    title="NL → SQL Assistant",
    description="Natural Language to SQL query system with reasoning and self-correction",
    version="2.0.0"
)

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

SESSIONS: dict[str, Session] = {}
llm = GroqClient()
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
    initial_questions: List[str] = []


# ============================================================
# 1️⃣ DB UPLOAD (ONCE PER SESSION)
# ============================================================
@app.post("/upload-db", response_model=UploadResponse)
async def upload_db(file: UploadFile = File(...)):
    """
    Upload a SQLite database, create session, and generate initial questions.
    """

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    
    if not file.filename.lower().endswith((".db", ".sqlite", ".sqlite3")):
        raise HTTPException(status_code=400, detail="Only SQLite files allowed.")

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
        schema = extract_schema(db_path)
    except Exception as e:
        if os.path.exists(db_path):
            os.remove(db_path)
        raise HTTPException(status_code=400, detail=f"Invalid database: {str(e)}")
    
    cache = SchemaCache()
    cache.load(schema)

    session = Session(db_path=db_path, schema=cache.get())
    SESSIONS[session_id] = session

    # Generate initial questions based on schema
    try:
        initial_questions = generate_initial_questions(llm, schema)
    except:
        initial_questions = []

    return UploadResponse(
        session_id=session_id,
        tables=list(schema.keys()),
        table_count=len(schema),
        message="Database uploaded successfully.",
        initial_questions=initial_questions
    )


# ============================================================
# 2️⃣ ASK QUESTIONS (CHAT LOOP)
# ============================================================
@app.post("/ask")
def ask_question(req: QuestionRequest):
    """
    Process a natural language question.
    """

    session = SESSIONS.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid session_id")

    user_input = req.question.strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        reasoning_steps = []
        
        # ------------------------------------------------
        # Generate Suggestions (Parallel if async, but here sequential)
        # ------------------------------------------------
        # We'll generate suggestions at the END, but preparing context here.
        
        # ... [Meta-Query Check] ...
        is_meta, meta_type, target_table = detect_meta_query(user_input)
        if is_meta:
            reasoning_steps.append({
                "icon": "🔍",
                "text": f"Detected meta-query: {meta_type}",
                "status": "complete"
            })
            result = handle_meta_query(meta_type, session.full_schema, target_table)
            session.add_user_message(user_input)
            session.add_system_message(result["answer"])
            return {
                **result, 
                "reasoning_steps": reasoning_steps, 
                "is_meta_query": True,
                "suggestions": [] # No suggestions for meta queries typically
            }
        
        # ... [Intent Classification] ...
        if not session.clarification_state:
            intent, _ = classify_intent(llm, user_input)
            if intent == "GENERAL_CHAT":
                reasoning_steps.append({
                    "icon": "💬",
                    "text": "General conversation detected",
                    "status": "complete"
                })
                result = handle_general_chat(llm, user_input, session.full_schema)
                session.add_user_message(user_input)
                session.add_system_message(result["answer"])
                return {
                    **result, 
                    "reasoning_steps": reasoning_steps,
                    "suggestions": [] # Could generate chat suggestions
                }

        # ... [Clarification] ...
        resolving_clarification = False
        if session.clarification_state:
            reasoning_steps.append({"icon": "📝", "text": "Processing clarification...", "status": "complete"})
            user_query = merge_intent(session.clarification_state["original_query"], user_input, session.clarification_state)
            session.clear_clarification()
            resolving_clarification = True
        else:
            user_query = user_input

        session.add_user_message(user_query)
        context = build_context(session.get_chat_history())
        enriched_query = f"Conversation context:\n{context}\n\nCurrent question:\n{user_query}"

        # ... [Ambiguity] ...
        if not resolving_clarification:
            ambiguous, data = detect_ambiguity(enriched_query)
            if ambiguous:
                reasoning_steps.append({"icon": "⚠️", "text": f"Ambiguity: '{data['term']}'", "status": "complete"})
                data["original_query"] = enriched_query
                session.clarification_state = data
                session.add_system_message(data["question"])
                return {"clarification": data["question"], "term": data.get("term"), "options": data.get("options", []), "reasoning_steps": reasoning_steps}

        # ... [Schema Refinement] ...
        reasoning_steps.append({"icon": "📊", "text": "Analyzing schema context...", "status": "complete"})
        refined_schema = refine_schema(session.full_schema, enriched_query)
        
        # ... [Planning] ...
        plan = create_plan(user_query, refined_schema)
        # Add varied reasoning steps for UI
        if plan.get("needs_join"): reasoning_steps.append({"icon": "🔗", "text": "JOIN required", "status": "complete"})
        if plan.get("aggregation"): reasoning_steps.append({"icon": "📈", "text": f"Aggregation: {plan['aggregation']}", "status": "complete"})
        reasoning_steps.append({"icon": "🎯", "text": f"Strategy: {plan['complexity'].upper()} query", "status": "complete"})

        # ... [Generation] ...
        reasoning_steps.append({"icon": "⚙️", "text": "Generating SQL...", "status": "complete"})
        try:
            gen_res = generate_sql_with_reasoning(llm, plan, refined_schema, enriched_query)
        except SQLGenerationError as e:
            return {"answer": "Generation failed.", "error": str(e), "reasoning_steps": reasoning_steps}

        sql = gen_res["sql"]
        llm_reasoning = gen_res["reasoning"]

        # ... [Validation] ...
        reasoning_steps.append({"icon": "🔒", "text": "Validating safety...", "status": "complete"})
        try:
            validate_sql(sql)
        except SQLValidationError as e:
            return {"answer": "Validation failed.", "error": str(e), "reasoning_steps": reasoning_steps, "sql": sql}

        # ... [Execution] ...
        reasoning_steps.append({"icon": "🚀", "text": "Executing query...", "status": "complete"})
        corrector = QueryCorrector(session.full_schema)
        attempts = []
        exec_result = None
        current_sql = sql
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                exec_result = execute_sql(session.db_path, current_sql)
                break
            except SQLExecutionError as e:
                error_msg = str(e)
                attempts.append({"sql": current_sql, "error": error_msg})
                
                if attempt < MAX_RETRIES:
                    fix = corrector.analyze_error(error_msg, current_sql)
                    
                    reasoning_steps.append({
                        "icon": "🔄", 
                        "text": f"Retrying ({attempt+1}/{MAX_RETRIES}): {fix.get('suggestion', 'Error detected')[:50]}", 
                        "status": "retry"
                    })
                    
                    if fix.get("can_retry"):
                        # Try simple fix first
                        fixed_sql = corrector.apply_fix(current_sql, fix)
                        
                        if fixed_sql and fixed_sql != current_sql:
                            # Simple fix worked
                            current_sql = fixed_sql
                            reasoning_steps.append({
                                "icon": "🔧", 
                                "text": f"Applied fix: {fix.get('fix_hint', 'Auto-correction')[:50]}", 
                                "status": "complete"
                            })
                        else:
                            # Need to regenerate with LLM
                            reasoning_steps.append({
                                "icon": "🤖", 
                                "text": "Regenerating SQL with error feedback...", 
                                "status": "complete"
                            })
                            
                            try:
                                retry_prompt_text = generate_retry_prompt(
                                    user_query, 
                                    current_sql, 
                                    error_msg, 
                                    fix, 
                                    refined_schema
                                )
                                gen_res_retry = generate_sql_with_reasoning(
                                    llm, 
                                    plan, 
                                    refined_schema, 
                                    enriched_query,
                                    retry_context=retry_prompt_text
                                )
                                current_sql = gen_res_retry["sql"]
                                llm_reasoning += f"\n\n[Retry {attempt+1}] {gen_res_retry.get('reasoning', '')}"
                            except Exception as regen_error:
                                # If regeneration fails, keep old SQL and hope for the best
                                reasoning_steps.append({
                                    "icon": "⚠️", 
                                    "text": f"Regeneration failed: {str(regen_error)[:50]}", 
                                    "status": "error"
                                })
                    else:
                        # Can't retry this error
                        break
                else:
                    # Max retries exceeded
                    return {
                        "answer": "I encountered errors executing the query after multiple attempts.", 
                        "error": error_msg, 
                        "reasoning_steps": reasoning_steps, 
                        "sql": sql,
                        "attempts": attempts
                    }

        if not exec_result: exec_result = {"columns": [], "rows": [], "row_count": 0}

        # ... [Answer Generation] ...
        reasoning_steps.append({"icon": "💬", "text": "Constructing answer...", "status": "complete"})
        try:
            final_answer = generate_final_answer(llm, user_query, current_sql, exec_result["columns"], exec_result["rows"], exec_result["row_count"])
        except:
             final_answer = interpret(exec_result, user_query)["answer"]
        
        session.add_system_message(final_answer)
        reasoning_steps.append({"icon": "✅", "text": "Done!", "status": "complete"})

        # ------------------------------------------------
        # 🆕 Generate Follow-up Suggestions
        # ------------------------------------------------
        suggestions = generate_related_questions(llm, user_query, refined_schema)

        return {
            "answer": final_answer,
            "reasoning": llm_reasoning,
            "reasoning_steps": reasoning_steps,
            "sql": current_sql,
            "columns": exec_result["columns"],
            "rows": exec_result["rows"],
            "row_count": exec_result["row_count"],
            "truncated": exec_result.get("truncated", False),
            "retries": len(attempts),
            "suggestions": suggestions
        }

    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}"
        print(f"[ERROR] {traceback.format_exc()}")
        return {"answer": "Error occurred.", "error": error_detail, "reasoning_steps": [{"icon": "❌", "text": "Error", "status": "error"}]}


# ... [Session/Health endpoints remain unchanged] ...
@app.get("/session/{session_id}")
def get_session_info(session_id: str):
    session = SESSIONS.get(session_id)
    if not session: raise HTTPException(status_code=404)
    return {"session_id": session_id, "tables": list(session.full_schema.keys()), "chat_history_length": len(session.get_chat_history()), "has_pending_clarification": session.clarification_state is not None}

@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    session = SESSIONS.pop(session_id, None)
    if session and os.path.exists(session.db_path): os.remove(session.db_path)
    return {"message": "Deleted"}

@app.get("/health")
def health(): return {"status": "ok", "active_sessions": len(SESSIONS)}

@app.get("/schema/{session_id}")
def get_schema(session_id: str):
    session = SESSIONS.get(session_id)
    if not session: raise HTTPException(status_code=404)
    return {"schema": session.full_schema}
