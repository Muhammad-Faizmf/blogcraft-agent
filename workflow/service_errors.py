from groq import APIConnectionError, APIStatusError

from agents.blog_agents import InvalidModelResponse
from config import ConfigurationError


def error_message(error: Exception) -> str:
    if isinstance(error, ConfigurationError):
        return str(error)
    if isinstance(error, APIStatusError):
        if error.status_code == 429:
            message = "Groq reached its usage limit. Your progress is saved in this session."
            try:
                seconds = int(error.response.headers.get("Retry-After", "0"))
            except ValueError:
                seconds = 0

            if seconds > 0:
                amount, unit = (seconds, "second") if seconds < 60 else ((seconds + 59) // 60, "minute")
                wait = f"{amount} {unit}{'s' if amount != 1 else ''}"
                return f"{message} Wait at least {wait} before retrying the failed step."
            return f"{message} Try again later to continue from the failed step."
        if error.status_code in (401, 403, 404):
            return "The AI service could not access the configured model. Contact the app administrator."
        if error.status_code >= 500:
            return "The AI service is temporarily unavailable. Please try again later."
    if isinstance(error, APIConnectionError):
        return "The AI service could not be reached. Please try again later."
    if isinstance(error, InvalidModelResponse):
        return "The AI service returned an incomplete response. Please try again."
    return "Blog generation could not continue. Please try again."
