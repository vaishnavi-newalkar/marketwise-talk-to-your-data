# 🧠 SQL Assistant - Natural Language to SQL

A beautiful, premium ChatGPT-style SQL assistant that converts natural language questions into SQL queries with intelligent error handling and self-correction.

## ✨ Features

- 🎨 **Premium UI**: Beautiful glassmorphism design with smooth animations
- 🤖 **Smart SQL Generation**: Powered by Groq LLMs (Llama 3.3)
- 🔄 **Self-Correction**: Automatically retries and fixes syntax errors
- 💬 **Chat History**: Persistent conversation history
- 📊 **Rich Results**: Interactive data tables and visualizations
- 🎯 **Suggestions**: Smart follow-up question recommendations
- 🔍 **Meta Queries**: Ask questions about your database schema
- ⚡ **Real-time**: Live reasoning steps and progress tracking

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file (already exists):

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

### 3. Run Application

#### Easy Way (Recommended):
```bash
# Double-click start.bat or run:
start.bat
```

#### Manual Way:
```bash
# Terminal 1 - Start API
uvicorn api:app --reload

# Terminal 2 - Start UI
streamlit run ui.py
```

### 4. Use the App

1. Open browser at `http://localhost:8501`
2. Upload a SQLite database (.db, .sqlite)
3. Start asking questions in natural language!

## 📁 Project Structure

```
marketwisePS2/
├── api.py                  # FastAPI backend server
├── ui.py                   # Streamlit frontend
├── start.bat              # Easy startup script
├── requirements.txt       # Dependencies
├── .env                   # Environment configuration
│
├── db/                    # Database utilities
│   ├── executor.py        # SQL execution
│   ├── validator.py       # DB validation
│   └── schema_extractor.py # Schema analysis
│
├── llm/                   # LLM integration
│   ├── client.py          # Groq client
│   ├── sql_generator.py   # SQL generation
│   └── self_correction.py # Error correction
│
├── nlp/                   # Natural language processing
│   ├── ambiguity_detector.py
│   ├── context_builder.py
│   ├── planner.py
│   └── suggestion_generator.py
│
├── validation/            # SQL validation
│   └── sql_validator.py
│
└── response/             # Response generation
    ├── interpreter.py
    └── answer_generator.py
```

## 🎯 Usage Examples

### Simple Queries
- "How many customers do we have?"
- "Show me all products"
- "What's the total sales?"

### Complex Queries
- "Which customers bought both product A and product B?"
- "Show top 10 customers by revenue"
- "List products that were never purchased"

### Meta Queries
- "What tables are in this database?"
- "Show me the schema for the customers table"
- "What columns does the orders table have?"

## 🔧 Troubleshooting

### API Not Connecting
1. Make sure the API server is running: `uvicorn api:app --reload`
2. Check that port 8000 is not in use
3. Verify `.env` file exists with valid GROQ_API_KEY

### SQL Errors
- The system automatically retries with corrections
- Check the "View Retry Attempts" expander to see what went wrong
- Verify your database schema is valid

### UI Not Loading
1. Install all dependencies: `pip install -r requirements.txt`
2. Make sure Streamlit is installed: `pip install streamlit`
3. Run: `streamlit run ui.py`

## 🎨 Features Breakdown

### Beautiful UI
- Animated gradient backgrounds
- Glassmorphism design
- Smooth hover effects
- Custom scrollbars
- Premium typography

### Smart Error Handling
- Syntax error detection
- Reserved word conflicts
- Missing columns/tables
- Automatic query regeneration
- Up to 2 retries per query

### Chat Features
- Message history
- Multiple chat sessions
- Auto-save conversations
- Follow-up suggestions
- Clarification questions

## 🔑 API Endpoints

- `POST /upload-db` - Upload database
- `POST /ask` - Ask a question
- `GET /health` - Health check
- `GET /schema/{session_id}` - Get schema
- `DELETE /session/{session_id}` - Delete session

## 📝 License

MIT License - Feel free to use and modify

## 🤝 Contributing

Contributions welcome! Please feel free to submit pull requests.

## 💡 Tips

1. **Better Results**: Be specific in your questions
2. **Complex Queries**: Break them into smaller questions first
3. **Database Schema**: Use meta queries to understand the structure
4. **Follow-ups**: Click suggested questions for related insights
5. **History**: Previous conversations are auto-saved

## 🆘 Support

For issues or questions:
1. Check the error messages in the UI
2. Review the retry attempts
3. Verify your database is valid SQLite
4. Ensure your GROQ_API_KEY is valid

---

**Made with ❤️ using FastAPI, Streamlit, and Groq**
