"""Configuration settings for the Insurance Claim Assistant."""

import os
from dotenv import load_dotenv

load_dotenv()

# Mistral AI settings
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MODEL_NAME = "mistral-small-latest"

# LangSmith settings (optional)
LANGSMITH_ENABLED = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGCHAIN_PROJECT", "insurance-claim-assistant")

# Application settings
MAX_FILE_SIZE_MB = 10
SUPPORTED_FILE_TYPES = ["pdf", "png", "jpg", "jpeg"]

# Appeal deadlines (days from denial)
DEFAULT_APPEAL_DEADLINE_DAYS = 180
URGENT_APPEAL_DEADLINE_DAYS = 60

# Output settings
OUTPUT_DIR = "./output"
