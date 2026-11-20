import logging
from threading import Lock
from uuid import uuid4

from langgraph.types import Command

from workflow.service_errors import error_message
from .state import ReviewDecision

logger = logging.getLogger(__name__)


class BlogRun:
    """Own a workflow and its checkpoints for one blog."""

    def __init__(self, graph, topic: str, audience: str):
        self.graph = graph
        self.topic = topic
        self.audience = audience
        self.config = {"configurable": {"thread_id": uuid4().hex}}
        self.lock = Lock()
        self.error = None
        self.attempt = 0

    def snapshot(self):
        return self.graph.get_state(self.config)

    def execute(self, operation):
        if not self.lock.acquire(blocking=False):
            return
        try:
            self.attempt += 1
            operation()
            self.error = None
        except Exception as error:
            logger.error("Blog workflow failed (%s, status=%s)", type(error).__name__, getattr(error, "status_code", None))
            self.error = error_message(error)
        finally:
            self.lock.release()

    def start(self):
        self.graph.invoke({"topic": self.topic, "audience": self.audience}, self.config)

    def resume(self, interrupt_id: str, decision: ReviewDecision):
        if any(item.id == interrupt_id for item in self.snapshot().interrupts):
            self.graph.invoke(Command(resume={interrupt_id: decision}), self.config)

    def retry(self):
        state = self.snapshot()
        if state.values.get("final_blog") or state.interrupts:
            return
        if state.next:
            self.graph.invoke(None, self.config)
        else:
            self.start()
