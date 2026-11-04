import argparse
import json
import os
import sys

import requests


def build_github_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def inspect_repository(repo_name: str) -> dict | None:
    url = f"https://api.github.com/repos/{repo_name}"
    try:
        response = requests.get(url, timeout=10, headers=build_github_headers())
        if response.status_code == 200:
            repo = response.json()
            repository = repo['full_name']
            repository_is_private = repo['private']
            repository_default_branch = repo['default_branch']
            repository_is_archived = repo["archived"]
            result = {
                "name": repository,
                "private": repository_is_private,
                "default_branch": repository_default_branch,
                "archived": repository_is_archived
            }
            return result
        else:
            print(f"Repository {repo_name}: request failed with status code {response.status_code}")

    except requests.exceptions.Timeout:
        print(f"Repository {repo_name}: Request timed out")
    except requests.exceptions.ConnectionError:
        print(f"Repository {repo_name}: Could not connect to the server")
    except requests.exceptions.JSONDecodeError:
        print(f"Repository {repo_name}: Response is not valid JSON")


def fetch_branch_rules(repo_name: str, branch: str) -> list | None:
    url = f"https://api.github.com/repos/{repo_name}/rules/branches/{branch}"
    try:
        response = requests.get(url, timeout=10, headers=build_github_headers())
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            print(f"Repository {repo_name} with branch {branch} responded with HTTP code {response.status_code}")
            return None

    except requests.exceptions.Timeout:
        print(f"Repository {repo_name} using {branch}: Request timed out")
    except requests.exceptions.ConnectionError:
        print(f"Repository {repo_name} using {branch}: Could not connect to the server")
    except requests.exceptions.JSONDecodeError:
        print(f"Repository {repo_name} using {branch}: Response is not valid JSON")


def filter_active_repositories(repositories: list) -> list:
    active_repositories = []
    for repository in repositories:
        if not repository['archived']:
            active_repositories.append(repository)
    return active_repositories


def requires_pull_request(rules: list) -> bool:
    for rule in rules:
        if rule['type'] == "pull_request":
            return True
    return False


def evaluate_pull_request_rule(rules: list | None) -> str:
    if rules is None:
        return "UNKNOWN"
    if requires_pull_request(rules):
        return "PASS"
    else:
        return "FAIL"


def get_required_approvals(rules: list) -> int | None:
    for rule in rules:
        if rule['type'] == 'pull_request':
            return rule['parameters']['required_approving_review_count']
    return None


def evaluate_required_approvals(approvals: int | None) -> str:
    if approvals is None:
        return "UNKNOWN"
    elif approvals == 0:
        return "FAIL"
    else:
        return "PASS"


def save_report(results: list, filename: str) -> None:
    with open(filename, "w", encoding="utf-8") as report_file:
        json.dump(results, report_file, indent=2)


def status_to_exit_code(status: str) -> int:
    if status == "PASS":
        return 0
    elif status == "FAIL":
        return 1
    else:
        return 2


def aggregate_statuses(statuses: list[str]) -> str:
    if not statuses: # Jeżeli statuses jest  pustą listą
        return "UNKNOWN"
    if "FAIL" in statuses:
        return "FAIL"
    if "UNKNOWN" in statuses:
        return "UNKNOWN"
    return "PASS"


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect GitHub repositories")
    parser.add_argument("--repo", required=True, help="Repository in owner/name format")
    parser.add_argument("--output", default="report.json", help="Output file")
    args = parser.parse_args()
    repos_list = [args.repo]
    results = []

    for repo in repos_list:
        inspection_result = inspect_repository(repo)
        if inspection_result is not None:
            results.append(inspection_result)
            print(f"Repository: {inspection_result['name']}")
            print(f"Private: {inspection_result['private']}")
            print(f"Default branch: {inspection_result['default_branch']}")
            print(f"Archived: {inspection_result['archived']}")
            rules = fetch_branch_rules(repo, inspection_result["default_branch"])
            if rules is not None:
                inspection_result["required_approvals"] = get_required_approvals(rules)
            else:
                inspection_result["required_approvals"] = None
            inspection_result["required_approvals_status"] = evaluate_required_approvals(
                inspection_result["required_approvals"])
            print(f"Required approvals status: {inspection_result['required_approvals_status']}")
            inspection_result["pull_request_rule_status"] = evaluate_pull_request_rule(rules)
            print(f"Pull request rule status: {inspection_result['pull_request_rule_status']}")
            statuses = [
                inspection_result["pull_request_rule_status"],
                inspection_result["required_approvals_status"],
            ]
            inspection_result["overall_status"] = aggregate_statuses(statuses)
            print(f"Overall status: {inspection_result['overall_status']}")
        print()

    if results:
        active_repositories = filter_active_repositories(results)
        print("Active repositories:", len(active_repositories))
        save_report(results, args.output)
        return status_to_exit_code(results[0]["overall_status"])
    else:
        print("No successful results. Report was not saved.")
        return 2

if __name__ == "__main__":
    sys.exit(main())