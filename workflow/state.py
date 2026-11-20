from typing import Literal, TypedDict


class BlogState(TypedDict, total=False):
    topic: str
    audience: str
    research_notes: str
    research_feedback: str
    draft: str
    draft_feedback: str
    final_blog: str
    revision_count: int


class ReviewDecision(TypedDict):
    action: Literal["approve", "revise"]
    feedback: str
