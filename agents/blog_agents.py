from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_groq import ChatGroq

from config import create_model_settings
from .prompts import EDITOR_PROMPT, RESEARCH_PROMPT, WRITER_PROMPT


class InvalidModelResponse(Exception):
    """The provider returned an incomplete or empty response."""


def build_model(secrets=None) -> ChatGroq:
    key, model = create_model_settings(secrets)
    return ChatGroq(
        api_key=key,
        model=model,
        temperature=0.3,
        timeout=30,
        max_retries=1,
        max_tokens=6000,
    )


class BlogAgents:
    def __init__(self, model: BaseChatModel):
        self.research_chain = RESEARCH_PROMPT | model
        self.writer_chain = WRITER_PROMPT | model
        self.editor_chain = EDITOR_PROMPT | model

    def research(self, state):
        response = self.research_chain.invoke({
            "topic": state["topic"],
            "audience": state["audience"],
            "research_notes": state.get("research_notes", ""),
            "research_feedback": state.get("research_feedback", ""),
        })
        return {"research_notes": response_text(response)}

    def write(self, state):
        response = self.writer_chain.invoke({
            "topic": state["topic"],
            "audience": state["audience"],
            "research_notes": state["research_notes"],
            "draft": state.get("draft", ""),
            "draft_feedback": state.get("draft_feedback", ""),
        })
        return {"draft": response_text(response)}

    def edit(self, state):
        response = self.editor_chain.invoke({
            "topic": state["topic"],
            "audience": state["audience"],
            "draft": state["draft"],
        })
        return {"draft": response_text(response)}


def response_text(response: AIMessage) -> str:
    text = response.text.strip()
    if not text or response.response_metadata.get("finish_reason") in {"length", "content_filter"}:
        raise InvalidModelResponse
    return text
