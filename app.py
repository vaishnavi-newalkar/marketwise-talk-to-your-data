import os

from db.validator import validate_sqlite_db
from db.schema_extractor import extract_schema
from db.schema_cache import SchemaCache
from session.session_manager import Session

from schema.refiner import refine_schema
from nlp.ambiguity_detector import detect_ambiguity
from nlp.intent_merger import merge_intent
from nlp.context_builder import build_context
from nlp.planner import create_plan

from llm.client import GroqClient
from llm.sql_generator import generate_sql

from validation.sql_validator import validate_sql
from db.executor import execute_sql
from response.interpreter import interpret
from utils.logger import setup_logger


def main():
    logger = setup_logger()

    print("=== NL → SQL CLI Demo ===")
    print("Note: For DB upload & multi-session use api.py\n")

    # ---------------------------------
    # 1️⃣ Ask user for DB path (CLI only)
    # ---------------------------------
    db_path = input("Enter path to SQLite DB: ").strip()

    if not os.path.exists(db_path):
        print("❌ Database file not found.")
        return

    # ---------------------------------
    # 2️⃣ Validate DB
    # ---------------------------------
    logger.info("Validating database...")
    validate_sqlite_db(db_path)

    # ---------------------------------
    # 3️⃣ Extract & cache schema
    # ---------------------------------
    logger.info("Extracting schema...")
    schema = extract_schema(db_path)

    cache = SchemaCache()
    cache.load(schema)

    # ---------------------------------
    # 4️⃣ Create session + LLM
    # ---------------------------------
    session = Session(db_path=db_path, schema=cache.get())
    llm = GroqClient()

    logger.info("System ready. Ask questions (type 'exit' to quit).")

    # ---------------------------------
    # 5️⃣ Chat loop (SAME as API logic)
    # ---------------------------------
    while True:
        user_input = input("\nUser > ").strip()

        if user_input.lower() in {"exit", "quit"}:
            logger.info("Session ended.")
            break

        # ------------------------------
        # Clarification handling
        # ------------------------------
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

        # ------------------------------
        # Ambiguity detection
        # ------------------------------
        if not resolving_clarification:
            ambiguous, data = detect_ambiguity(user_query)
            if ambiguous:
                data["original_query"] = user_query
                session.clarification_state = data
                session.add_system_message(data["question"])
                print("System >", data["question"])
                continue

        # ------------------------------
        # Context building
        # ------------------------------
        context = build_context(session.get_chat_history())
        enriched_query = f"{context}\nCurrent question: {user_query}"

        # ------------------------------
        # Schema refinement
        # ------------------------------
        refined_schema = refine_schema(session.full_schema, user_query)

        # ------------------------------
        # Planning
        # ------------------------------
        plan = create_plan(user_query, refined_schema)

        # ------------------------------
        # SQL generation
        # ------------------------------
        sql = generate_sql(
            llm_client=llm,
            plan=plan,
            schema=refined_schema,
            question=enriched_query
        )

        logger.info(f"Generated SQL:\n{sql}")

        # ------------------------------
        # Validation + execution
        # ------------------------------
        try:
            validate_sql(sql)
            rows = execute_sql(session.db_path, sql)
            answer = interpret(rows)
            print("\nAnswer >", answer)

        except Exception as e:
            logger.error(str(e))
            print("Error >", e)


if __name__ == "__main__":
    main()
