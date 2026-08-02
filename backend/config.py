import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
RULES_DIR = Path(__file__).parent / "rules"

AZURE_OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT",
    "https://fractal-finance-analytics-i2c-openai-i2c-poc.openai.azure.com/",
).rstrip("/")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv(
    "AZURE_OPENAI_API_VERSION", "2024-12-01-preview"
)
AZURE_OPENAI_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_DEPLOYMENT", "t1-gpt-5-nano"
)
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8000"))


def load_business_rules() -> dict:
    rules_path = RULES_DIR / "collection_rules.yaml"
    with open(rules_path, "r") as f:
        return yaml.safe_load(f)


BUSINESS_RULES = load_business_rules()
