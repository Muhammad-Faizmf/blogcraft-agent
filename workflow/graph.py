from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from agents.blog_agents import BlogAgents
from config import MAX_AUDIENCE_LENGTH, MAX_FEEDBACK_LENGTH, MAX_REVISIONS, MAX_TOPIC_LENGTH
from .state import BlogState


def validate_input(state: BlogState):
    topic = state.get("topic", "").strip()
    audience = state.get("audience", "").strip()
    if not 0 < len(topic) <= MAX_TOPIC_LENGTH:
        raise ValueError(f"Enter a topic of 1 to {MAX_TOPIC_LENGTH} characters.")
    if not 0 < len(audience) <= MAX_AUDIENCE_LENGTH:
        raise ValueError(f"Enter an audience of 1 to {MAX_AUDIENCE_LENGTH} characters.")
    return {"topic": topic, "audience": audience}


def review(state, step, content_key, feedback_key, approve_node, revise_node):
    revisions = state.get("revision_count", 0)
    decision = interrupt({
        "step": step,
        "content": state[content_key],
        "revisions_left": MAX_REVISIONS - revisions,
    })
    if isinstance(decision, dict) and decision.get("action") == "approve":
        return Command(goto=approve_node, update={feedback_key: ""})

    feedback = decision.get("feedback") if isinstance(decision, dict) else None
    if (
        isinstance(decision, dict)
        and decision.get("action") == "revise"
        and isinstance(feedback, str)
        and 0 < len(feedback.strip()) <= MAX_FEEDBACK_LENGTH
        and revisions < MAX_REVISIONS
    ):
        return Command(
            goto=revise_node,
            update={feedback_key: feedback.strip(), "revision_count": revisions + 1},
        )

    return Command(goto=step)


def research_review(state: BlogState) -> Command:
    return review(state, "research_review", "research_notes", "research_feedback", "writer", "researcher")


def draft_review(state: BlogState) -> Command:
    return review(state, "draft_review", "draft", "draft_feedback", "finalize", "writer")


def finalize(state: BlogState):
    return {"final_blog": state["draft"]}


def create_blog_graph(model, checkpointer=None):
    agents = BlogAgents(model)
    builder = StateGraph(BlogState)
    builder.add_node("validate", validate_input)
    builder.add_node("researcher", agents.research)
    builder.add_node("research_review", research_review, destinations=("research_review", "writer", "researcher"))
    builder.add_node("writer", agents.write)
    builder.add_node("editor", agents.edit)
    builder.add_node("draft_review", draft_review, destinations=("draft_review", "finalize", "writer"))
    builder.add_node("finalize", finalize)
    builder.add_edge(START, "validate")
    builder.add_edge("validate", "researcher")
    builder.add_edge("researcher", "research_review")
    builder.add_edge("writer", "editor")
    builder.add_edge("editor", "draft_review")
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=checkpointer if checkpointer is not None else InMemorySaver())
