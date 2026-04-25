import anthropic
from src.config import settings

HAIKU_MODEL = "claude-haiku-4-5-20251001"
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

client = anthropic.AsyncAnthropic(
    api_key=settings.ANTHROPIC_API_KEY.get_secret_value()
)
