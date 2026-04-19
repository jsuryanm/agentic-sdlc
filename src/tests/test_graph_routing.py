from src.pipelines.graph import (
    route_after_critic,
    route_after_hitl_qa,
    route_after_qa,
)


def test_route_after_critic_approved_goes_to_qa():
    state = {"critic_report": {"approved": True}, "critic_retries": 0}
    assert route_after_critic(state) == "qa"


def test_route_after_critic_rejected_goes_to_developer():
    state = {"critic_report": {"approved": False}, "critic_retries": 1}
    assert route_after_critic(state) == "developer"


def test_route_after_qa_goes_to_hitl_qa():
    state = {"test_report": {"status": "pass"}, "qa_retries": 0}
    assert route_after_qa(state) == "hitl_qa"


def test_route_after_hitl_qa_verdicts():
    assert route_after_hitl_qa({"feedback": [{"verdict": "approve"}], "qa_retries": 0}) == "devops"
    assert route_after_hitl_qa({"feedback": [{"verdict": "reject"}], "qa_retries": 0}) == "developer"
