#!/usr/bin/env python3
import html
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
seen_create_events = set()
for e in events:
    typ = e.get("type", "")
    repo = e.get("repo", {}).get("name", "")
    repo_url = f"https://github.com/{repo}"
    label = None
    detail = None

    if typ == "PushEvent":
        commits = e.get("payload", {}).get("commits", [])
        msg = commits[-1].get("message", "").splitlines()[0] if commits else "Pushed commits"
        label = "↗ PUSH"
        detail = msg[:72]
    elif typ == "PullRequestEvent":
        action = e.get("payload", {}).get("action", "updated")
        pr = e.get("payload", {}).get("pull_request", {})
        title = pr.get("title", "Pull request")
        pr_url = pr.get("html_url", repo_url)
        label = "◆ MERGED" if action == "closed" and pr.get("merged") else "⌁ PULL"
        detail = title[:72]
        repo_url = pr_url
    elif typ == "IssuesEvent":
        action = e.get("payload", {}).get("action", "updated")
        issue = e.get("payload", {}).get("issue", {})
        title = issue.get("title", "Issue")
        issue_url = issue.get("html_url", repo_url)
        label = "! ISSUE"
        detail = f"{action.upper()} · {title[:62]}"
        repo_url = issue_url
    elif typ == "CreateEvent":
        ref_type = e.get("payload", {}).get("ref_type", "repository")
        ref = e.get("payload", {}).get("ref") or ref_type
        create_key = (repo, ref_type, ref)
        if create_key in seen_create_events:
            continue
        seen_create_events.add(create_key)
        label = "⌇ BRANCH" if ref_type == "branch" else "+ CREATE"
        detail = f"{ref_type.upper()} · {ref}"[:72]

    if label:
        safe_repo = html.escape(repo)
        safe_url = html.escape(repo_url, quote=True)
        safe_label = html.escape(label)
        safe_detail = html.escape(detail)
        rows.append(
            "<tr>"
            f'<td width="96"><code>{safe_label}</code></td>'
            f'<td><a href="{safe_url}"><strong>{safe_repo}</strong></a><br/>'
            f"<sub>{safe_detail}</sub></td>"
            f'<td align="right"><sub>{ago(e["created_at"])}</sub></td>'
            "</tr>"
        )
    if len(rows) >= 5:
        break

if not rows:
    rows = ['<tr><td><sub>NO PUBLIC ACTIVITY DETECTED // STANDING BY</sub></td></tr>']

block = (
    START
    + "\n\n<table>\n"
    + '<tr><td colspan="3"><sub>SYS.ACTIVITY.LOG // LIVE FEED</sub></td></tr>\n'
    + "\n".join(rows)
    + "\n</table>\n\n"
    + END
)
text = open(README, encoding="utf-8").read()
pattern = re.escape(START) + r".*?" + re.escape(END)
text = re.sub(pattern, block, text, flags=re.S)
open(README, "w", encoding="utf-8").write(text)
