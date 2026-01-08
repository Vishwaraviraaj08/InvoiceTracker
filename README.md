# backend/.env


# Groq API Configuration
GROQ_API_KEY=<YOUR_GROQ_API_KEY>


# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=invoice_manager

# Application Settings
DEBUG=true
LOG_LEVEL=INFO

# Embedding Model (runs locally via sentence-transformers)
EMBEDDING_MODEL=all-MiniLM-L6-v2


# Invoice Manager - Production-Grade AI System

A full-stack, enterprise-grade Invoice Manager application leveraging modern AI orchestration (LangChain/LangGraph), RAG-based document querying, MCP servers for modular tool execution, and a React TypeScript frontend.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    React Frontend (TypeScript)                   │
│         Dashboard │ Documents │ Global Chat │ Doc Chat          │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  /upload-invoice │ /documents │ /validate │ /chat/global        │
└─────────────────────────────────────────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   LangGraph      │  │   MCP Servers    │  │   MongoDB        │
│   Agent          │  │  ─────────────   │  │  ───────────     │
│  ─────────────   │  │  • Validation    │  │  • documents     │
│  • Intent Node   │  │  • RAG Query     │  │  • embeddings    │
│  • Tool Router   │  │  • Chat History  │  │  • chats         │
│  • Fallback      │  │  • Doc Listing   │  │  • validations   │
└──────────────────┘  └──────────────────┘  └──────────────────┘
              │                  │
              ▼                  ▼
┌──────────────────────────────────────────┐
│           Groq LLM Pool (Load Balanced)  │
│   llama3-70b │ mixtral-8x7b │ llama3-8b  │
└──────────────────────────────────────────┘
```

## ✨ Features

- **Invoice Upload & Validation** - Upload PDF/image/text invoices with AI-powered validation
- **Per-Document RAG** - Ask questions about specific invoices using vector search
- **Global Chatbot** - LangGraph-orchestrated agent for invoice management
- **MCP Servers** - Modular, structured tools for each capability
- **Model Rotation** - Load distribution across Groq models with fallback

## 📁 Project Structure

```
AgenticAI_FA3/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Environment configuration
│   │   ├── api/routes/          # API endpoints
│   │   ├── core/
│   │   │   ├── llm/             # Groq client with rotation
│   │   │   ├── langchain/       # Tools, RAG, embeddings
│   │   │   └── langgraph/       # Agent orchestration
│   │   ├── mcp/                 # MCP servers
│   │   ├── db/                  # MongoDB models & repos
│   │   ├── services/            # Business logic
│   │   └── utils/               # Text extraction
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/
    ├── src/
    │   ├── components/          # Reusable UI components
    │   ├── pages/               # Page components
    │   ├── services/            # API client
    │   └── types/               # TypeScript interfaces
    └── package.json
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB (running locally or connection string)
- Groq API Key

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and add your GROQ_API_KEY

# Run server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload-invoice` | Upload invoice file |
| GET | `/api/documents` | List all invoices |
| GET | `/api/documents/{id}` | Get invoice details |
| DELETE | `/api/documents/{id}` | Delete invoice |
| POST | `/api/validate-invoice/{id}` | Validate invoice |
| POST | `/api/chat/global` | Global chatbot |
| POST | `/api/chat/document/{id}` | Per-document RAG chat |
| GET | `/api/chats/global` | Get global chat history |
| GET | `/api/chats/document/{id}` | Get document chat history |

## 🤖 LangGraph Agent

The agent uses conditional routing based on intent classification:

```
User Message → Intent Classification
                      │
    ┌─────────────────┼─────────────────┐
    ↓                 ↓                 ↓
Validate         RAG Query         List Docs
    │                 │                 │
    └────────────────┼─────────────────┘
                      ↓
              Response/Fallback
```

**Supported Intents:**
- `validate_invoice` - Validate document correctness
- `query_document` - RAG query on specific invoice
- `list_documents` - List all invoices
- `get_document_details` - Get invoice metadata
- `general_chat` - General conversation

## 🔧 MCP Servers

| Server | Tools | Purpose |
|--------|-------|---------|
| `validation_server` | `validate_invoice`, `get_validation_rules` | Invoice validation |
| `rag_server` | `query_document`, `get_document_context` | Per-document RAG |
| `chat_server` | `get_chat_history`, `save_message` | Chat persistence |
| `document_server` | `list_documents`, `get_document_metadata` | Document CRUD |

## 💬 Example Prompts

**Global Chat:**
- "List all my invoices"
- "Validate invoice XYZ"
- "Which invoices are pending validation?"
- "Help me understand invoice management"

**Document Chat (RAG):**
- "What is the total amount?"
- "Who is the vendor?"
- "Is tax included?"
- "Summarize this invoice"

## 🛠️ Technology Stack

- **Backend**: FastAPI, LangChain, LangGraph, MongoDB, Groq
- **Frontend**: React 19, TypeScript, Bootstrap 5
- **AI/ML**: sentence-transformers, FAISS, Groq LLMs
- **Document Processing**: pypdf, pdfplumber, Pillow

## 📝 License

MIT License
