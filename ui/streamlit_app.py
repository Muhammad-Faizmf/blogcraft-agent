import logging
import re

import streamlit as st

from agents.blog_agents import build_model
from config import MAX_AUDIENCE_LENGTH, MAX_FEEDBACK_LENGTH, MAX_TOPIC_LENGTH
from workflow.graph import create_blog_graph, validate_input
from workflow.run import BlogRun
from workflow.service_errors import error_message

logger = logging.getLogger(__name__)
CUSTOM_AUDIENCE = "Custom audience"
AUDIENCES = [
    "Software Engineers & Developers",
    "Beginners & Students",
    "Data Scientists & AI Practitioners",
    "CTOs & Technical Leaders",
    "Product Managers",
    "General Tech Audience",
    CUSTOM_AUDIENCE,
]
IDEAS = [
    ("AI agents", "Building AI Agents with LangGraph", AUDIENCES[0]),
    ("FastAPI vs Go", "FastAPI vs Go for Microservices", "Backend Engineers"),
    ("Zero-trust security", "Zero-Trust Architecture for Cloud Apps", AUDIENCES[3]),
    ("Bootstrapping SaaS", "How to Bootstrap a B2B SaaS", "Indie Hackers & Founders"),
]


def render():
    st.set_page_config(
        page_title="BlogCraft Agent",
        page_icon="✍️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.title("BlogCraft Agent")
    run = st.session_state.get("blog_run")
    if run is not None and run.lock.locked():
        show_processing(st.empty())
        with run.lock:
            pass
        st.rerun()

    action_area = st.empty()
    with action_area.container():
        if run is None:
            run = render_setup()
            action = run.start if run is not None else None
        else:
            if st.button("Start New Blog", key=f"reset-{run.attempt}"):
                del st.session_state.blog_run
                st.rerun()
            action = render_current_run(run)

    if action is not None:
        show_processing(action_area)
        run.execute(action)
        st.rerun()


def show_processing(action_area):
    action_area.button("Processing…", key="blog_processing", disabled=True, type="primary")


def render_current_run(run):
    state = run.snapshot()
    final_blog = state.values.get("final_blog")
    if not final_blog or state.next:
        st.text(f"Blog Topic: {run.topic}")
        st.text(f"Target Audience: {run.audience}")

    if run.error:
        st.error(run.error)
        if st.button("Retry Generation", key=f"retry-{run.attempt}", type="primary"):
            return run.retry
    elif state.interrupts:
        return render_review(run, state.interrupts[0])
    elif final_blog and not state.next:
        render_final(run, final_blog)
    else:
        st.warning("This blog is still in progress.")
        if st.button("Continue Generation", key=f"continue-{run.attempt}", type="primary"):
            return run.retry

    return None


def choose_idea(topic, audience):
    st.session_state.blog_topic = topic
    st.session_state.blog_audience = audience if audience in AUDIENCES else CUSTOM_AUDIENCE
    st.session_state.blog_custom_audience = "" if audience in AUDIENCES else audience


def render_setup():
    st.caption("Review an outline and an edited draft, then download your approved post.")
    for column, (label, topic, audience) in zip(st.columns(len(IDEAS)), IDEAS):
        column.button(label, on_click=choose_idea, args=(topic, audience))

    topic = st.text_input("Blog topic", max_chars=MAX_TOPIC_LENGTH, key="blog_topic")
    audience = st.selectbox("Target audience", AUDIENCES, key="blog_audience")
    if audience == CUSTOM_AUDIENCE:
        audience = st.text_input(
            "Custom audience", max_chars=MAX_AUDIENCE_LENGTH, key="blog_custom_audience"
        )
    if not st.button("Start Blog Generation", type="primary"):
        return

    try:
        inputs = validate_input({"topic": topic, "audience": audience})
    except ValueError as error:
        st.error(str(error))
        return

    graph = build_graph()
    if graph is None:
        return None

    run = BlogRun(graph, **inputs)
    st.session_state.blog_run = run
    return run


def build_graph():
    try:
        try:
            secrets = {name: st.secrets.get(name) for name in ("GROQ_API_KEY", "GROQ_MODEL")}
        except FileNotFoundError:
            secrets = None
        return create_blog_graph(build_model(secrets))
    except Exception as error:
        logger.error("Blog configuration failed (%s)", type(error).__name__)
        st.error(error_message(error))
        return None


def render_review(run, pending):
    review = pending.value
    is_research = review["step"] == "research_review"
    st.subheader("Review notes and outline" if is_research else "Review edited draft")
    st.markdown(review["content"])
    st.caption(f"Revisions remaining across both stages: {review['revisions_left']}")

    with st.form(f"review-{pending.id}-{run.attempt}"):
        feedback = st.text_area(
            "Revision feedback", max_chars=MAX_FEEDBACK_LENGTH, disabled=not review["revisions_left"]
        )
        approve, revise = st.columns(2)
        approved = approve.form_submit_button("Approve Outline" if is_research else "Approve Final Post", type="primary")
        revised = revise.form_submit_button("Request Revision", disabled=not review["revisions_left"])

    if revised and not feedback.strip():
        st.warning("Enter feedback before requesting a revision.")
    elif approved or revised:
        decision = {"action": "approve" if approved else "revise", "feedback": feedback.strip()}
        return lambda: run.resume(pending.id, decision)

    return None


def render_final(run, markdown):
    st.success("Blog post approved and ready to download.")
    heading = re.match(r"#\s+([^\n]+)", markdown.lstrip())
    title = heading.group(1).strip() if heading else run.topic
    st.text(f"Blog Title: {title}")
    st.text(f"Target Audience: {run.audience}")
    st.markdown(markdown)
    slug = re.sub(r"[^a-z0-9]+", "-", run.topic.lower()).strip("-")[:60].rstrip("-")
    st.download_button("Download Markdown", markdown, f"{slug or 'blog-post'}.md", mime="text/markdown")
