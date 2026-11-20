from agents.blog_agents import build_model
from config import MAX_FEEDBACK_LENGTH
from workflow.graph import create_blog_graph, validate_input
from workflow.run import BlogRun
from workflow.service_errors import error_message


def main() -> int:
    try:
        inputs = validate_input({"topic": input("Topic: "), "audience": input("Audience: ")})
    except ValueError as error:
        print(error)
        return 1
    except (EOFError, KeyboardInterrupt):
        return 0

    try:
        run = BlogRun(create_blog_graph(build_model()), **inputs)
    except Exception as error:
        print(error_message(error))
        return 1

    run.execute(run.start)
    while True:
        try:
            if run.error:
                print(run.error)
                if input("Retry? [y/N]: ").strip().lower() != "y":
                    return 1
                run.execute(run.retry)
                continue

            state = run.snapshot()
            if state.values.get("final_blog") and not state.next:
                print(state.values["final_blog"])
                return 0
            if not state.interrupts:
                print("The workflow paused without an active review.")
                return 1

            pending = state.interrupts[0]
            print(pending.value["content"])
            action = input("Approve [a], revise [r], or quit [q]: ").strip().lower()
            if action == "q":
                return 0
            if action not in {"a", "r"}:
                continue
            feedback = ""
            if action == "r":
                if not pending.value["revisions_left"]:
                    print("Revision limit reached. You can approve the current version or quit.")
                    continue
                feedback = input("Revision feedback: ").strip()
                if not 0 < len(feedback) <= MAX_FEEDBACK_LENGTH:
                    print(f"Enter 1 to {MAX_FEEDBACK_LENGTH} characters of feedback.")
                    continue

            decision = {"action": "approve" if action == "a" else "revise", "feedback": feedback}
            run.execute(lambda: run.resume(pending.id, decision))
        except (EOFError, KeyboardInterrupt):
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
