# GitHub Repo Auditor

A Python CLI tool that checks selected GitHub ruleset requirements
for a repository's default branch.

It checks whether a pull request rule is present and whether it
requires at least one approving review.

Results are displayed in the terminal and saved to a JSON report.
This tool does not currently evaluate classic branch protection rules.

## Usage

```
uv run python github_repo_auditor.py  --repo pablo222/ai-task-manager 
```


## Example JSON report
```
[
  {
    "name": "pablo222/ai-task-manager",
    "private": false,
    "default_branch": "main",
    "archived": false,
    "required_approvals": 0,
    "required_approvals_status": "FAIL",
    "pull_request_rule_status": "PASS",
    "overall_status": "FAIL"
  }
]
```
## Exit codes

- `0` — PASS: all evaluated checks passed.
- `1` — FAIL: at least one check failed.
- `2` — UNKNOWN: the audit could not determine an overall result, or repository data could not be retrieved.