from pathlib import Path
import os
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")
INPUT_JSON = Path(os.getenv(
    "AGRI_INPUT_JSON",
    str(PROJECT_DIR / "data" / "expanded_crop_guide.json")
))
OUTPUT_DIR = PROJECT_DIR / "output"
DB_PATH = OUTPUT_DIR / "kg_extraction_openrouter_final.db"
LOG_PATH = OUTPUT_DIR / "extraction.log"

PROVIDER = "openrouter"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"
OPENROUTER_HTTP_REFERER = "http://localhost"
OPENROUTER_APP_TITLE = "Agricultural Knowledge Graph Extraction"
ACTIVE_MODEL = "openai/gpt-oss-120b"  # provisional candidate from the 20-chunk comparison

# Start with 3,000-character work units. A truncated unit is split again automatically.
TARGET_CHUNK_CHARS = 4000
MAX_CHUNK_CHARS = 3200
CHUNK_OVERLAP_PARAGRAPHS = 0
MAX_RECURSIVE_SPLIT_DEPTH = 5
MIN_SPLIT_CHARS = 700

# One API attempt per generation call. Truncation triggers splitting, not a blind retry.
MAX_OUTPUT_TOKENS = 12288
GENERATION_RETRIES = 2  # retries only for transient network/server errors; truncation does not retry
RETRY_DELAY_SECONDS = 4
REQUEST_TIMEOUT_SECONDS = 240
TEMPERATURE = 0.0
TOP_P = 0.9
DAILY_REQUEST_BUDGET = 850
# The benchmark log ended at request 83 on 2026-10-26; carry this into the new ledger.
LEGACY_REQUESTS_DAY = "2026-10-26"
LEGACY_REQUESTS_USED = 83
RETRY_FAILED_CHUNKS = True
EXPORT_AFTER_EVERY_N_CHUNKS = 10

ENTITY_TYPES = [
    "CROP", "VARIETY", "DISEASE", "PEST", "WEED", "SYMPTOM", "PATHOGEN",
    "CHEMICAL", "PESTICIDE", "BIO_AGENT", "TREATMENT", "FERTILIZER", "NUTRIENT",
    "CLIMATE", "SOIL_TYPE", "TEMPERATURE", "RAINFALL", "GROWTH_STAGE", "SEASON",
    "IRRIGATION_METHOD", "AGRICULTURAL_PRACTICE", "REGION", "DISTRICT", "ZONE",
    "YIELD", "HARVESTING_METHOD", "WATER_REQUIREMENT", "SOIL_PROPERTY", "PLANT_PART",
    "ORGANISM", "OTHER"
]
PREDICATES = [
    "HAS_VARIETY", "HAS_DISEASE", "AFFECTS", "CAUSED_BY", "HAS_SYMPTOM", "CONTROLLED_BY",
    "RECOMMENDED_FOR", "RESISTANT_TO", "SUSCEPTIBLE_TO", "REQUIRES", "GROWN_IN",
    "SUITABLE_FOR", "APPLIED_DURING", "CONTAINS_NUTRIENT", "HAS_GROWTH_STAGE", "FAVOURED_BY",
    "MANAGED_BY", "PRODUCES", "HAS_YIELD", "IRRIGATED_BY", "SOWN_DURING", "HARVESTED_DURING",
    "OCCURS_IN", "FOUND_IN", "USED_FOR", "CONTROLS", "PREVENTS", "INCREASES", "REDUCES",
    "OPTIMUM_TEMPERATURE", "OPTIMUM_RAINFALL", "OPTIMUM_SOIL", "REQUIRES_WATER", "HAS_DURATION",
    "HAS_SPACING", "HAS_DOSE", "HAS_APPLICATION_METHOD", "HAS_SOIL_PROPERTY",
    "HAS_CLIMATE_REQUIREMENT", "HAS_PRACTICE", "PART_OF", "ASSOCIATED_WITH", "OTHER"
]
