import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

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
from schema.refiner import refine_schema
from nlp.planner import create_plan

from llm.client import GroqClient
from llm.sql_generator import generate_sql

from validation.sql_validator import validate_sql
from db.executor import execute_sql
from response.interpreter import interpret


# ----------------------------
# App & global state
# ----------------------------
app = FastAPI(title="NL → SQL System (Session-Based)")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploaded_dbs")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory session store (hackathon-safe)
SESSIONS: dict[str, Session] = {}

# Single shared LLM client
llm = GroqClient()


# ----------------------------
# Request models
# ----------------------------
class QuestionRequest(BaseModel):
    session_id: str
    question: str


# ============================================================
# 1️⃣ DB UPLOAD (ONCE PER SESSION)
# ============================================================
@app.post("/upload-db")
async def upload_db(file: UploadFile = File(...)):
    """
    Upload a SQLite database and create a new session.
    """

    if not file.filename.lower().endswith((".db", ".sqlite")):
        raise HTTPException(
            status_code=400,
            detail="Only SQLite (.db / .sqlite) files are allowed."
        )

    # Create session id
    session_id = str(uuid.uuid4())
    db_path = os.path.join(UPLOAD_DIR, f"{session_id}.sqlite")

    # Save DB file
    with open(db_path, "wb") as f:
        f.write(await file.read())

    # Validate DB
    try:
        validate_sqlite_db(db_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Extract & cache schema
    schema = extract_schema(db_path)
    cache = SchemaCache()
    cache.load(schema)

    # Create session
    session = Session(db_path=db_path, schema=cache.get())
    SESSIONS[session_id] = session

    return {
        "session_id": session_id,
        "tables": list(schema.keys()),
        "message": "Database uploaded and session created successfully."
    }


# ============================================================
# 2️⃣ ASK QUESTIONS (CHAT LOOP)
# ============================================================
@app.post("/ask")
def ask_question(req: QuestionRequest):
    """
    Ask a natural language question for a given session.
    """

    session = SESSIONS.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid session_id")

    user_input = req.question.strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # ------------------------------------------------
    # Handle clarification response (STATEFUL)
    # ------------------------------------------------
    resolving_clarification = False

    if session.clarification_state:
        user_query = merge_intent(
            original_query=session.clarification_state["original_query"],
            clarification_response=user_input,
            clarification_state=session.clarification_state
        )
        session.clear_clarification()
        resolving_clarification = True
    else:
        user_query = user_input

    session.add_user_message(user_query)

    # ------------------------------------------------
    # Build conversational context
    # ------------------------------------------------
    context = build_context(session.get_chat_history())

    enriched_query = f"""
    Conversation so far:
    {context}

    Current user question:
    {user_query}
    """

    # ------------------------------------------------
    # Ambiguity detection (SKIP if resolving)
    # ------------------------------------------------
    if not resolving_clarification:
        ambiguous, data = detect_ambiguity(enriched_query)
        if ambiguous:
            data["original_query"] = enriched_query
            session.clarification_state = data
            session.add_system_message(data["question"])
            return {
                "clarification": data["question"]
            }

    # ------------------------------------------------
    # Schema refinement (USE CONTEXT)
    # ------------------------------------------------
    refined_schema = refine_schema(
        session.full_schema,
        enriched_query
    )


    # ------------------------------------------------
    # Planning
    # ------------------------------------------------
    plan = create_plan(user_query, refined_schema)

    # ------------------------------------------------
    # SQL generation
    # ------------------------------------------------
    sql = generate_sql(
        llm_client=llm,
        plan=plan,
        schema=refined_schema,
        question=enriched_query
    )

    # ------------------------------------------------
    # SQL validation & execution
    # ------------------------------------------------
    try:
        validate_sql(sql)
        rows = execute_sql(session.db_path, sql)
        answer = interpret(rows)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "sql": sql,
        "answer": answer
    }


# ============================================================
# 3️⃣ HEALTH CHECK (OPTIONAL)
# ============================================================
@app.get("/health")
def health():
    return {
        "status": "ok",
        "active_sessions": len(SESSIONS)
    }
