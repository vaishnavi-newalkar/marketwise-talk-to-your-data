import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

# -------------------------------------------------
# Page config
# -------------------------------------------------
st.set_page_config(
    page_title="NL → SQL Chat",
    page_icon="🧠",
    layout="centered"
)

st.title("🧠 NL → SQL Chat")
st.caption("Chat with your database like ChatGPT")

# -------------------------------------------------
# Session state
# -------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []  # chat history

if "tables" not in st.session_state:
    st.session_state.tables = None

if "waiting_for_clarification" not in st.session_state:
    st.session_state.waiting_for_clarification = False

# -------------------------------------------------
# Sidebar – DB Upload
# -------------------------------------------------
with st.sidebar:
    st.header("📂 Database")

    uploaded_db = st.file_uploader(
        "Upload SQLite DB",
        type=["db", "sqlite"]
    )

    if uploaded_db and st.button("Upload"):
        with st.spinner("Uploading DB..."):
            files = {"file": uploaded_db}
            res = requests.post(f"{API_URL}/upload-db", files=files)

        if res.status_code == 200:
            data = res.json()
            st.session_state.session_id = data["session_id"]
            st.session_state.tables = data["tables"]
            st.session_state.messages = []
            st.session_state.waiting_for_clarification = False
            st.success("Database ready ✅")
        else:
            st.error(res.json().get("detail", "Upload failed"))

    if st.session_state.tables:
        st.subheader("Tables")
        st.write(st.session_state.tables)

    if st.session_state.session_id:
        if st.button("🔄 Reset Chat"):
            st.session_state.session_id = None
            st.session_state.tables = None
            st.session_state.messages = []
            st.session_state.waiting_for_clarification = False
            st.rerun()

# -------------------------------------------------
# Chat history (ChatGPT style)
# -------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -------------------------------------------------
# Chat input
# -------------------------------------------------
if st.session_state.session_id:

    placeholder = (
        "Reply to clarify…" if st.session_state.waiting_for_clarification
        else "Ask a question about your database…"
    )

    user_input = st.chat_input(placeholder)

    if user_input:
        # Show user message immediately
        st.session_state.messages.append(
            {"role": "user", "content": user_input}
        )

        payload = {
            "session_id": st.session_state.session_id,
            "question": user_input,
            "is_clarification": st.session_state.waiting_for_clarification
        }

        with st.spinner("Thinking..."):
            res = requests.post(f"{API_URL}/ask", json=payload)

        if res.status_code != 200:
            st.session_state.messages.append(
                {"role": "assistant", "content": "❌ Error processing request"}
            )
            st.stop()

        result = res.json()

        # -----------------------------
        # Clarification turn (ChatGPT style)
        # -----------------------------
        if result.get("clarification"):
            st.session_state.messages.append(
                {"role": "assistant", "content": result["clarification"]}
            )
            st.session_state.waiting_for_clarification = True
            st.stop()  # ⛔ WAIT for user reply


        # -----------------------------
        # Normal answer turn
        # -----------------------------
        st.session_state.waiting_for_clarification = False

        if result.get("answer"):
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": result["answer"]
                }
            )

        with st.chat_message("assistant"):

            # ✅ Final Answer (human-readable)
            if result.get("answer"):
                st.markdown(f"✅ **{result['answer']}**")

            # 🧠 Reasoning (dropdown)
            if result.get("reasoning"):
                with st.expander("🧠 Reasoning"):
                    st.markdown(result["reasoning"])

            # 📊 Result Preview (table)
            if result.get("rows"):
                st.markdown("📊 **Result Preview**")
                st.dataframe(result["rows"], use_container_width=True)

            # 🔍 Generated SQL (dropdown)
            if result.get("sql"):
                with st.expander("🔍 Generated SQL"):
                    st.code(result["sql"], language="sql")


        st.rerun()

else:
    st.info("👈 Upload a SQLite database to start chatting")
