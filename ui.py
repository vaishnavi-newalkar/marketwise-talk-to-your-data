"""
NL → SQL Chat Assistant - Streamlit UI

A beautiful, ChatGPT-style interface with:
- Modern glassmorphism design
- Live step-by-step reasoning display
- Expandable sections for SQL, reasoning, and results
- Smart suggestions & onboarding
"""

import streamlit as st
import requests
import pandas as pd
import json
import os
from datetime import datetime
from typing import Optional, Dict, List
import uuid

# -------------------------------------------------
# Configuration
# -------------------------------------------------
API_URL = "http://127.0.0.1:8000"
CHAT_HISTORY_FILE = "chat_history.json"

st.set_page_config(
    page_title="SQL Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# Chat History Persistence
# -------------------------------------------------
def load_chat_history() -> Dict:
    if os.path.exists(CHAT_HISTORY_FILE):
        try:
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"chats": {}, "current_chat_id": None}
    return {"chats": {}, "current_chat_id": None}

def save_chat_history(data: Dict):
    try:
        with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"Failed to save: {e}")

def create_new_chat(db_name: str = None, session_id: str = None, tables: List[str] = None, initial_questions: List[str] = None) -> str:
    chat_id = str(uuid.uuid4())[:8]
    history = load_chat_history()
    history["chats"][chat_id] = {
        "id": chat_id,
        "title": "New Chat",
        "db_name": db_name,
        "session_id": session_id,
        "tables": tables or [],
        "initial_questions": initial_questions or [],
        "messages": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    history["current_chat_id"] = chat_id
    save_chat_history(history)
    return chat_id

def update_chat_title(chat_id: str, first_message: str):
    history = load_chat_history()
    if chat_id in history["chats"]:
        title = first_message[:30] + "..." if len(first_message) > 30 else first_message
        history["chats"][chat_id]["title"] = title
        save_chat_history(history)

def add_message_to_chat(chat_id: str, role: str, content: str, extra_data: Dict = None):
    history = load_chat_history()
    if chat_id in history["chats"]:
        msg = {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        if extra_data: msg["extra_data"] = extra_data
        history["chats"][chat_id]["messages"].append(msg)
        history["chats"][chat_id]["updated_at"] = datetime.now().isoformat()
        
        # Auto-title on first user message
        if role == "user" and len([m for m in history["chats"][chat_id]["messages"] if m["role"] == "user"]) == 1:
            update_chat_title(chat_id, content)
            
        save_chat_history(history)

def delete_chat(chat_id: str):
    history = load_chat_history()
    if chat_id in history["chats"]:
        del history["chats"][chat_id]
        if history["current_chat_id"] == chat_id:
            msg_ids = list(history["chats"].keys())
            history["current_chat_id"] = msg_ids[0] if msg_ids else None
        save_chat_history(history)

def get_current_chat() -> Optional[Dict]:
    history = load_chat_history()
    cid = history.get("current_chat_id")
    return history["chats"].get(cid) if cid else None

def switch_chat(chat_id: str):
    history = load_chat_history()
    history["current_chat_id"] = chat_id
    save_chat_history(history)

def get_all_chats() -> List[Dict]:
    history = load_chat_history()
    return sorted(history["chats"].values(), key=lambda x: x.get("updated_at", ""), reverse=True)


# -------------------------------------------------
# UI Components
# -------------------------------------------------
def apply_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 25%, #2a1f3e 50%, #1a1f3a 75%, #0a0e27 100%);
        background-size: 400% 400%;
        animation: gradientShift 15s ease infinite;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .main-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        letter-spacing: -0.5px;
        margin-bottom: 1rem;
        text-shadow: 0 0 30px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button {
        border-radius: 0.75rem !important;
        font-weight: 500 !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        background: rgba(102, 126, 234, 0.1) !important;
        backdrop-filter: blur(10px) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4) !important;
        border-color: rgba(102, 126, 234, 0.5) !important;
        background: rgba(102, 126, 234, 0.2) !important;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 8px 30px rgba(102, 126, 234, 0.6) !important;
        transform: translateY(-2px) scale(1.02);
    }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(15, 18, 35, 0.95) 0%, rgba(22, 26, 46, 0.95) 100%);
        border-right: 1px solid rgba(102, 126, 234, 0.2);
        backdrop-filter: blur(20px);
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.3);
    }
    
    /* Chat message styling */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 1rem !important;
        backdrop-filter: blur(10px) !important;
        margin-bottom: 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stChatMessage:hover {
        background: rgba(255, 255, 255, 0.05) !important;
        border-color: rgba(102, 126, 234, 0.3) !important;
        transform: translateX(4px);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: rgba(102, 126, 234, 0.1) !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
        border-radius: 0.5rem !important;
        font-weight: 600 !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(102, 126, 234, 0.15) !important;
        border-color: rgba(102, 126, 234, 0.4) !important;
    }
    
    /* Input styling */
    .stTextInput > div > div > input,
    .stChatInput > div > input {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(102, 126, 234, 0.3) !important;
        border-radius: 0.75rem !important;
        color: white !important;
        font-weight: 400 !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stChatInput > div > input:focus {
        border-color: rgba(102, 126, 234, 0.6) !important;
        box-shadow: 0 0 20px rgba(102, 126, 234, 0.3) !important;
        background: rgba(255, 255, 255, 0.08) !important;
    }
    
    /* Success/Error/Info boxes */
    .stSuccess, .stError, .stInfo {
        border-radius: 0.75rem !important;
        border-left: 4px solid !important;
        backdrop-filter: blur(10px) !important;
        animation: slideIn 0.3s ease-out;
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-10px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    /* Code blocks */
    code {
        background: rgba(102, 126, 234, 0.1) !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
        border-radius: 0.375rem !important;
        padding: 0.125rem 0.375rem !important;
        font-family: 'Fira Code', 'Courier New', monospace !important;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        border-radius: 0.75rem !important;
        overflow: hidden !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #667eea !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* Divider */
    hr {
        border-color: rgba(102, 126, 234, 0.2) !important;
        margin: 1.5rem 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)


def render_reasoning_tree(steps):
    if not steps: return
    st.markdown("**System reasoning:**")
    for i, step in enumerate(steps):
        icon = step.get("icon", "•")
        status = step.get("status", "complete")
        color = "green" if status == "complete" else "red" if status == "error" else "orange" if status == "retry" else "gray"
        prefix = "└──" if i == len(steps) - 1 else "├──"
        st.markdown(f"`{prefix}` {icon} :{color}[{step.get('text', '')}]")


def render_message(role: str, content: str, extra_data: Optional[Dict] = None, message_index: int = 0):
    avatar = "👤" if role == "user" else "🤖"
    with st.chat_message(role, avatar=avatar):
        if role == "user":
            st.markdown(content)
            return

        if extra_data:
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
            
            if extra_data.get("reasoning_steps"):
                render_reasoning_tree(extra_data["reasoning_steps"])
                st.markdown("---")
            
            if content:
                st.success(f"**✅ Answer**\n\n{content}")
            
            if extra_data.get("reasoning") or extra_data.get("sql"):
                c1, c2 = st.columns(2)
                with c1:
                    if extra_data.get("reasoning"):
                        with st.expander("🧠 LLM Reasoning"): st.markdown(extra_data["reasoning"])
                with c2:
                    if extra_data.get("sql"):
                        with st.expander("🔍 Generated SQL"): st.code(extra_data["sql"], language="sql")
            
            if extra_data.get("rows") and extra_data.get("columns"):
                rc = extra_data.get('row_count', len(extra_data['rows']))
                with st.expander(f"📊 Result Data ({rc} rows)", expanded=True):
                    df = pd.DataFrame(extra_data["rows"], columns=extra_data["columns"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
            
            if extra_data.get("suggestions"):
                st.markdown("**✨ Suggested Follow-ups:**")
                cols = st.columns(len(extra_data["suggestions"]))
                for idx, sugg in enumerate(extra_data["suggestions"]):
                    with cols[idx]:
                        # Use message_index for unique key
                        if st.button(sugg, key=f"sugg_{message_index}_{idx}"):
                            # Set input and rerun logic handled in main loop
                            st.session_state.clicked_suggestion = sugg
                            st.rerun()

            if extra_data.get("error"):
                st.error(f"⚠️ **Error:** {extra_data['error']}")
                
                # Show retry attempts if available
                if extra_data.get("attempts"):
                    with st.expander("🔍 View Retry Attempts"):
                        for i, attempt in enumerate(extra_data["attempts"], 1):
                            st.markdown(f"**Attempt {i}:**")
                            st.code(attempt.get("sql", ""), language="sql")
                            st.caption(f"Error: {attempt.get('error', 'Unknown')}")
                            st.divider()
        else:
            st.markdown(content)


def check_api_health() -> bool:
    try:
        return requests.get(f"{API_URL}/health", timeout=2).status_code == 200
    except: return False

def upload_database(file) -> Optional[Dict]:
    try:
        files = {"file": (file.name, file.getvalue(), "application/octet-stream")}
        res = requests.post(f"{API_URL}/upload-db", files=files, timeout=60)
        return res.json() if res.status_code == 200 else None
    except: return None

def send_question(session_id: str, question: str, is_clarification: bool = False) -> Optional[Dict]:
    try:
        payload = {"session_id": session_id, "question": question, "is_clarification": is_clarification}
        res = requests.post(f"{API_URL}/ask", json=payload, timeout=120)
        return res.json() if res.status_code == 200 else None
    except: return None

def get_schema(session_id: str) -> Optional[Dict]:
    """Fetch the database schema from the API."""
    try:
        res = requests.get(f"{API_URL}/schema/{session_id}", timeout=10)
        return res.json() if res.status_code == 200 else None
    except: return None


def main():
    apply_custom_css()
    
    # State Init
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = load_chat_history().get("current_chat_id")
    if "clicked_suggestion" not in st.session_state:
        st.session_state.clicked_suggestion = None
    if "waiting_for_clarification" not in st.session_state:
        st.session_state.waiting_for_clarification = False

    # Sidebar
    with st.sidebar:
        if st.button("➕ New Chat", use_container_width=True, type="primary"):
            st.session_state.current_chat_id = create_new_chat()
            st.session_state.clicked_suggestion = None
            st.rerun()
        
        st.divider()
        st.subheader("💬 History")
        
        chats = get_all_chats()
        current_id = st.session_state.current_chat_id
        
        for chat in chats:
            c1, c2 = st.columns([5, 1])
            is_active = chat["id"] == current_id
            title = chat.get("title", "New Chat")
            
            if c1.button(f"{'📌' if is_active else '💬'} {title[:20]}...", key=chat["id"], use_container_width=True):
                switch_chat(chat["id"])
                st.session_state.current_chat_id = chat["id"]
                st.rerun()
            
            if c2.button("🗑️", key=f"del_{chat['id']}"):
                delete_chat(chat["id"])
                st.rerun()

        st.divider()
        st.subheader("📂 Database")
        
        # API Status with real-time check
        api_status = check_api_health()
        if api_status:
            st.success("✅ API Connected", icon="🟢")
        else:
            st.error("❌ API Disconnected", icon="🔴")
            st.caption("⚠️ Please start the API server:\n```bash\nuvicorn api:app --reload\n```")
        
        uploaded_file = st.file_uploader("Upload SQLite", type=["db", "sqlite"])
        if uploaded_file and st.button("📤 Upload", use_container_width=True):
            with st.spinner("Analyzing schema..."):
                res = upload_database(uploaded_file)
                if res:
                    history = load_chat_history()
                    cid = st.session_state.current_chat_id
                    
                    if not cid or cid not in history["chats"]:
                        cid = create_new_chat(uploaded_file.name, res["session_id"], res["tables"], res.get("initial_questions"))
                        st.session_state.current_chat_id = cid
                    else:
                        history["chats"][cid].update({
                            "db_name": uploaded_file.name,
                            "session_id": res["session_id"],
                            "tables": res["tables"],
                            "initial_questions": res.get("initial_questions", [])
                        })
                        save_chat_history(history)
                    
                    st.success("✅ Database linked!")
                    st.rerun()
        
        # Display schema if database is loaded
        current_chat = get_current_chat()
        if current_chat and current_chat.get("session_id"):
            st.divider()
            st.subheader("📊 Database Schema")
            
            # Fetch schema from API
            schema_data = get_schema(current_chat["session_id"])
            if schema_data and schema_data.get("schema"):
                schema = schema_data["schema"]
                
                # Display database name
                db_name = current_chat.get("db_name", "Unknown")
                st.caption(f"**Database:** {db_name}")
                st.caption(f"**Tables:** {len(schema)}")
                
                # Display each table with its columns
                for table_name, table_info in schema.items():
                    with st.expander(f"📋 {table_name}", expanded=False):
                        columns = table_info.get("columns", [])
                        column_types = table_info.get("column_types", {})
                        primary_keys = table_info.get("primary_key", [])
                        row_count = table_info.get("row_count", 0)
                        
                        st.caption(f"**Rows:** {row_count:,}")
                        st.markdown("**Columns:**")
                        
                        for col in columns:
                            col_type = column_types.get(col, "")
                            pk_marker = " 🔑" if col in primary_keys else ""
                            st.markdown(f"• `{col}` ({col_type}){pk_marker}")
                        
                        # Show foreign keys if any
                        foreign_keys = table_info.get("foreign_keys", [])
                        if foreign_keys:
                            st.markdown("**Foreign Keys:**")
                            for fk in foreign_keys:
                                st.markdown(f"• {fk['from']} → {fk['to_table']}.{fk['to_column']}")
            else:
                st.info("Schema not available")

    # Main Area
    st.markdown("<h1 class='main-title'>🧠 SQL Assistant</h1>", unsafe_allow_html=True)
    
    current_chat = get_current_chat()
    if not current_chat or not current_chat.get("session_id"):
        st.info("👈 Upload a database to get started!", icon="📂")
        return

    # Display History
    for i, msg in enumerate(current_chat.get("messages", [])):
        render_message(msg["role"], msg["content"], msg.get("extra_data"), message_index=i)

    # Initial Questions (Onboarding)
    # Don't show initial questions if a suggestion was just clicked
    if not current_chat.get("messages") and not st.session_state.get("clicked_suggestion"):
        suggestions = current_chat.get("initial_questions", [])
        if suggestions:
            st.markdown("### 💡 Recommended Starter Questions")
            cols = st.columns(2)
            for i, q in enumerate(suggestions):
                if cols[i % 2].button(f"✨ {q}", key=f"init_{i}", use_container_width=True):
                    st.session_state.clicked_suggestion = q
                    st.rerun()

    # Input Handling
    user_input = st.chat_input("Ask a question...")
    
    # Handle clicked suggestion override
    if st.session_state.clicked_suggestion:
        user_input = st.session_state.clicked_suggestion
        st.session_state.clicked_suggestion = None  # Reset immediately

    if user_input:
        # Add User Message
        add_message_to_chat(st.session_state.current_chat_id, "user", user_input)
        with st.chat_message("user", avatar="👤"): st.markdown(user_input)

        # Process Response
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("🔄 Thinking..."):
                res = send_question(
                    current_chat["session_id"], 
                    user_input, 
                    st.session_state.waiting_for_clarification
                )
        
        if res:
            # Handle Clarification
            if res.get("clarification"):
                clarification_data = {
                    "clarification": res.get("clarification"),
                    "term": res.get("term"),
                    "options": res.get("options", []),
                    "reasoning_steps": res.get("reasoning_steps", [])
                }
                add_message_to_chat(st.session_state.current_chat_id, "assistant", res["clarification"], clarification_data)
                st.session_state.waiting_for_clarification = True
                st.rerun()
            
            # Save Response
            extra_data = {
                "reasoning": res.get("reasoning"),
                "reasoning_steps": res.get("reasoning_steps"),
                "sql": res.get("sql"),
                "columns": res.get("columns"),
                "rows": res.get("rows"),
                "suggestions": res.get("suggestions"),  # Save suggestions!
                "error": res.get("error"),
                "attempts": res.get("attempts")  # Save retry attempts
            }
            add_message_to_chat(st.session_state.current_chat_id, "assistant", res.get("answer"), extra_data)
            st.session_state.waiting_for_clarification = False
            st.rerun()

if __name__ == "__main__":
    main()
