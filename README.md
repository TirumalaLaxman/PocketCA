# Pocket C.A. — AI-Powered Chartered Accountant & Tax Advisory

**Pocket C.A.** is a full-stack AI financial platform designed for Indian accounting, taxation, and GST use cases.

It combines **Generative AI, Retrieval-Augmented Generation (RAG), document retrieval, deterministic financial calculators, and conversational session management** into a single application.

The system is designed around Indian Accounting Standards (Ind AS), Direct Taxation (Income Tax Act 1961), and Indirect Taxation (GST Act 2017).

---

## 🚀 Key Features

### 1. 🤖 AI Chartered Accountant Advisory

* **Multi-Turn Session Memory** — Each consultation maintains independent conversation context and message history.
* **RAG Grounding** — User queries retrieve relevant context from statutory reference documents such as `accounting.pdf` and `gst.pdf`.
* **Citation Support** — AI responses can reference the source document and page used for the response.
* **Google Gemini Integration** — Uses Gemini for natural-language financial and accounting assistance.
* **Graceful Fallback** — Supports local BM25 knowledge retrieval and deterministic tools when generative AI is unavailable.

### 2. 🧮 Interactive Financial Calculators

PocketCA includes deterministic financial tools for common accounting and taxation calculations:

* **GST Calculator** — Calculates CGST, SGST, IGST, taxable values, and invoice totals.
* **Income Tax Calculator** — Compares Old and New Tax Regimes.
* **TDS Calculator** — Supports common TDS sections and PAN-related rules.
* **Loan EMI Calculator** — Calculates monthly EMI, total interest, and repayment amounts.
* **HRA Exemption Calculator** — Calculates exempt and taxable HRA.
* **Depreciation Calculator** — Supports Straight Line Method (SLM) and Written Down Value (WDV).
* **Double-Entry Journal Generator** — Generates formatted debit/credit journal entries with narration.

### 3. 📄 Document Upload & Ingestion

Users can upload financial documents such as:

* PDF
* TXT
* CSV
* Financial statements
* Invoices
* Audit notes

Uploaded documents can be processed and indexed into the retrieval system for subsequent analysis.

### 4. 💻 Modern CA Dashboard

* Professional financial dashboard interface
* Multi-session consultation sidebar
* Markdown response rendering
* Conversation export
* Quick inquiry suggestions
* Interactive financial calculator drawer
* Send calculator results directly to chat
* Runtime Google Gemini API key configuration
* Responsive interface

---

## 🧠 Tech Stack

| Category                | Technologies                           |
| ----------------------- | -------------------------------------- |
| **Programming**         | Python, JavaScript                     |
| **AI / LLM**            | Google Gemini                          |
| **RAG**                 | LangChain, FAISS, BM25                 |
| **Backend**             | FastAPI, Uvicorn                       |
| **Frontend**            | HTML5, CSS3, JavaScript                |
| **Document Processing** | PDF, TXT, CSV                          |
| **Vector Search**       | FAISS                                  |
| **Keyword Search**      | BM25                                   |
| **Database / Storage**  | Local file-based storage, vector store |
| **Testing**             | Python-based automated tests           |
| **Development Tools**   | Git, GitHub, VS Code                   |

---

## 🔄 How PocketCA Works

The core AI workflow combines document retrieval with large language model generation.

```text
                    USER QUERY
                        │
                        ▼
              ┌─────────────────┐
              │  FastAPI Backend │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ Query Processing │
              └────────┬────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
       ┌─────────────┐   ┌─────────────┐
       │    FAISS    │   │    BM25     │
       │Vector Search│   │Keyword Search│
       └──────┬──────┘   └──────┬──────┘
              │                 │
              └────────┬────────┘
                       ▼
              Relevant Documents
                       │
                       ▼
              Retrieved Context
                       │
                       ▼
              ┌─────────────────┐
              │  Google Gemini  │
              │      LLM        │
              └────────┬────────┘
                       │
                       ▼
              Grounded AI Response
                       │
                       ▼
             Citations + User Answer
```

### RAG Pipeline

PocketCA follows an end-to-end Retrieval-Augmented Generation workflow:

```text
Documents
   ↓
Document Loading
   ↓
Text Extraction
   ↓
Chunking
   ↓
Embedding / Indexing
   ↓
FAISS + BM25
   ↓
User Query
   ↓
Relevant Context Retrieval
   ↓
Prompt Construction
   ↓
Google Gemini
   ↓
Grounded Response
```

This architecture allows the application to provide responses based on the project's available reference material instead of relying entirely on the LLM's internal knowledge.

---

## 🧩 Deterministic Financial Tools

An important design decision in PocketCA is separating **financial calculations from LLM generation**.

Instead of asking the language model to perform every calculation, deterministic Python tools handle calculations such as:

```text
GST
Income Tax
TDS
EMI
HRA
Depreciation
Journal Entries
```

This approach makes numerical operations more predictable and allows the LLM to focus primarily on **reasoning, explanation, and conversational interaction**.

---

## 📄 Dynamic Document Ingestion

PocketCA supports adding new documents to the knowledge base.

```text
User Uploads Document
        ↓
Document Validation
        ↓
Text Extraction
        ↓
Text Chunking
        ↓
Indexing
        ↓
FAISS / BM25
        ↓
Available for Future Queries
```

This allows the retrieval system to be extended with additional accounting, tax, GST, invoice, or financial documents.

---

## 🏗️ Project Structure

```text
PocketCA/
│
├── backend/
│   ├── main.py
│   │   └── FastAPI server, sessions, API endpoints
│   │
│   ├── prompts.py
│   │   └── AI system prompts and RAG templates
│   │
│   ├── rag.py
│   │   └── Document loading, chunking, FAISS and BM25 retrieval
│   │
│   ├── tools.py
│   │   └── Deterministic financial calculators
│   │
│   ├── requirements.txt
│   │   └── Python dependencies
│   │
│   └── vector_store/
│       └── Generated vector store cache
│
├── data/
│   ├── accounting.pdf
│   │   └── Accounting / Ind AS reference material
│   │
│   ├── gst.pdf
│   │   └── GST reference material
│   │
│   └── uploads/
│       └── User-uploaded documents
│
├── frontend/
│   ├── index.html
│   │   └── Dashboard interface
│   │
│   ├── script.js
│   │   └── Chat, sessions, calculators and uploads
│   │
│   └── style.css
│       └── UI styling and responsive layout
│
├── scratch/
│   └── test_pocketca.py
│       └── Automated verification tests
│
└── README.md
```

---

## ⚡ Quick Start

### Prerequisites

* Python 3.10+
* Google Gemini API key for generative AI features
* Git
* Modern web browser

### 1. Clone the Repository

```bash
git clone https://github.com/TirumalaLaxman/PocketCA.git
cd PocketCA
```

### 2. Install Backend Dependencies

```bash
cd backend
python -m pip install -r requirements.txt
```

### 3. Configure Google Gemini

Create a `.env` file inside the `backend/` directory:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

The API key can also be configured through the application's settings interface if supported by the current frontend implementation.

### 4. Start the Backend

From the `backend/` directory:

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

FastAPI API documentation:

```text
http://127.0.0.1:8000/docs
```

### 5. Start the Frontend

Open a new terminal:

```bash
cd frontend
python -m http.server 3000
```

Then open:

```text
http://localhost:3000
```

---

## 🧪 Running Automated Tests

PocketCA includes an automated verification script covering the financial tools, RAG functionality, and API endpoints.

On Windows PowerShell:

```powershell
$env:PYTHONIOENCODING="utf-8"
python scratch/test_pocketca.py
```

---

## 📡 API Endpoints

| Method   | Endpoint                | Description                                                |
| -------- | ----------------------- | ---------------------------------------------------------- |
| `GET`    | `/`                     | System status, knowledge base metrics and tool information |
| `POST`   | `/chat`                 | Multi-turn AI consultation with RAG context                |
| `GET`    | `/history/{session_id}` | Retrieve consultation history                              |
| `DELETE` | `/history/{session_id}` | Clear consultation history                                 |
| `POST`   | `/upload`               | Upload PDF/TXT/CSV documents                               |
| `POST`   | `/config/api-key`       | Configure Google Gemini API key                            |
| `GET`    | `/tools`                | List available financial tools                             |
| `POST`   | `/tools/gst`            | Calculate GST                                              |
| `POST`   | `/tools/tax`            | Compare tax regimes                                        |
| `POST`   | `/tools/tds`            | Calculate TDS                                              |
| `POST`   | `/tools/emi`            | Calculate loan EMI                                         |
| `POST`   | `/tools/hra`            | Calculate HRA exemption                                    |
| `POST`   | `/tools/depreciation`   | Generate depreciation schedule                             |
| `POST`   | `/tools/journal`        | Generate double-entry journal entries                      |

---

## 🔐 Security Note

API keys and other sensitive configuration values should be stored securely and should **never be committed to GitHub**.

Use environment variables or the application's supported runtime configuration mechanism.

Make sure `.env` is included in `.gitignore`.

---

## ⚠️ Disclaimer

PocketCA is an **AI-assisted financial and accounting application developed for educational and software-engineering purposes**.

It should not be treated as a substitute for professional advice from a qualified Chartered Accountant, tax professional, or financial advisor.

Tax laws, regulations, rates, and compliance requirements can change. Users should verify applicable rules against current official sources before making financial or compliance decisions.

---

## 🎯 Project Goals

PocketCA was built to explore how modern AI technologies can be combined with domain-specific financial software.

The project demonstrates:

* Retrieval-Augmented Generation (RAG)
* Large Language Model integration
* Vector search
* Keyword retrieval
* Document ingestion
* Prompt engineering
* Conversational AI
* Deterministic financial computation
* REST API development
* Full-stack application development
* AI application architecture

---

## 🚧 Future Improvements

Potential future enhancements include:

* Authentication and user accounts
* Persistent database-backed conversations
* More Indian tax and GST reference documents
* Improved document parsing
* Hybrid retrieval optimization
* Reranking retrieved documents
* Evaluation datasets for RAG quality
* Automated response evaluation
* Production deployment
* Advanced financial document analysis
* Voice-based financial assistant
* Role-based access control

---

## 👨‍💻 Author

**Tirumala Laxman**

AI/ML Engineer | Python Developer | Generative AI Enthusiast

GitHub: https://github.com/TirumalaLaxman

---

⭐ If you find the project interesting, feel free to explore the repository and follow the development journey.
