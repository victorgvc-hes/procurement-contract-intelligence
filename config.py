import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

RAW_CONTRACTS_DIR = DATA_DIR / "raw" / "contracts"
RAW_PO_DIR = DATA_DIR / "raw" / "purchase_orders"

CHUNKS_DIR = DATA_DIR / "processed" / "chunks"
EXTRACTED_DIR = DATA_DIR / "processed" / "extracted"
DB_PATH = DATA_DIR / "processed" / "procurement.duckdb"

# ---------------------------------------------------------------------------
# Claude model
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
MODEL_NAME: str = "claude-opus-4-6"
MAX_TOKENS: int = 4096

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
CHUNK_SIZE: int = 1000
CHUNK_OVERLAP: int = 200

# ---------------------------------------------------------------------------
# Embeddings / vector store
# ---------------------------------------------------------------------------
EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"          # free HuggingFace model
CHROMA_PERSIST_DIR: Path = BASE_DIR / ".chroma"

# ---------------------------------------------------------------------------
# Extraction behaviour
# ---------------------------------------------------------------------------
USE_MOCK_EXTRACTOR: bool = True   # set False to use live Claude API calls

# ---------------------------------------------------------------------------
# Compliance thresholds
# ---------------------------------------------------------------------------
PAYMENT_DAYS_THRESHOLD: int = 30      # flag POs paid later than this vs contract terms
PRICE_BREACH_THRESHOLD: float = 0.05  # flag POs where actual price > contracted * (1 + threshold)
RENEWAL_ALERT_DAYS: int = 90          # warn if contract expires within this many days

# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------
PO_CSV = RAW_PO_DIR / "SCMS_Delivery_History_Dataset.csv"
