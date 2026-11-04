import json
from github_repo_auditor import (filter_active_repositories, save_report, requires_pull_request,
                                 fetch_branch_rules, evaluate_pull_request_rule, status_to_exit_code,
                                 build_github_headers, get_required_approvals, evaluate_required_approvals,
                                 aggregate_statuses)
from unittest.mock import Mock, patch

import requests


def test_filter_active_repositories_excludes_archived():
    sample_repositories = [
        {"name": "example/active", "archived": False},
        {"name": "example/old", "archived": True},
    ]
    result = filter_active_repositories(sample_repositories)
    assert result == [{"name": "example/active", "archived": False}]


def test_filter_active_repositories_handles_empty_list():
    sample_repositories = []
    result = filter_active_repositories(sample_repositories)
    assert result == []


def test_filter_active_repositories_excludes_all_archived():
    sample_repositories = [
        {"name": "example/active_not", "archived": True},
        {"name": "example/old", "archived": True},
    ]
    result = filter_active_repositories(sample_repositories)
    assert result == []


def test_save_report_writes_json(tmp_path):
    sample_repositories = [
        {"name": "example/one", "archived": False},
    ]
    report_path = tmp_path / "my_report.json"
    save_report(sample_repositories, str(report_path))
    with open(report_path, "r", encoding="utf-8") as report_file:
        generated_report = json.load(report_file)
    assert generated_report == sample_repositories


def test_requires_pull_request_finds_rule_after_other_rules():
    rules = [
        {"type": "required_status_checks"},
        {"type": "pull_request"},
    ]
    result = requires_pull_request(rules)
    assert result is True


def test_requires_pull_request_returns_false_when_missing():
    rules = [
        {"type": "required_status_checks"},
        {"type": "deletion"},
    ]
    result = requires_pull_request(rules)
    assert result is False


def test_requires_pull_request_returns_false_for_empty_rules():
    rules = []
    assert requires_pull_request(rules) is False


def test_fetch_branch_rules_returns_rules():
    response = Mock()
    response.status_code = 200
    response.json.return_value = [{"type": "pull_request"}]
    with patch("github_repo_auditor.requests.get", return_value=response):
        result = fetch_branch_rules("example/service", "main")
    assert result == [{"type": "pull_request"}]


def test_fetch_branch_rules_returns_none_for_403():
    response = Mock()
    response.status_code = 403
    with patch("github_repo_auditor.requests.get", return_value=response):
        result = fetch_branch_rules("example/service", "main")
    response.json.assert_not_called()
    assert result is None


def test_fetch_branch_rules_returns_none_on_timeout():
    with patch("github_repo_auditor.requests.get", side_effect=requests.exceptions.Timeout):
        result = fetch_branch_rules("example/service", "main")
    assert result is None


def test_evaluate_pull_request_rule_none():
    rules = None
    result = evaluate_pull_request_rule(rules)
    assert result == "UNKNOWN"


def test_evaluate_pull_request_rule_pass():
    rules = [{"type": "pull_request"}]
    assert evaluate_pull_request_rule(rules) == "PASS"


def test_evaluate_pull_request_rule_fail():
    rules = [{"type": "required_status_checks"}]
    assert evaluate_pull_request_rule(rules) == "FAIL"


def test_evaluate_pull_request_rule_empty():
    rules = []
    assert evaluate_pull_request_rule(rules) == "FAIL"


def test_status_to_exit_code_returns_one_for_fail():
    assert status_to_exit_code("FAIL") == 1


def test_build_github_headers_without_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    headers = build_github_headers()
    assert headers == {"Accept": "application/vnd.github+json"}


def test_build_github_headers_with_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    headers = build_github_headers()
    assert headers == {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer test-token",
    }


def test_get_required_approvals_finds_rule_after_other_rules():
    rules = [
        {"type": "required_status_checks"},
        {
            "type": "pull_request",
            "parameters": {"required_approving_review_count": 2},
        },
    ]
    result = get_required_approvals(rules)
    assert result == 2


def test_evaluate_required_approvals_returns_unknown():
    assert evaluate_required_approvals(None) == "UNKNOWN"


def test_evaluate_required_approvals_returns_fail():
    assert evaluate_required_approvals(0) == "FAIL"


def test_evaluate_required_approvals_returns_pass():
    assert evaluate_required_approvals(1) == "PASS"


def test_evaluate_required_approvals_returns_pass2():
    assert evaluate_required_approvals(2) == "PASS"


def test_aggregate_statuses_returns_unknown_for_empty_list():
    assert aggregate_statuses([]) == "UNKNOWN"


def test_aggregate_statuses_returns_both_pass():
    assert aggregate_statuses(["PASS", "PASS"]) == "PASS"


def test_aggregate_statuses_returns_pass_fail():
    assert aggregate_statuses(["PASS", "FAIL"]) == "FAIL"


def test_aggregate_statuses_returns_pass_unknown():
    assert aggregate_statuses(["PASS", "UNKNOWN"]) == "UNKNOWN"


def test_aggregate_statuses_returns_unknown_fail():
    assert aggregate_statuses(["UNKNOWN", "FAIL"]) == "FAIL"