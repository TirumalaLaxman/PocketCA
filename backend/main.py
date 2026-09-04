"""
PocketCA - AI-Powered Chartered Accountant Backend
FastAPI server providing multi-session chat, RAG-grounded tax & accounting advisory,
financial calculator tools, file ingestion, and runtime configuration.
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from prompts import SYSTEM_PROMPT, RAG_CONTEXT_TEMPLATE
from rag import rag_engine, DATA_DIR, UPLOADS_DIR
import tools

# ----------------------------------------------------------------------
# 1. Environment & Initialization
# ----------------------------------------------------------------------
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

# Initialize RAG with knowledge base
if API_KEY:
    rag_engine.set_api_key(API_KEY)
rag_engine.initialize()

app = FastAPI(
    title="PocketCA Backend",
    description="AI-Powered Chartered Accountant Assistant & Tax Advisory API",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------------
# 2. Session & Memory Store
# ----------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    sources: Optional[List[str]] = None


class SessionManager:
    """Manages conversational context per session ID in-memory."""
    def __init__(self):
        self.sessions: Dict[str, List[ChatMessage]] = {}

    def get_history(self, session_id: str) -> List[ChatMessage]:
        return self.sessions.get(session_id, [])

    def add_message(self, session_id: str, role: str, content: str, sources: Optional[List[str]] = None):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(ChatMessage(role=role, content=content, sources=sources))
        # Keep last 12 messages for conversation context
        if len(self.sessions[session_id]) > 12:
            self.sessions[session_id] = self.sessions[session_id][-12:]

    def clear(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]


session_mgr = SessionManager()


# ----------------------------------------------------------------------
# 3. LLM Client Helper
# ----------------------------------------------------------------------
def get_llm():
    global API_KEY
    if not API_KEY:
        return None

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        # Active Google Gemini models
        for model_name in ["gemini-3.6-flash", "gemini-3.8-flash", "gemini-3.5-flash"]:
            try:
                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    api_key=API_KEY,
                    temperature=0.2,
                )
                return llm
            except Exception:
                continue
        return None
    except Exception as e:
        print(f"Error initializing ChatGoogleGenerativeAI: {e}")
        return None


def generate_offline_answer(question: str, rag_results: List[Dict[str, Any]]) -> str:
    """
    Fallback reasoning engine when GOOGLE_API_KEY is not configured.
    Provides answers from the knowledge base and guides the user.
    """
    q_lower = question.lower()

    # If RAG found strong matches in knowledge base
    if rag_results:
        snippets = "\n\n".join([f"**From {r['source']} (Page {r['page']}):**\n{r['text']}" for r in rag_results])
        return (
            f"### Pocket C.A. Knowledge Base Advisory\n\n"
            f"Here is the relevant statutory reference matching your inquiry:\n\n"
            f"{snippets}"
        )

    # General offline guidance
    return (
        "### Pocket C.A. Assistant\n\n"
        "I am ready to help you with:\n"
        "• **GST:** Rate slabs (0%, 5%, 12%, 18%, 28%), Input Tax Credit (ITC) conditions, RCM rules\n"
        "• **Income Tax:** Old vs New Tax Regime comparisons (FY 2024-25 / FY 2025-26)\n"
        "• **TDS:** Sections 194C, 194J, 194I, 194H, 194Q\n"
        "• **Accounting:** Golden rules, double-entry journal entries, Balance Sheet & P&L\n"
        "• **Calculators:** Click on the **Financial Calculators** tab in the sidebar for instant audit-ready computations."
    )


# ----------------------------------------------------------------------
# 4. Request / Response Models
# ----------------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    use_rag: bool = True


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    sources: List[str] = Field(default_factory=list)


class ApiKeyRequest(BaseModel):
    api_key: str


class GstRequest(BaseModel):
    amount: float
    rate: float = 18.0
    tax_type: str = "exclusive"
    is_interstate: bool = False


class TaxRequest(BaseModel):
    gross_income: float
    financial_year: str = "2024-25"
    deductions_80c: float = 0.0
    deductions_80d: float = 0.0
    other_deductions: float = 0.0
    is_senior_citizen: bool = False


class TdsRequest(BaseModel):
    section: str = "194J"
    amount: float
    pan_available: bool = True
    payee_type: str = "individual"


class EmiRequest(BaseModel):
    principal: float
    annual_rate: float
    tenure_months: int


class HraRequest(BaseModel):
    basic_salary: float
    da: float = 0.0
    hra_received: float = 0.0
    rent_paid: float = 0.0
    is_metro: bool = False


class DeprRequest(BaseModel):
    cost: float
    salvage_value: float = 0.0
    useful_life_years: int = 5
    method: str = "SLM"
    rate_percent: Optional[float] = None


class JournalRequest(BaseModel):
    transaction_description: str
    amount: float
    debit_account: str
    credit_account: str
    narration: Optional[str] = None


# ----------------------------------------------------------------------
# 5. Core API Endpoints
# ----------------------------------------------------------------------
@app.get("/")
def home():
    """System health check and capability status."""
    return {
        "status": "PocketCA Running",
        "version": "2.0.0",
        "api_key_configured": bool(API_KEY),
        "knowledge_base": {
            "total_chunks": len(rag_engine.chunks),
            "faiss_active": rag_engine.faiss_store is not None,
            "fallback_active": True
        },
        "available_tools": [
            "GST Calculator", "Income Tax Comparison", "TDS Calculator",
            "Loan EMI Calculator", "HRA Exemption", "Depreciation", "Journal Entry"
        ]
    }


@app.post("/config/api-key")
def configure_api_key(data: ApiKeyRequest):
    """Set or update Google Gemini API key at runtime."""
    global API_KEY
    cleaned_key = data.api_key.strip()
    if not cleaned_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")

    API_KEY = cleaned_key
    rag_engine.set_api_key(API_KEY)
    return {
        "success": True,
        "message": "Google API key successfully configured. Generative AI models are now active."
    }


@app.post("/chat", response_model=ChatResponse)
def chat(data: ChatRequest):
    """Multi-turn conversational chat with RAG retrieval and tool awareness."""
    session_id = data.session_id or str(uuid.uuid4())
    question = data.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # 1. RAG Search
    sources = []
    rag_context = ""
    rag_results = []

    if data.use_rag:
        try:
            rag_results = rag_engine.search(question, top_k=2)
            if rag_results:
                context_blocks = []
                for r in rag_results:
                    src_label = f"{r['source']} (Page {r['page']})"
                    if src_label not in sources:
                        sources.append(src_label)
                    context_blocks.append(f"[{src_label}]:\n{r['text']}")
                rag_context = "\n\n".join(context_blocks)
        except Exception as e:
            print(f"RAG search error: {e}")

    # 2. Get LLM instance
    llm = get_llm()

    if not llm:
        # Fallback offline mode
        answer = generate_offline_answer(question, rag_results)
        session_mgr.add_message(session_id, "user", question)
        session_mgr.add_message(session_id, "assistant", answer, sources)
        return ChatResponse(answer=answer, session_id=session_id, sources=sources)

    # 3. Build messages with history and system prompt
    try:
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        messages = [SystemMessage(content=SYSTEM_PROMPT)]

        # Add prior session history
        history = session_mgr.get_history(session_id)
        for msg in history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            else:
                messages.append(AIMessage(content=msg.content))

        # Build current prompt
        if rag_context:
            current_prompt = RAG_CONTEXT_TEMPLATE.format(
                rag_context=rag_context,
                question=question
            )
        else:
            current_prompt = question

        messages.append(HumanMessage(content=current_prompt))

        # Invoke model
        response = llm.invoke(messages)
        if isinstance(response.content, list):
            parts = [item.get("text", "") if isinstance(item, dict) else str(item) for item in response.content]
            answer = "".join(parts)
        else:
            answer = str(response.content)

        # Save to memory
        session_mgr.add_message(session_id, "user", question)
        session_mgr.add_message(session_id, "assistant", answer, sources)

        return ChatResponse(
            answer=answer,
            session_id=session_id,
            sources=sources
        )
    except Exception as e:
        print(f"LLM generation error: {e}")
        # Graceful fallback
        fallback_msg = (
            f"*(Note: LLM request encountered an error: {str(e)[:100]}. Showing knowledge base reference below.)*\n\n" +
            generate_offline_answer(question, rag_results)
        )
        return ChatResponse(
            answer=fallback_msg,
            session_id=session_id,
            sources=sources
        )


@app.get("/history/{session_id}")
def get_history(session_id: str):
    """Retrieve chat history for a session."""
    return {
        "session_id": session_id,
        "messages": [m.dict() for m in session_mgr.get_history(session_id)]
    }


@app.delete("/history/{session_id}")
def clear_history(session_id: str):
    """Clear chat history for a session."""
    session_mgr.clear(session_id)
    return {"success": True, "message": f"Session {session_id} cleared."}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload PDF or text documents for dynamic RAG knowledge indexing."""
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    allowed_exts = [".pdf", ".txt", ".md", ".csv"]
    file_ext = Path(filename).suffix.lower()
    if file_ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported formats: {', '.join(allowed_exts)}"
        )

    saved_path = UPLOADS_DIR / filename
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    ingest_result = rag_engine.ingest_file(saved_path)

    return {
        "success": True,
        "filename": filename,
        "details": ingest_result,
        "message": f"Document '{filename}' successfully uploaded and indexed for consultation."
    }


# ----------------------------------------------------------------------
# 6. CA Financial Calculator Endpoints
# ----------------------------------------------------------------------
@app.get("/tools")
def list_tools():
    """List all available CA financial calculators."""
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
    return tools.calculate_gst(
        amount=data.amount,
        rate=data.rate,
        tax_type=data.tax_type,
        is_interstate=data.is_interstate
    )


@app.post("/tools/tax")
def calculate_tax_endpoint(data: TaxRequest):
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
    return tools.calculate_tds(
        section=data.section,
        amount=data.amount,
        pan_available=data.pan_available,
        payee_type=data.payee_type
    )


@app.post("/tools/emi")
def calculate_emi_endpoint(data: EmiRequest):
    return tools.calculate_emi(
        principal=data.principal,
        annual_rate=data.annual_rate,
        tenure_months=data.tenure_months
    )


@app.post("/tools/hra")
def calculate_hra_endpoint(data: HraRequest):
    return tools.calculate_hra_exemption(
        basic_salary=data.basic_salary,
        da=data.da,
        hra_received=data.hra_received,
        rent_paid=data.rent_paid,
        is_metro=data.is_metro
    )


@app.post("/tools/depreciation")
def calculate_depreciation_endpoint(data: DeprRequest):
    return tools.calculate_depreciation(
        cost=data.cost,
        salvage_value=data.salvage_value,
        useful_life_years=data.useful_life_years,
        method=data.method,
        rate_percent=data.rate_percent
    )


@app.post("/tools/journal")
def generate_journal_endpoint(data: JournalRequest):
    return tools.generate_journal_entry(
        transaction_description=data.transaction_description,
        amount=data.amount,
        debit_account=data.debit_account,
        credit_account=data.credit_account,
        narration=data.narration
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)