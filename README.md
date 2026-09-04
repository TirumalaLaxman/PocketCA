# Pocket C.A. - AI-Powered Chartered Accountant & Tax Advisory

**Pocket C.A.** is a production-ready, full-stack AI financial platform tailored for Indian Accounting Standards (Ind AS), Direct Taxation (Income Tax Act 1961), and Indirect Taxation (GST Act 2017).

It provides intelligent multi-turn conversational advisory, Retrieval-Augmented Generation (RAG) over statutory reference documents, interactive audit-ready financial calculators, dynamic document ingestion (invoices, balance sheets), and session management.

---

## 🚀 Key Features

### 1. 🤖 AI Chartered Accountant Advisory
- **Multi-Turn Session Memory**: Each consultation maintains independent conversation context and message history.
- **RAG Grounding**: Queries automatically search and retrieve statutory context from authoritative knowledge base documents (`accounting.pdf`, `gst.pdf`).
- **Citation Badges**: Answers cite statutory references (e.g. `[gst.pdf, Page 1]`, `[accounting.pdf, Page 2]`).
- **Graceful Fallback**: Functions seamlessly in both online mode (via Google Gemini) and offline mode (via local BM25 knowledge search and deterministic tools).

### 2. 🧮 Interactive Financial Calculators
- **GST Calculator**: Computes CGST, SGST, IGST, taxable values, and invoice totals for both tax-exclusive and tax-inclusive transactions across standard rate slabs (0%, 5%, 12%, 18%, 28%).
- **Income Tax Regime Comparison (FY 2024-25 / FY 2025-26)**: Side-by-side analysis of the New Tax Regime (Section 115BAC) vs Old Tax Regime, factoring in Standard Deduction (₹75,000 New / ₹50,000 Old), Section 87A rebate, and 4% Cess with optimal regime recommendation.
- **TDS Calculator**: Computes statutory withholding tax under Sections 194C, 194J, 194I, 194H, 194Q, 194A, and enforces Section 206AA (20% rate) when PAN is missing.
- **Loan EMI Calculator**: Calculates monthly equated installments, total interest outgo, and overall repayment schedule.
- **HRA Exemption Calculator**: Computes Section 10(13A) 3-rule exemption and taxable HRA for metro and non-metro locations.
- **Depreciation Calculator**: Computes asset write-down schedules under Straight Line Method (SLM) and Written Down Value (WDV - Section 32).
- **Double-Entry Journal Generator**: Produces formatted debit/credit journal entries with narration.

### 3. 📄 Document Upload & Ingestion
- Upload financial statements, invoices, and audit notes (PDF, TXT, CSV) via the drag-and-drop dropzone or attachment button to index them dynamically into the RAG vector store for instant analysis.

### 4. 💻 Modern CA Dashboard UI
- High-contrast financial dark theme with emerald and royal blue accents.
- Full Markdown support (tables, lists, bolding, code/journal blocks).
- Multi-session consultation sidebar with conversation export (`.md`).
- Quick inquiry suggestion chips.
- Interactive calculator drawer with direct "Send to Chat" functionality.
- In-app Google Gemini API Key configuration modal.

---

## 🛠️ Project Structure

```
PocketCA/
├── backend/
│   ├── main.py              # FastAPI server, session management, endpoints
│   ├── prompts.py           # CA system instructions & RAG templates
│   ├── rag.py               # Document loading, chunking, FAISS & BM25 engine
│   ├── tools.py             # Deterministic CA financial calculators
│   ├── requirements.txt     # Python dependencies
│   └── vector_store/        # FAISS vector store cache (auto-generated)
├── data/
│   ├── accounting.pdf       # Reference manual: Accounting & Ind AS
│   ├── gst.pdf              # Reference manual: Indian GST Regulations
│   └── uploads/             # User-uploaded documents (auto-created)
├── frontend/
│   ├── index.html           # Professional CA workspace dashboard
│   ├── script.js            # Client logic, chat, session, calculators, upload
│   └── style.css            # Dark mode financial theme & responsive layout
└── README.md
```

---

## ⚡ Quick Start Guide

### Prerequisites
- Python 3.10+ (Python 3.14 fully supported)
- Google Gemini API Key (optional for basic calculators; required for generative AI chat)

### 1. Install Backend Dependencies
```bash
cd backend
python -m pip install -r requirements.txt
```

### 2. Configure API Key (Optional)
Create a `.env` file in `backend/`:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```
*(Alternatively, you can click the **Settings** gear icon in the frontend UI to enter your API key directly at runtime).*

### 3. Launch Backend Server
```bash
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
FastAPI documentation will be accessible at: `http://127.0.0.1:8000/docs`.

### 4. Launch Frontend
Open `frontend/index.html` in any web browser, or serve it with Python:
```bash
cd frontend
python -m http.server 3000
```
Navigate to `http://localhost:3000` in your browser.

---

## 🧪 Running Automated Tests

To run the end-to-end verification suite testing all tools, RAG search, and FastAPI endpoints:
```bash
$env:PYTHONIOENCODING="utf-8"
python scratch/test_pocketca.py
```

---

## 📜 API Endpoints Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | System status, knowledge base metrics, and tool list |
| `POST` | `/chat` | Multi-turn conversational consultation with RAG context |
| `GET` | `/history/{session_id}` | Retrieve message history for a consultation session |
| `DELETE` | `/history/{session_id}` | Clear message history for a session |
| `POST` | `/upload` | Upload PDF/TXT/CSV financial file to RAG knowledge base |
| `POST` | `/config/api-key` | Set/update Google Gemini API key dynamically |
| `GET` | `/tools` | List metadata of all available CA financial calculators |
| `POST` | `/tools/gst` | Calculate GST with inclusive/exclusive & CGST/SGST/IGST splits |
| `POST` | `/tools/tax` | Compare Income Tax liabilities (Old vs New Regime) |
| `POST` | `/tools/tds` | Calculate TDS rates, threshold checks, and Section 206AA |
| `POST` | `/tools/emi` | Calculate monthly loan EMI and total interest |
| `POST` | `/tools/hra` | Calculate Section 10(13A) exempt & taxable HRA |
| `POST` | `/tools/depreciation` | Generate SLM / WDV asset amortization schedule |
| `POST` | `/tools/journal` | Format audit-ready double-entry journal entry |
