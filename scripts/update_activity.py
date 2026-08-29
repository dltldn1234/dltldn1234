#!/usr/bin/env python3
import json, os, re, urllib.request
from datetime import datetime, timezone

USER = "dltldn1234"
README = "README.md"
START = "<!-- ACTIVITY:START -->"
END = "<!-- ACTIVITY:END -->"

token = os.environ.get("GITHUB_TOKEN", "")
headers = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "siwoo-system-profile",
}
if token:
    headers["Authorization"] = f"Bearer {token}"

req = urllib.request.Request(
    f"https://api.github.com/users/{USER}/events/public?per_page=30",
    headers=headers,
)

with urllib.request.urlopen(req, timeout=20) as response:
    events = json.load(response)

def ago(iso):
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    sec = max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))
    if sec < 3600:
        return f"{max(1, sec // 60)}m ago"
    if sec < 86400:
        return f"{sec // 3600}h ago"
    return f"{sec // 86400}d ago"

rows = []
for e in events:
    typ = e.get("type", "")
    repo = e.get("repo", {}).get("name", "")
    repo_url = f"https://github.com/{repo}"
    text = None
    icon = "›"

    if typ == "PushEvent":
        commits = e.get("payload", {}).get("commits", [])
        msg = commits[-1].get("message", "").splitlines()[0] if commits else "Pushed commits"
        text = f"**PUSH** → [{repo}]({repo_url}) — `{msg[:58]}`"
        icon = "↗"
    elif typ == "PullRequestEvent":
        action = e.get("payload", {}).get("action", "updated")
        pr = e.get("payload", {}).get("pull_request", {})
        title = pr.get("title", "Pull request")
        pr_url = pr.get("html_url", repo_url)
        text = f"**PR {action.upper()}** → [{title}]({pr_url}) · `{repo}`"
        icon = "⌁"
    elif typ == "IssuesEvent":
        action = e.get("payload", {}).get("action", "updated")
        issue = e.get("payload", {}).get("issue", {})
        title = issue.get("title", "Issue")
        issue_url = issue.get("html_url", repo_url)
        text = f"**ISSUE {action.upper()}** → [{title}]({issue_url}) · `{repo}`"
        icon = "#"
    elif typ == "CreateEvent":
        ref_type = e.get("payload", {}).get("ref_type", "repository")
        text = f"**CREATE** → `{ref_type}` in [{repo}]({repo_url})"
        icon = "+"

    if text:
        rows.append(f"{icon} {text} <sub>{ago(e['created_at'])}</sub>")
    if len(rows) >= 5:
        break

if not rows:
    rows = ["`No public activity detected.`"]

block = START + "\n\n" + "\n\n".join(rows) + "\n\n" + END
text = open(README, encoding="utf-8").read()
pattern = re.escape(START) + r".*?" + re.escape(END)
text = re.sub(pattern, block, text, flags=re.S)
open(README, "w", encoding="utf-8").write(text)
