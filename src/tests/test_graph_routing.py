from src.core.config import settings
from src.pipelines.graph import (
    route_after_code_review,
    route_after_hitl_arch,
    route_after_hitl_deploy,
    route_after_hitl_developer,
    route_after_hitl_qa,
    route_after_hitl_req,
    route_after_hitl_review,
    route_after_qa,
)


def test_hitl_req_approve_goes_to_doc_requirements():
    state = {'feedback': [{'phase': 'requirements', 'verdict': 'approve'}]}
    assert route_after_hitl_req(state) == 'doc_requirements'


def test_hitl_req_reject_loops_to_requirement():
    state = {'feedback': [{'phase': 'requirements', 'verdict': 'reject'}]}
    assert route_after_hitl_req(state) == 'requirement'


def test_hitl_arch_approve_goes_to_doc_architecture():
    state = {'feedback': [{'phase': 'architecture', 'verdict': 'approve'}]}
    assert route_after_hitl_arch(state) == 'doc_architecture'


def test_hitl_arch_reject_loops_to_architect():
    state = {'feedback': [{'phase': 'architecture', 'verdict': 'reject'}]}
    assert route_after_hitl_arch(state) == 'architect'


def test_hitl_developer_approve_goes_to_code_review():
    state = {'feedback': [{'phase': 'developer', 'verdict': 'approve'}]}
    assert route_after_hitl_developer(state) == 'code_review'


def test_hitl_developer_reject_loops_to_developer():
    state = {'feedback': [{'phase': 'developer', 'verdict': 'reject'}]}
    assert route_after_hitl_developer(state) == 'developer'


def test_code_review_pass_goes_to_hitl_review():
    state = {'code_review': {'passed': True}, 'review_retries': 0}
    assert route_after_code_review(state) == 'hitl_review'


def test_code_review_fail_under_limit_loops_to_developer():
    state = {'code_review': {'passed': False}, 'review_retries': 1}
    assert state['review_retries'] < settings.MAX_REVIEW_RETRIES
    assert route_after_code_review(state) == 'developer'


def test_code_review_fail_at_limit_surfaces_to_human():
    state = {
        'code_review': {'passed': False},
        'review_retries': settings.MAX_REVIEW_RETRIES,
    }
    assert route_after_code_review(state) == 'hitl_review'


def test_hitl_review_approve_goes_to_doc_developer():
    state = {'feedback': [{'phase': 'code_review', 'verdict': 'approve'}]}
    assert route_after_hitl_review(state) == 'doc_developer'


def test_hitl_review_reject_loops_to_developer():
    state = {'feedback': [{'phase': 'code_review', 'verdict': 'reject'}]}
    assert route_after_hitl_review(state) == 'developer'


def test_qa_pass_goes_to_hitl_qa():
    state = {'test_report': {'status': 'pass'}, 'qa_retries': 0}
    assert route_after_qa(state) == 'hitl_qa'


def test_qa_fail_under_limit_loops_to_developer():
    state = {'test_report': {'status': 'fail'}, 'qa_retries': 0}
    assert route_after_qa(state) == 'developer'


def test_qa_fail_at_limit_surfaces_to_human():
    state = {
        'test_report': {'status': 'fail'},
        'qa_retries': settings.MAX_QA_RETRIES,
    }
    assert route_after_qa(state) == 'hitl_qa'


def test_hitl_qa_approve_goes_to_doc_qa():
    state = {'feedback': [{'phase': 'qa', 'verdict': 'approve'}]}
    assert route_after_hitl_qa(state) == 'doc_qa'


def test_hitl_qa_reject_loops_to_developer():
    state = {'feedback': [{'phase': 'qa', 'verdict': 'reject'}]}
    assert route_after_hitl_qa(state) == 'developer'


def test_hitl_deploy_approve_goes_to_devops():
    state = {'feedback': [{'phase': 'deployment', 'verdict': 'approve'}]}
    assert route_after_hitl_deploy(state) == 'devops'


def test_hitl_deploy_reject_loops_to_qa():
    state = {'feedback': [{'phase': 'deployment', 'verdict': 'reject'}]}
    assert route_after_hitl_deploy(state) == 'qa'
