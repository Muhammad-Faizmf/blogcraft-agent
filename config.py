import os
from pathlib import Path

from dotenv import dotenv_values

MAX_TOPIC_LENGTH = 200
MAX_AUDIENCE_LENGTH = 120
MAX_FEEDBACK_LENGTH = 2000
MAX_REVISIONS = 5
DEFAULT_MODEL = "openai/gpt-oss-20b"


def create_model_settings(secrets=None):
    """Read optional Streamlit overrides, environment variables, and local defaults."""
    local = dotenv_values(Path(__file__).resolve().with_name(".env"))
    secrets = secrets if secrets is not None else {}

    def read(name):
        for value in (secrets.get(name), os.getenv(name), local.get(name)):
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    key = read("GROQ_API_KEY")
    if not key:
        raise ConfigurationError("The blog generator needs GROQ_API_KEY.")
    return key, read("GROQ_MODEL") or DEFAULT_MODEL


class ConfigurationError(Exception):
    """Required settings are missing."""
