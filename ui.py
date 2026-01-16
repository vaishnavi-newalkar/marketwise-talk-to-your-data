"""
NL → SQL Chat Assistant - Streamlit UI

A beautiful, ChatGPT-style interface for natural language database queries.
Features:
- Modern glassmorphism design with dark theme
- ChatGPT-style chat bubbles with animations
- Sidebar for database upload and info
- Expandable sections for SQL, reasoning, and results
"""

import streamlit as st
import requests
import pandas as pd
from typing import Optional

# -------------------------------------------------
# Configuration
# -------------------------------------------------
API_URL = "http://127.0.0.1:8000"

# -------------------------------------------------
# Page Configuration
# -------------------------------------------------
st.set_page_config(
    page_title="SQL Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# Custom CSS for beautiful UI
# -------------------------------------------------
def apply_custom_css():
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Root variables */
    :root {
        --bg-primary: #0f0f23;
        --bg-secondary: #1a1a2e;
        --bg-tertiary: #16213e;
        --accent-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --accent-blue: #667eea;
        --accent-purple: #764ba2;
        --accent-pink: #f093fb;
        --accent-orange: #f5576c;
        --text-primary: #ffffff;
        --text-secondary: #a0a0b8;
        --text-muted: #6b6b80;
        --border-color: rgba(255, 255, 255, 0.1);
        --glass-bg: rgba(255, 255, 255, 0.05);
        --glass-border: rgba(255, 255, 255, 0.1);
        --user-bubble: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --assistant-bubble: rgba(255, 255, 255, 0.08);
        --success-color: #10b981;
        --error-color: #ef4444;
        --warning-color: #f59e0b;
    }
    
    /* Global styles */
    .stApp {
        background: linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-secondary) 50%, var(--bg-tertiary) 100%);
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main title styling */
    .main-title {
        background: var(--accent-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.5rem;
        animation: fadeIn 0.8s ease-out;
    }
    
    .subtitle {
        color: var(--text-secondary);
        text-align: center;
        font-size: 1.1rem;
        font-weight: 400;
        margin-bottom: 2rem;
        animation: fadeIn 1s ease-out;
    }
    
    /* Chat container */
    .chat-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 1rem;
    }
    
    /* Message bubbles */
    .message-container {
        display: flex;
        margin-bottom: 1.5rem;
        animation: slideIn 0.3s ease-out;
    }
    
    .message-container.user {
        justify-content: flex-end;
    }
    
    .message-container.assistant {
        justify-content: flex-start;
    }
    
    .message-bubble {
        max-width: 85%;
        padding: 1rem 1.25rem;
        border-radius: 1.25rem;
        font-size: 0.95rem;
        line-height: 1.6;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    
    .user .message-bubble {
        background: var(--user-bubble);
        color: white;
        border-bottom-right-radius: 0.25rem;
    }
    
    .assistant .message-bubble {
        background: var(--assistant-bubble);
        color: var(--text-primary);
        border-bottom-left-radius: 0.25rem;
        backdrop-filter: blur(10px);
        border: 1px solid var(--glass-border);
    }
    
    /* Avatar styling */
    .avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        margin: 0 0.75rem;
        flex-shrink: 0;
    }
    
    .user .avatar {
        background: var(--accent-gradient);
        order: 2;
    }
    
    .assistant .avatar {
        background: rgba(102, 126, 234, 0.2);
        border: 1px solid var(--accent-blue);
    }
    
    /* Answer card styling */
    .answer-card {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 1rem;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    
    .answer-card h4 {
        color: var(--success-color);
        margin: 0 0 0.5rem 0;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* SQL code block styling */
    .sql-block {
        background: rgba(0, 0, 0, 0.4);
        border: 1px solid var(--border-color);
        border-radius: 0.75rem;
        padding: 1rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        overflow-x: auto;
        color: #e2e8f0;
    }
    
    /* Reasoning block styling */
    .reasoning-block {
        background: rgba(102, 126, 234, 0.1);
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 0.75rem;
        padding: 1rem;
        color: var(--text-secondary);
        font-size: 0.9rem;
        line-height: 1.7;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(26, 26, 46, 0.95) 0%, rgba(22, 33, 62, 0.95) 100%);
        backdrop-filter: blur(20px);
        border-right: 1px solid var(--border-color);
    }
    
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: var(--text-primary);
    }
    
    /* File uploader styling */
    .stFileUploader > div {
        background: var(--glass-bg);
        border: 2px dashed var(--glass-border);
        border-radius: 1rem;
        padding: 1.5rem;
        transition: all 0.3s ease;
    }
    
    .stFileUploader > div:hover {
        border-color: var(--accent-blue);
        background: rgba(102, 126, 234, 0.1);
    }
    
    /* Button styling - Updated for Streamlit 1.31+ */
    .stButton > button {
        background: var(--accent-gradient) !important;
        color: white !important;
        border: none !important;
        border-radius: 0.75rem !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6) !important;
    }
    
    /* Chat input styling */
    .stChatInput > div {
        background: var(--glass-bg) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 1rem !important;
    }
    
    .stChatInput textarea {
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: var(--glass-bg) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 0.75rem !important;
        color: var(--text-primary) !important;
        font-weight: 500 !important;
    }
    
    .streamlit-expanderContent {
        background: rgba(0, 0, 0, 0.2) !important;
        border: 1px solid var(--glass-border) !important;
        border-top: none !important;
        border-radius: 0 0 0.75rem 0.75rem !important;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        border-radius: 0.75rem;
        overflow: hidden;
    }
    
    /* Info/Success/Error boxes */
    .stAlert {
        background: var(--glass-bg) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 0.75rem !important;
    }
    
    /* Spinner styling */
    .stSpinner > div {
        border-color: var(--accent-blue) transparent transparent transparent !important;
    }
    
    /* Table list in sidebar */
    .table-chip {
        display: inline-block;
        background: rgba(102, 126, 234, 0.2);
        border: 1px solid rgba(102, 126, 234, 0.3);
        color: var(--accent-blue);
        padding: 0.25rem 0.75rem;
        border-radius: 2rem;
        font-size: 0.85rem;
        margin: 0.25rem;
        transition: all 0.2s ease;
    }
    
    .table-chip:hover {
        background: rgba(102, 126, 234, 0.3);
        transform: translateY(-1px);
    }
    
    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    .thinking-indicator {
        display: flex;
        gap: 0.25rem;
        padding: 0.5rem;
    }
    
    .thinking-dot {
        width: 8px;
        height: 8px;
        background: var(--accent-blue);
        border-radius: 50%;
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    .thinking-dot:nth-child(2) { animation-delay: 0.2s; }
    .thinking-dot:nth-child(3) { animation-delay: 0.4s; }
    
    /* Status badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: 2rem;
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    .status-badge.connected {
        background: rgba(16, 185, 129, 0.2);
        color: var(--success-color);
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .status-badge.disconnected {
        background: rgba(239, 68, 68, 0.2);
        color: var(--error-color);
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--glass-border);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--accent-blue);
    }
    </style>
    """, unsafe_allow_html=True)


def render_header():
    """Render the main header."""
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 class="main-title">🧠 SQL Assistant</h1>
        <p class="subtitle">Chat with your database using natural language</p>
    </div>
    """, unsafe_allow_html=True)


def render_message(role: str, content: str, extra_data: Optional[dict] = None):
    """Render a chat message with optional expandable sections."""
    avatar = "👤" if role == "user" else "🤖"
    
    with st.chat_message(role, avatar=avatar):
        st.markdown(content)
        
        if extra_data and role == "assistant":
            # Render expandable sections
            if extra_data.get("reasoning"):
                with st.expander("🧠 **Reasoning Process**", expanded=False):
                    st.markdown(f"""
                    <div class="reasoning-block">
                    {extra_data['reasoning']}
                    </div>
                    """, unsafe_allow_html=True)
            
            if extra_data.get("sql"):
                with st.expander("🔍 **Generated SQL Query**", expanded=False):
                    st.code(extra_data["sql"], language="sql")
            
            if extra_data.get("rows") and extra_data.get("columns"):
                with st.expander(f"📊 **Result Preview** ({extra_data.get('row_count', len(extra_data['rows']))} rows)", expanded=True):
                    df = pd.DataFrame(extra_data["rows"], columns=extra_data["columns"])
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        height=min(400, len(df) * 38 + 40)
                    )
                    
                    if extra_data.get("truncated"):
                        st.warning("⚠️ Results were truncated. Showing first 1000 rows.")
            
            if extra_data.get("error"):
                st.error(f"⚠️ **Error:** {extra_data['error']}")


def check_api_health() -> bool:
    """Check if the API is reachable."""
    try:
        res = requests.get(f"{API_URL}/health", timeout=2)
        return res.status_code == 200
    except:
        return False


def upload_database(file) -> Optional[dict]:
    """Upload database to the API."""
    try:
        files = {"file": (file.name, file.getvalue(), "application/octet-stream")}
        res = requests.post(f"{API_URL}/upload-db", files=files, timeout=30)
        if res.status_code == 200:
            return res.json()
        else:
            error = res.json().get("detail", "Upload failed")
            st.error(f"❌ {error}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the API server. Please ensure it's running.")
        return None
    except Exception as e:
        st.error(f"❌ Upload error: {str(e)}")
        return None


def send_question(session_id: str, question: str, is_clarification: bool = False) -> Optional[dict]:
    """Send a question to the API."""
    try:
        payload = {
            "session_id": session_id,
            "question": question,
            "is_clarification": is_clarification
        }
        res = requests.post(f"{API_URL}/ask", json=payload, timeout=60)
        
        if res.status_code == 200:
            return res.json()
        elif res.status_code == 404:
            st.error("❌ Session expired. Please upload the database again.")
            return None
        else:
            error = res.json().get("detail", "Request failed")
            return {"error": error, "answer": f"Error: {error}"}
    except requests.exceptions.ConnectionError:
        st.error("❌ Lost connection to the API server.")
        return None
    except requests.exceptions.Timeout:
        st.error("❌ Request timed out. The query may be too complex.")
        return None
    except Exception as e:
        return {"error": str(e), "answer": f"Error: {str(e)}"}


def render_sidebar():
    """Render the sidebar with database upload and info."""
    with st.sidebar:
        st.markdown("## 📂 Database")
        
        # API Status
        api_healthy = check_api_health()
        if api_healthy:
            st.markdown("""
            <div class="status-badge connected">
                <span>●</span> API Connected
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-badge disconnected">
                <span>●</span> API Disconnected
            </div>
            """, unsafe_allow_html=True)
            st.warning("Start the API server with:\n`uvicorn api:app --reload`")
        
        st.markdown("---")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Upload SQLite Database",
            type=["db", "sqlite", "sqlite3"],
            help="Upload a SQLite database file to start chatting"
        )
        
        if uploaded_file:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📤 Upload", use_container_width=True):
                    with st.spinner("Processing database..."):
                        result = upload_database(uploaded_file)
                        if result:
                            st.session_state.session_id = result["session_id"]
                            st.session_state.tables = result["tables"]
                            st.session_state.messages = []
                            st.session_state.waiting_for_clarification = False
                            st.success(f"✅ Database loaded! ({result['table_count']} tables)")
                            st.rerun()
        
        # Show current database info
        if st.session_state.get("tables"):
            st.markdown("---")
            st.markdown("### 📋 Tables")
            
            # Render table chips
            table_html = "".join([
                f'<span class="table-chip">{table}</span>' 
                for table in st.session_state.tables
            ])
            st.markdown(f'<div style="margin-top: 0.5rem;">{table_html}</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Reset button
            if st.button("🔄 Reset Chat", use_container_width=True):
                st.session_state.messages = []
                st.session_state.waiting_for_clarification = False
                st.rerun()
            
            if st.button("🗑️ Clear Session", use_container_width=True):
                # Clear everything
                for key in ["session_id", "tables", "messages", "waiting_for_clarification"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        st.markdown("---")
        st.markdown("""
        <div style="color: var(--text-muted); font-size: 0.8rem; padding: 1rem 0;">
            <p><strong>Tips:</strong></p>
            <ul style="padding-left: 1.2rem; margin: 0.5rem 0;">
                <li>Ask questions in plain English</li>
                <li>Reference table and column names</li>
                <li>Be specific about what you want</li>
                <li>Use "top 5", "highest", "average" etc.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


def main():
    """Main application entry point."""
    
    # Apply CSS
    apply_custom_css()
    
    # Initialize session state
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "tables" not in st.session_state:
        st.session_state.tables = None
    if "waiting_for_clarification" not in st.session_state:
        st.session_state.waiting_for_clarification = False
    
    # Render components
    render_sidebar()
    render_header()
    
    # Main chat area
    if not st.session_state.session_id:
        # Welcome screen
        st.markdown("""
        <div style="
            text-align: center;
            padding: 4rem 2rem;
            background: rgba(255, 255, 255, 0.02);
            border: 1px dashed rgba(255, 255, 255, 0.1);
            border-radius: 1.5rem;
            margin: 2rem auto;
            max-width: 600px;
        ">
            <div style="font-size: 4rem; margin-bottom: 1rem;">📂</div>
            <h2 style="color: #ffffff; margin-bottom: 0.5rem;">Upload a Database to Start</h2>
            <p style="color: #a0a0b8; font-size: 1.1rem;">
                Upload a SQLite database file using the sidebar to begin asking questions
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Feature cards
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div style="
                background: rgba(102, 126, 234, 0.1);
                border: 1px solid rgba(102, 126, 234, 0.2);
                border-radius: 1rem;
                padding: 1.5rem;
                text-align: center;
                height: 100%;
            ">
                <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">💬</div>
                <h3 style="color: #ffffff; margin-bottom: 0.5rem; font-size: 1.1rem;">Natural Language</h3>
                <p style="color: #a0a0b8; font-size: 0.9rem;">Ask questions in plain English</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style="
                background: rgba(118, 75, 162, 0.1);
                border: 1px solid rgba(118, 75, 162, 0.2);
                border-radius: 1rem;
                padding: 1.5rem;
                text-align: center;
                height: 100%;
            ">
                <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🧠</div>
                <h3 style="color: #ffffff; margin-bottom: 0.5rem; font-size: 1.1rem;">Smart Reasoning</h3>
                <p style="color: #a0a0b8; font-size: 0.9rem;">See how queries are generated</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div style="
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.2);
                border-radius: 1rem;
                padding: 1.5rem;
                text-align: center;
                height: 100%;
            ">
                <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📊</div>
                <h3 style="color: #ffffff; margin-bottom: 0.5rem; font-size: 1.1rem;">Instant Results</h3>
                <p style="color: #a0a0b8; font-size: 0.9rem;">View data in beautiful tables</p>
            </div>
            """, unsafe_allow_html=True)
        
        return
    
    # Chat history
    for msg in st.session_state.messages:
        render_message(
            role=msg["role"],
            content=msg["content"],
            extra_data=msg.get("extra_data")
        )
    
    # Chat input
    placeholder = (
        "Reply to clarify..." if st.session_state.waiting_for_clarification
        else "Ask a question about your database..."
    )
    
    if user_input := st.chat_input(placeholder):
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Display user message
        render_message("user", user_input)
        
        # Get response
        with st.spinner(""):
            # Show thinking indicator
            thinking_placeholder = st.empty()
            thinking_placeholder.markdown("""
            <div style="display: flex; align-items: center; gap: 1rem; padding: 1rem;">
                <div style="
                    background: rgba(102, 126, 234, 0.2);
                    border-radius: 50%;
                    width: 36px;
                    height: 36px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 1.2rem;
                ">🤖</div>
                <div class="thinking-indicator">
                    <div class="thinking-dot"></div>
                    <div class="thinking-dot"></div>
                    <div class="thinking-dot"></div>
                </div>
                <span style="color: #a0a0b8; font-size: 0.9rem;">Thinking...</span>
            </div>
            """, unsafe_allow_html=True)
            
            result = send_question(
                st.session_state.session_id,
                user_input,
                st.session_state.waiting_for_clarification
            )
            
            thinking_placeholder.empty()
        
        if not result:
            st.rerun()
            return
        
        # Handle clarification
        if result.get("clarification"):
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["clarification"],
                "extra_data": {
                    "term": result.get("term"),
                    "options": result.get("options")
                }
            })
            st.session_state.waiting_for_clarification = True
            st.rerun()
            return
        
        # Normal answer
        st.session_state.waiting_for_clarification = False
        
        answer = result.get("answer", "I couldn't process that query.")
        extra_data = {
            "reasoning": result.get("reasoning"),
            "sql": result.get("sql"),
            "columns": result.get("columns"),
            "rows": result.get("rows"),
            "row_count": result.get("row_count"),
            "truncated": result.get("truncated"),
            "error": result.get("error")
        }
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "extra_data": extra_data
        })
        
        st.rerun()


if __name__ == "__main__":
    main()
