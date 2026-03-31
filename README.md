# Procurement Contract Intelligence

> AI-powered contract analysis and compliance monitoring for procurement teams

## What it does

This system ingests PDF procurement contracts, uses Claude (Anthropic) to extract
structured clause data (pricing, penalties, renewal terms), and detects compliance
gaps by joining those clauses against real purchase-order actuals from the SCMS
dataset. A ChromaDB-backed RAG layer lets users ask natural-language questions
across the full contract corpus, and a four-page Streamlit dashboard surfaces
everything — from clause-level drill-down to renewal deadline alerts — in a
production-ready UI.

## Architecture

```
PDF Contracts          Ingestion              LLM Extraction
(CUAD dataset)  ─────► PyMuPDF + LangChain ─► Claude API
                        chunker.py             Pydantic schemas
                                               DuckDB storage
                              │                      │
                              ▼                      ▼
                       RAG Q&A Layer         Compliance Engine
                       ChromaDB              Gap detection vs
                       SentenceTransformers  SCMS PO actuals
                       Claude (answers)      DuckDB SQL joins
                              │                      │
                              └──────────┬───────────┘
                                         ▼
                               Streamlit Dashboard
                               4-page UI · Plotly charts
```

## Tech Stack

| Component       | Technology                     | Purpose                                  |
|-----------------|-------------------------------|------------------------------------------|
| PDF Parsing     | PyMuPDF (`fitz`)              | Extract raw text per page from contracts |
| Chunking        | LangChain `RecursiveCharacterTextSplitter` | Overlapping 1000-char chunks |
| LLM Extraction  | Anthropic Claude (`claude-opus-4-6`) | Structured clause extraction via Pydantic |
| Vector Store    | ChromaDB (persistent)         | Semantic chunk storage and retrieval     |
| Embeddings      | `sentence-transformers/all-MiniLM-L6-v2` | Free HuggingFace embeddings   |
| Database        | DuckDB                        | Clause storage and compliance SQL joins  |
| Dashboard       | Streamlit + Plotly            | 4-page interactive UI                    |
| Validation      | Pydantic v2                   | Schema enforcement on LLM output         |
| Testing         | pytest                        | Unit tests for parser, schema, gap engine|

## Dataset

| Dataset | Source | Usage |
|---------|--------|-------|
| **CUAD** — Contract Understanding Atticus Dataset | [Kaggle](https://www.kaggle.com/datasets/konradb/atticus-open-contract-dataset-aok-beta) | 31 PDF contracts, 1 957 chunks, 3 clause types extracted |
| **SCMS Delivery History** — Shipment pricing & delivery data | [Kaggle](https://www.kaggle.com/datasets/divyeshardeshana/supply-chain-management-dataset) | 10 324 PO rows, used for compliance gap joins |

## Project Structure

```
procurement-contract-intelligence/
├── config.py                      # Single source of truth — model, paths, thresholds
├── requirements.txt
├── .env                           # ANTHROPIC_API_KEY (gitignored)
├── .gitignore
├── README.md
│
├── data/
│   ├── raw/
│   │   ├── contracts/             # CUAD PDF contracts
│   │   └── purchase_orders/       # SCMS shipment pricing CSV
│   └── processed/
│       ├── chunks/                # JSON chunked contract text
│       ├── compliance_*.csv       # Gap engine output CSVs
│       └── procurement.duckdb     # DuckDB — all extracted clause tables
│
├── ingestion/
│   ├── pdf_parser.py              # PyMuPDF: PDF → raw text per page
│   ├── chunker.py                 # LangChain: text → overlapping chunks
│   └── pipeline.py                # Orchestrates parse → chunk → JSON
│
├── extraction/
│   ├── schema.py                  # Pydantic models: PriceClause, PenaltyClause, RenewalClause
│   ├── llm_extractor.py           # Claude API calls with keyword-filtered chunks
│   ├── mock_extractor.py          # Deterministic stubs for testing without API credits
│   ├── db_writer.py               # Writes validated clauses → DuckDB
│   └── run_extraction.py          # Batch extraction script
│
├── compliance/
│   ├── po_loader.py               # Loads and cleans SCMS PO CSV
│   ├── gap_engine.py              # price_gaps / penalty_exposure / renewal_alerts
│   ├── queries.sql                # Named SQL for each compliance check
│   └── run_compliance.py          # Batch compliance report + CSV export
│
├── rag/
│   ├── embedder.py                # Chunks → ChromaDB (idempotent)
│   ├── qa_chain.py                # RetrievalQA: ChromaDB + Claude answer generation
│   └── run_rag.py                 # Embed all contracts + run 3 test questions
│
├── app/
│   ├── dashboard.py               # Streamlit home: 4 metric cards + clause chart
│   └── pages/
│       ├── 1_contract_explorer.py # Contract table, clause drill-down, bar chart
│       ├── 2_compliance_gaps.py   # Price / penalty / renewal tabs with Plotly
│       └── 3_ask_your_contracts.py# Chat UI with session history + source citations
│
├── scripts/
│   └── run_ingestion.py           # Batch PDF ingestion → chunk JSON files
│
├── notebooks/
│   └── eval_extraction.ipynb      # Precision/recall eval + renewal timeline chart
│
└── tests/
    ├── test_parser.py             # PDF parser and chunker unit tests
    ├── test_schema.py             # Pydantic model tests
    └── test_gap_engine.py         # Compliance gap engine tests
```

## Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd procurement-contract-intelligence

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Anthropic API key
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# 5. Download datasets and place them at:
#    data/raw/contracts/           ← CUAD PDF files
#    data/raw/purchase_orders/     ← SCMS_Delivery_History_Dataset.csv

# 6. Run PDF ingestion (parse + chunk all contracts)
python scripts/run_ingestion.py

# 7. Run LLM extraction → DuckDB
python extraction/run_extraction.py

# 8. Build the RAG vector index
python rag/run_rag.py

# 9. Launch the dashboard
streamlit run app/dashboard.py
```

> **Note:** Steps 7–8 use the Anthropic API when `USE_MOCK_EXTRACTOR = False`.
> The default is `True` (no API credits), which uses hardcoded stubs for development.

## Switching to Live Mode

Open `config.py` and change:

```python
USE_MOCK_EXTRACTOR: bool = True   # ← change to False
```

Then re-run extraction and the RAG embedder. All 31 contracts × ~3 filtered chunks
each ≈ 90–100 API calls. Estimated cost: **$0.10–0.30 USD** at current pricing.

## Running Tests

```bash
pytest tests/ -v
```

## Portfolio Notes

This project demonstrates end-to-end production patterns for applied LLM engineering:
**structured output extraction** (Claude + Pydantic schema enforcement with fallback
validation), **RAG architecture** (chunking strategy, vector retrieval, cited answers),
and **compliance analytics** (DuckDB joins across heterogeneous data sources with a
mock/live toggle for cost-free development). The codebase is organised around clear
separation of concerns — ingestion, extraction, compliance, RAG, and UI are fully
decoupled — reflecting the kind of modular design required for maintainable AI systems
in production.
