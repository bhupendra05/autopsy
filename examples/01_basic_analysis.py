"""Example: analyze a production incident from logs + git + deploys."""
import os
from pathlib import Path

import anthropic
from autopsy import analyze, ParsedInput
from autopsy.parsers import parse_logs, parse_git_log, parse_deploys
from autopsy.report import print_terminal

HERE = Path(__file__).parent

log_content = (HERE / "sample_incident.log").read_text()
git_content = (HERE / "sample_git.log").read_text()
deploy_content = (HERE / "sample_deploys.json").read_text()

parsed = ParsedInput(
    raw_logs=log_content,
    raw_git=git_content,
    raw_deploys=deploy_content,
    events=parse_logs(log_content) + parse_git_log(git_content) + parse_deploys(deploy_content),
)

client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var
postmortem = analyze(parsed, client, thinking_budget=8000)

print_terminal(postmortem)
