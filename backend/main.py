"""
PocketCA - AI-Powered Chartered Accountant Backend
FastAPI server providing multi-session chat, RAG-grounded tax & accounting advisory,
financial calculator tools, file ingestion, and runtime configuration.

HOW THIS FILE WORKS:
- This is the MAIN SERVER file. When you run this, it starts a web server (API).
- The frontend (website/app) sends HTTP requests to this server.
- This server processes those requests using AI (Google Gemini) and returns responses.
- Think of it like a "brain" that the frontend talks to.
"""

import os          # os = Operating System
import uuid        # uuid = (universally unique Identifier). Generates random unique IDs for chat sessions
import shutil      # shutil = Shell Utilities. Helps with file like copying uploaded files
from pathlib import Path  # Path = Makes file/folder paths easier across Windows/Mac/Linux

from typing import Dict, Any, List, Optional #typing used for type hints, ensures code readability

from dotenv import load_dotenv

# FastAPI = A modern Python framework for building web APIs quickly.
# UploadFile, File = Handle file uploads from users
# Form = Handle data from users
# HTTPException = Return error messages to the frontend (like "400 Bad Request")
from fastapi import FastAPI, UploadFile, File, Form, HTTPException

# CORSMiddleware = Allows the frontend (running on a different port/domain) to talk to this backend.
# Without this, the browser would block requests from the frontend to the backend (security feature).
from fastapi.middleware.cors import CORSMiddleware

# BaseModel = A Pydantic class that validates incoming data automatically.
# When a user sends JSON data, Pydantic checks that it has the right fields and types.
# Field = Lets us set default values and validation rules for model fields.
from pydantic import BaseModel, Field

# Our own custom files (in the same backend/ folder):
from prompts import SYSTEM_PROMPT, RAG_CONTEXT_TEMPLATE  # AI instructions & prompt templates
from rag import rag_engine, DATA_DIR, UPLOADS_DIR         # Knowledge base search engine
import tools  # Financial calculator functions (GST, Tax, TDS, EMI, etc.)

# =====================================================================
# 1. ENVIRONMENT & INITIALIZATION
# =====================================================================
# This section loads configuration and starts up the server.

# Find the .env file in the same folder as this script
env_path = Path(__file__).parent / ".env"
# Load the .env file — this reads GOOGLE_API_KEY from the file and puts it into os.environ
load_dotenv(dotenv_path=env_path)

# Read the API key from environment variables.
# We check two possible names because users might set either one.
# Optional[str] means: this could be a string OR None (if no key is set).
API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

# Initialize the RAG (Retrieval-Augmented Generation) knowledge base.
# If we have an API key, tell the RAG engine so it can use Google's AI for better search.
if API_KEY:
    rag_engine.set_api_key(API_KEY)
# Load and index all PDF/text documents from the data/ folder
rag_engine.initialize()

# Create the FastAPI application — this is the web server object.
# Everything below (routes, middleware) gets attached to this 'app'.
app = FastAPI(
    title="PocketCA Backend",
    description="AI-Powered Chartered Accountant Assistant & Tax Advisory API",
    version="2.0.0"
)

# CORS Middleware Setup:
# CORS = Cross-Origin Resource Sharing
# When your frontend runs on http://localhost:3000 and backend on http://localhost:8000,
# the browser blocks requests between them by default (security feature).
# This middleware tells the browser: "It's okay, allow requests from any origin."
# allow_origins=["*"] means "accept requests from ANY website" (use specific URLs in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Which websites can access this API
    allow_credentials=True,       # Allow cookies and authentication headers
    allow_methods=["*"],          # Allow all HTTP methods (GET, POST, DELETE, etc.)
    allow_headers=["*"],          # Allow all HTTP headers
)


# =====================================================================
# 2. SESSION & MEMORY STORE
# =====================================================================
# Sessions let the AI remember previous messages in a conversation.
# Each user gets a unique "session_id" so their chat history stays separate.

class ChatMessage(BaseModel):
    """
    Represents a single message in a chat conversation.
    
    - role: Who sent the message — "user" (the human) or "assistant" (the AI)
    - content: The actual text of the message
    - sources: Optional list of knowledge base references used (e.g., "gst.pdf (Page 2)")
    """
    role: str  # "user" or "assistant"
    content: str
    sources: Optional[List[str]] = None  # None means no sources were used


class SessionManager:
    """
    Manages conversational context per session ID, stored in-memory (RAM).
    
    WHY WE NEED THIS:
    Without sessions, the AI would forget everything after each message.
    The SessionManager stores the last few messages so the AI can reference 
    previous conversation context (like "what did I ask earlier?").
    
    NOTE: Since this is stored in RAM, all chat history is lost when the server restarts.
    For production, you'd use a database like Redis or PostgreSQL.
    """
    def __init__(self):
        # Dictionary mapping session_id -> list of ChatMessages
        # Example: {"abc-123": [ChatMessage(role="user", content="What is GST?"), ...]}
        self.sessions: Dict[str, List[ChatMessage]] = {}

    def get_history(self, session_id: str) -> List[ChatMessage]:
        """Retrieve all stored messages for a given session. Returns empty list if session doesn't exist."""
        return self.sessions.get(session_id, [])

    def add_message(self, session_id: str, role: str, content: str, sources: Optional[List[str]] = None):
        """
        Add a new message to a session's history.
        Automatically creates a new session if the session_id doesn't exist yet.
        Keeps only the last 12 messages to prevent memory from growing too large.
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(ChatMessage(role=role, content=content, sources=sources))
        # Memory limit: Keep only the last 12 messages (6 user + 6 assistant pairs)
        # This prevents the conversation context from getting too long for the AI model
        if len(self.sessions[session_id]) > 12:
            self.sessions[session_id] = self.sessions[session_id][-12:]

    def clear(self, session_id: str):
        """Delete all messages for a session (used when user wants to start fresh)."""
        if session_id in self.sessions:
            del self.sessions[session_id]


# Create a single SessionManager instance that the entire app shares
session_mgr = SessionManager()


# =====================================================================
# 3. LLM CLIENT HELPER
# =====================================================================
# LLM = Large Language Model (the AI brain, in this case Google Gemini).
# These functions handle connecting to the AI model and generating responses.

# Active Google Gemini models (tried in priority order)
AVAILABLE_GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-flash-latest",
    "gemini-pro-latest",
]

def invoke_gemini_with_fallback(messages: list) -> str:
    """
    Invokes Google Gemini AI with automatic fallback across active models.
    Tries gemini-3.8-flash -> gemini-3.6-flash -> gemini-flash-latest -> gemini-pro-latest.
    """
    global API_KEY
    if not API_KEY:
        raise ValueError("No Gemini API key configured.")

    from langchain_google_genai import ChatGoogleGenerativeAI

    last_error = None
    for model_name in AVAILABLE_GEMINI_MODELS:
        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                api_key=API_KEY,
                temperature=0.2,
            )
            response = llm.invoke(messages)
            if isinstance(response.content, list):
                parts = [item.get("text", "") if isinstance(item, dict) else str(item) for item in response.content]
                return "".join(parts)
            return str(response.content)
        except Exception as e:
            print(f"Model '{model_name}' invocation error: {e}")
            last_error = e
            continue

    raise last_error or RuntimeError("All Gemini models failed.")


def get_llm():
    """Returns True if API_KEY is present for AI generation."""
    global API_KEY
    return bool(API_KEY)


def generate_offline_answer(question: str, rag_results: List[Dict[str, Any]]) -> str:
    """
    Fallback answer generator when Google API key is NOT configured (offline mode).
    
    Instead of using AI, this function:
    1. Checks if the knowledge base (PDFs) has relevant information
    2. If yes, shows those snippets directly to the user
    3. If no, shows a generic "here's what I can help with" message
    
    This ensures the app is still useful even without an internet connection or API key.
    """
    q_lower = question.lower()

    # If the RAG engine found matching text in the knowledge base PDFs
    if rag_results:
        # Format each result as a readable snippet with its source reference
        snippets = "\n\n".join([f"**From {r['source']} (Page {r['page']}):**\n{r['text']}" for r in rag_results])
        return (
            f"### Pocket C.A. Knowledge Base Advisory\n\n"
            f"Here is the relevant statutory reference matching your inquiry:\n\n"
            f"{snippets}"
        )

    # No knowledge base matches found — show a general help message
    return (
        "### Pocket C.A. Assistant\n\n"
        "I am ready to help you with:\n"
        "• **GST:** Rate slabs (0%, 5%, 12%, 18%, 28%), Input Tax Credit (ITC) conditions, RCM rules\n"
        "• **Income Tax:** Old vs New Tax Regime comparisons (FY 2024-25 / FY 2025-26)\n"
        "• **TDS:** Sections 194C, 194J, 194I, 194H, 194Q\n"
        "• **Accounting:** Golden rules, double-entry journal entries, Balance Sheet & P&L\n"
        "• **Calculators:** Click on the **Financial Calculators** tab in the sidebar for instant audit-ready computations."
    )


# =====================================================================
# 4. REQUEST / RESPONSE MODELS
# =====================================================================
# These classes define the SHAPE of data coming IN (requests) and going OUT (responses).
# Pydantic automatically validates the data — if a required field is missing or wrong type,
# the API returns a clear error message like "field 'amount' is required".

class ChatRequest(BaseModel):
    """What the frontend sends when the user asks a question."""
    question: str                          # The user's question text (required)
    session_id: Optional[str] = None       # Which conversation this belongs to (auto-generated if not sent)
    use_rag: bool = True                   # Whether to search the knowledge base for context (default: yes)


class ChatResponse(BaseModel):
    """What this API sends back after processing the user's question."""
    answer: str                            # The AI-generated or knowledge-base answer
    session_id: str                        # The session ID (so frontend can continue the conversation)
    sources: List[str] = Field(default_factory=list)  # List of knowledge base sources used


class ApiKeyRequest(BaseModel):
    """What the frontend sends when the user configures their API key."""
    api_key: str                           # The Google Gemini API key string


# --- Calculator Request Models ---
# Each calculator endpoint has its own model defining what input it needs.

class GstRequest(BaseModel):
    """Input for GST Calculator."""
    amount: float                          # The bill amount in ₹
    rate: float = 18.0                     # GST rate percentage (default 18%)
    tax_type: str = "exclusive"            # "exclusive" (GST added on top) or "inclusive" (GST already in price)
    is_interstate: bool = False            # True = IGST (different states), False = CGST+SGST (same state)


class TaxRequest(BaseModel):
    """Input for Income Tax Calculator (compares Old vs New regime)."""
    gross_income: float                    # Total annual income before any deductions
    financial_year: str = "2024-25"        # Which FY's tax slabs to use
    deductions_80c: float = 0.0            # Deductions under Sec 80C (PPF, ELSS, LIC, etc.) — max ₹1.5L
    deductions_80d: float = 0.0            # Deductions under Sec 80D (Health insurance premium)
    other_deductions: float = 0.0          # Any other deductions (80G donations, etc.)
    is_senior_citizen: bool = False        # Senior citizens (60-80 yrs) get higher exemption limit


class TdsRequest(BaseModel):
    """Input for TDS Calculator."""
    section: str = "194J"                  # Which TDS section (194C, 194J, 194I, 194H, 194Q, 194A)
    amount: float                          # The bill/payment amount in ₹
    pan_available: bool = True             # Does the payee have a PAN card? (No PAN = higher TDS rate)
    payee_type: str = "individual"         # Type of payee: "individual", "company", "technical", etc.


class EmiRequest(BaseModel):
    """Input for Loan EMI Calculator."""
    principal: float                       # Loan amount in ₹
    annual_rate: float                     # Annual interest rate in % (e.g., 8.5)
    tenure_months: int                     # Loan duration in months (e.g., 240 for 20 years)


class HraRequest(BaseModel):
    """Input for HRA (House Rent Allowance) Exemption Calculator."""
    basic_salary: float                    # Annual basic salary in ₹
    da: float = 0.0                        # Dearness Allowance (part of salary)
    hra_received: float = 0.0              # Actual HRA received from employer per year
    rent_paid: float = 0.0                 # Actual rent paid per year
    is_metro: bool = False                 # True if living in Delhi/Mumbai/Kolkata/Chennai (50% vs 40% rule)


class DeprRequest(BaseModel):
    """Input for Depreciation Calculator."""
    cost: float                            # Original cost of the asset in ₹
    salvage_value: float = 0.0             # Expected value at end of useful life (scrap value)
    useful_life_years: int = 5             # How many years the asset will be used
    method: str = "SLM"                    # "SLM" (Straight Line) or "WDV" (Written Down Value)
    rate_percent: Optional[float] = None   # Custom depreciation rate (auto-calculated if not provided)


class JournalRequest(BaseModel):
    """Input for Journal Entry Generator."""
    transaction_description: str           # What the transaction is about (e.g., "Purchased furniture")
    amount: float                          # Transaction amount in ₹
    debit_account: str                     # Account to debit (e.g., "Furniture")
    credit_account: str                    # Account to credit (e.g., "Cash" or "Bank")
    narration: Optional[str] = None        # Optional narration text (auto-generated if not provided)


# =====================================================================
# 5. CORE API ENDPOINTS
# =====================================================================
# Endpoints are URLs that the frontend can call. Each one does something specific.
# Decorators like @app.get("/") and @app.post("/chat") map URLs to Python functions.

@app.get("/")
def home():
    """
    HEALTH CHECK ENDPOINT — GET /
    
    The frontend calls this to check if the server is running and what features are available.
    Returns server status, whether API key is set, knowledge base stats, and available tools.
    
    Example: Frontend checks this on startup to show "Connected" or "Offline" status.
    """
    return {
        "status": "PocketCA Running",
        "version": "2.0.0",
        "api_key_configured": bool(API_KEY),        # True if API key is set, False otherwise
        "knowledge_base": {
            "total_chunks": len(rag_engine.chunks),  # How many text chunks are indexed
            "faiss_active": rag_engine.faiss_store is not None,  # Is AI-powered search active?
            "fallback_active": True                  # Basic keyword search is always available
        },
        "available_tools": [
            "GST Calculator", "Income Tax Comparison", "TDS Calculator",
            "Loan EMI Calculator", "HRA Exemption", "Depreciation", "Journal Entry"
        ]
    }


@app.post("/config/api-key")
def configure_api_key(data: ApiKeyRequest):
    """
    API KEY CONFIGURATION — POST /config/api-key
    
    Allows the user to set or change their Google Gemini API key at runtime,
    without needing to restart the server or edit the .env file.
    
    The frontend provides a settings page where users can paste their API key.
    """
    global API_KEY  # Modify the global API_KEY variable
    cleaned_key = data.api_key.strip()  # Remove any accidental whitespace
    if not cleaned_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")

    API_KEY = cleaned_key
    rag_engine.set_api_key(API_KEY)  # Update the RAG engine so it can use AI-powered search
    return {
        "success": True,
        "message": "Google API key successfully configured. Generative AI models are now active."
    }


@app.post("/chat", response_model=ChatResponse)
def chat(data: ChatRequest):
    """
    MAIN CHAT ENDPOINT — POST /chat
    
    This is the HEART of the application. When a user sends a question:
    
    Step 1: Search the knowledge base (RAG) for relevant tax/accounting info
    Step 2: Try to get an AI model (Gemini) to answer
    Step 3: If AI is unavailable, use offline mode (knowledge base snippets only)
    
    The AI gets:
    - A system prompt (telling it to act as a Chartered Accountant)
    - Previous conversation history (for context)
    - Relevant knowledge base snippets (for accuracy)
    - The user's current question
    """
    # Generate a unique session ID if the frontend didn't provide one
    session_id = data.session_id or str(uuid.uuid4())
    question = data.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # ----- Step 1: RAG Search (find relevant info from knowledge base) -----
    sources = []       # Will hold source references like "gst.pdf (Page 2)"
    rag_context = ""   # Will hold the actual text from matched documents
    rag_results = []   # Raw search results

    if data.use_rag:
        try:
            # Search the knowledge base for the top 2 most relevant chunks
            rag_results = rag_engine.search(question, top_k=2)
            if rag_results:
                context_blocks = []
                for r in rag_results:
                    # Create a readable source label like "gst.pdf (Page 2)"
                    src_label = f"{r['source']} (Page {r['page']})"
                    if src_label not in sources:
                        sources.append(src_label)
                    context_blocks.append(f"[{src_label}]:\n{r['text']}")
                # Join all found text blocks into one context string
                rag_context = "\n\n".join(context_blocks)
        except Exception as e:
            print(f"RAG search error: {e}")  # Log but don't crash — RAG failure shouldn't break chat

    # ----- Step 2 & 3: Generate AI Response -----
    if not API_KEY:
        # NO AI KEY AVAILABLE — use offline fallback mode
        answer = generate_offline_answer(question, rag_results)
        session_mgr.add_message(session_id, "user", question)
        session_mgr.add_message(session_id, "assistant", answer, sources)
        return ChatResponse(answer=answer, session_id=session_id, sources=sources)

    try:
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        # Start with the system prompt (tells AI to act as a Chartered Accountant)
        messages = [SystemMessage(content=SYSTEM_PROMPT)]

        # Add previous conversation messages (so AI remembers what was discussed)
        history = session_mgr.get_history(session_id)
        for msg in history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            else:
                messages.append(AIMessage(content=msg.content))

        # Build the current question — if we found knowledge base context, include it
        if rag_context:
            current_prompt = RAG_CONTEXT_TEMPLATE.format(
                rag_context=rag_context,
                question=question
            )
        else:
            current_prompt = question

        messages.append(HumanMessage(content=current_prompt))

        # Invoke Gemini with multi-model fallback (gemini-3.8-flash -> 3.6-flash -> flash-latest)
        answer = invoke_gemini_with_fallback(messages)

        # Save both the question and answer to session memory for future context
        session_mgr.add_message(session_id, "user", question)
        session_mgr.add_message(session_id, "assistant", answer, sources)

        return ChatResponse(
            answer=answer,
            session_id=session_id,
            sources=sources
        )
    except Exception as e:
        # If all AI models fail, fall back to statutory knowledge base smoothly
        print(f"All LLM generation attempts failed: {e}")
        answer = generate_offline_answer(question, rag_results)
        session_mgr.add_message(session_id, "user", question)
        session_mgr.add_message(session_id, "assistant", answer, sources)
        return ChatResponse(
            answer=answer,
            session_id=session_id,
            sources=sources
        )


@app.get("/history/{session_id}")
def get_history(session_id: str):
    """
    GET CHAT HISTORY — GET /history/{session_id}
    
    Returns all stored messages for a given session.
    The frontend uses this to restore a previous conversation when the user comes back.
    """
    return {
        "session_id": session_id,
        "messages": [m.dict() for m in session_mgr.get_history(session_id)]
    }


@app.delete("/history/{session_id}")
def clear_history(session_id: str):
    """
    CLEAR CHAT HISTORY — DELETE /history/{session_id}
    
    Deletes all messages in a session. Used when the user clicks "New Chat" or "Clear History".
    """
    session_mgr.clear(session_id)
    return {"success": True, "message": f"Session {session_id} cleared."}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    DOCUMENT UPLOAD — POST /upload
    
    Allows users to upload their own PDF, TXT, MD, or CSV files.
    The uploaded document gets:
    1. Saved to the data/uploads/ folder
    2. Indexed into the knowledge base (RAG engine)
    3. Available for the AI to reference when answering future questions
    
    Example: A user uploads their company's "TDS Policy.pdf" — now the AI can answer
    questions about their specific TDS policy, not just general TDS rules.
    
    'async def' is used here because file uploads involve waiting for data transfer,
    and async allows the server to handle other requests while waiting.
    """
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    # Only allow specific file types (security measure — don't accept .exe, .py, etc.)
    allowed_exts = [".pdf", ".txt", ".md", ".csv"]
    file_ext = Path(filename).suffix.lower()
    if file_ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported formats: {', '.join(allowed_exts)}"
        )

    # Save the uploaded file to disk
    saved_path = UPLOADS_DIR / filename
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)  # Copy uploaded file data to the saved path

    # Index the file into the knowledge base so the AI can search it
    ingest_result = rag_engine.ingest_file(saved_path)

    return {
        "success": True,
        "filename": filename,
        "details": ingest_result,
        "message": f"Document '{filename}' successfully uploaded and indexed for consultation."
    }


# =====================================================================
# 6. CA FINANCIAL CALCULATOR ENDPOINTS
# =====================================================================
# These endpoints connect the frontend's calculator forms to the actual
# calculation functions in tools.py. Each endpoint:
# 1. Receives input data from the frontend (validated by Pydantic models above)
# 2. Calls the corresponding function in tools.py
# 3. Returns the calculation results as JSON

@app.get("/tools")
def list_tools():
    """
    LIST ALL CALCULATORS — GET /tools
    
    Returns a list of all available financial calculators.
    The frontend uses this to build the calculator menu/sidebar.
    """
    return {
        "tools": [
            {"id": "gst", "name": "GST Calculator", "endpoint": "/tools/gst"},
            {"id": "tax", "name": "Income Tax (Old vs New)", "endpoint": "/tools/tax"},
            {"id": "tds", "name": "TDS Calculator", "endpoint": "/tools/tds"},
            {"id": "emi", "name": "Loan EMI Calculator", "endpoint": "/tools/emi"},
            {"id": "hra", "name": "HRA Exemption Calculator", "endpoint": "/tools/hra"},
            {"id": "depreciation", "name": "Depreciation Calculator", "endpoint": "/tools/depreciation"},
            {"id": "journal", "name": "Journal Entry Generator", "endpoint": "/tools/journal"}
        ]
    }


@app.post("/tools/gst")
def calculate_gst_endpoint(data: GstRequest):
    """GST CALCULATOR — POST /tools/gst — Calculates CGST/SGST/IGST breakdown."""
    return tools.calculate_gst(
        amount=data.amount,
        rate=data.rate,
        tax_type=data.tax_type,
        is_interstate=data.is_interstate
    )


@app.post("/tools/tax")
def calculate_tax_endpoint(data: TaxRequest):
    """INCOME TAX — POST /tools/tax — Compares Old vs New tax regime and recommends the better one."""
    return tools.calculate_income_tax(
        gross_income=data.gross_income,
        financial_year=data.financial_year,
        deductions_80c=data.deductions_80c,
        deductions_80d=data.deductions_80d,
        other_deductions=data.other_deductions,
        is_senior_citizen=data.is_senior_citizen
    )


@app.post("/tools/tds")
def calculate_tds_endpoint(data: TdsRequest):
    """TDS CALCULATOR — POST /tools/tds — Calculates TDS deduction for various sections."""
    return tools.calculate_tds(
        section=data.section,
        amount=data.amount,
        pan_available=data.pan_available,
        payee_type=data.payee_type
    )


@app.post("/tools/emi")
def calculate_emi_endpoint(data: EmiRequest):
    """LOAN EMI — POST /tools/emi — Calculates monthly EMI, total interest, and repayment."""
    return tools.calculate_emi(
        principal=data.principal,
        annual_rate=data.annual_rate,
        tenure_months=data.tenure_months
    )


@app.post("/tools/hra")
def calculate_hra_endpoint(data: HraRequest):
    """HRA EXEMPTION — POST /tools/hra — Calculates tax-exempt HRA under Section 10(13A)."""
    return tools.calculate_hra_exemption(
        basic_salary=data.basic_salary,
        da=data.da,
        hra_received=data.hra_received,
        rent_paid=data.rent_paid,
        is_metro=data.is_metro
    )


@app.post("/tools/depreciation")
def calculate_depreciation_endpoint(data: DeprRequest):
    """DEPRECIATION — POST /tools/depreciation — Generates year-by-year depreciation schedule."""
    return tools.calculate_depreciation(
        cost=data.cost,
        salvage_value=data.salvage_value,
        useful_life_years=data.useful_life_years,
        method=data.method,
        rate_percent=data.rate_percent
    )


@app.post("/tools/journal")
def generate_journal_endpoint(data: JournalRequest):
    """JOURNAL ENTRY — POST /tools/journal — Generates a formatted double-entry bookkeeping entry."""
    return tools.generate_journal_entry(
        transaction_description=data.transaction_description,
        amount=data.amount,
        debit_account=data.debit_account,
        credit_account=data.credit_account,
        narration=data.narration
    )


# =====================================================================
# 7. SERVER STARTUP
# =====================================================================
# This block runs ONLY when you execute this file directly (python main.py).
# It does NOT run when the file is imported by another script.

if __name__ == "__main__":
    import uvicorn  # Uvicorn = A fast ASGI web server for running FastAPI apps
    # Read port from environment variable (Render sets this automatically)
    # Falls back to 8000 for local development
    port = int(os.environ.get("PORT", 8000))
    # host="0.0.0.0" allows external connections (required for cloud deployment)
    # For local-only access, you can change this to "127.0.0.1"
    uvicorn.run(app, host="0.0.0.0", port=port)