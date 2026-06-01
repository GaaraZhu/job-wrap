#!/usr/bin/env python3
"""
job-wrap: Analyze git commit history across workspace directories.

Usage:
  python analyze.py [dirs...] [--config config.yaml] [--email work@co.com] [--note "extra context"]
                   [--mode cv|farewell|all|raw]
"""

import argparse
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import tomllib

# Files committed by convention but not meaningful contribution
DEFAULT_EXCLUDE_PATTERNS = [
    r"package-lock\.json$",
    r"yarn\.lock$",
    r"pnpm-lock\.yaml$",
    r"npm-shrinkwrap\.json$",
    r"Gemfile\.lock$",
    r"Pipfile\.lock$",
    r"poetry\.lock$",
    r"composer\.lock$",
    r"go\.sum$",
    r"Cargo\.lock$",
    r"\.terraform\.lock\.hcl$",
    r"\.snap$",
    r"_pb2\.py$",
    r"_pb2_grpc\.py$",
    r"\.pb\.go$",
]


def run(cmd, cwd=None):
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def find_git_repos(root):
    repos = []
    root = Path(root).expanduser().resolve()
    if not root.exists():
        print(f"  Warning: directory not found: {root}", file=sys.stderr)
        return repos
    for dirpath, dirnames, _ in os.walk(root):
        if ".git" in dirnames:
            repos.append(Path(dirpath))
            dirnames.clear()
    return repos


def normalize_remote(url):
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    if url.startswith("git@"):
        url = url[4:].replace(":", "/", 1)
    for prefix in ["https://", "http://"]:
        if url.startswith(prefix):
            url = url[len(prefix):]
            break
    return url.lower()


def get_repo_remote_key(repo_path):
    output = run(["git", "remote", "-v"], cwd=repo_path)
    
    # Try to find 'origin' remote first
    for line in output.splitlines():
        if "(fetch)" not in line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            name, url = parts[0], parts[1]
            if name == "origin":
                normalized = normalize_remote(url)
                # Extract just the repo name (last part) to handle migrations
                # e.g., github.com/jarden-digital/investcloud-function-apps -> investcloud-function-apps
                return normalized.split("/")[-1]
    
    # Fall back to first remote found
    for line in output.splitlines():
        if "(fetch)" not in line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            normalized = normalize_remote(parts[1])
            return normalized.split("/")[-1]
    
    return f"local:{repo_path.name}"


def get_local_author_email(repo_path):
    return run(["git", "config", "user.email"], cwd=repo_path)


def is_excluded(filename, patterns):
    return any(re.search(p, filename) for p in patterns)


def get_commits_and_stats(repo_path, emails, exclude_patterns):
    """
    Returns list of commit dicts with keys:
      hash, date, date_str, subject, lines_added, lines_removed
    """
    author_args = []
    for email in emails:
        author_args += ["--author", email]

    # Get commit hashes + dates + subjects
    log_output = run(
        ["git", "log"] + author_args + ["--format=%H\t%ai\t%s", "--all", "--no-merges"],
        cwd=repo_path,
    )
    if not log_output:
        return []

    commits_meta = {}
    for line in log_output.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            h, date_str, subject = parts
            try:
                date = datetime.fromisoformat(date_str[:19])
            except ValueError:
                date = None
            commits_meta[h] = {"hash": h, "date": date, "date_str": date_str[:10], "subject": subject}

    if not commits_meta:
        return []

    # Get numstat for those commits
    numstat_output = run(
        ["git", "log"] + author_args + ["--numstat", "--format=%H", "--all", "--no-merges"],
        cwd=repo_path,
    )

    # Parse numstat: blocks separated by commit hash lines
    lines_added_by_hash = defaultdict(int)
    lines_removed_by_hash = defaultdict(int)
    current_hash = None
    for line in numstat_output.splitlines():
        line = line.strip()
        if not line:
            continue
        if line in commits_meta:
            current_hash = line
            continue
        if current_hash is None:
            continue
        parts = line.split("\t")
        if len(parts) == 3:
            added_str, removed_str, filename = parts
            if is_excluded(filename, exclude_patterns):
                continue
            try:
                lines_added_by_hash[current_hash] += int(added_str)
                lines_removed_by_hash[current_hash] += int(removed_str)
            except ValueError:
                pass  # binary files show "-"

    commits = []
    for h, meta in commits_meta.items():
        commits.append({
            **meta,
            "lines_added": lines_added_by_hash[h],
            "lines_removed": lines_removed_by_hash[h],
        })

    return sorted(commits, key=lambda c: c["date"] or datetime.min)


def load_config(path):
    with open(path, "rb") as f:
        return tomllib.load(f)


def resolve_supplementary(paths):
    resolved = []
    for p in paths:
        p = Path(p).expanduser().resolve()
        if p.exists():
            resolved.append(str(p))
        else:
            print(f"  Warning: supplementary file not found: {p}", file=sys.stderr)
    return resolved


def load_prompt_template(mode):
    template_path = Path(__file__).parent / "prompts" / f"{mode}.md"
    if template_path.exists():
        return template_path.read_text().strip()
    return None


def format_analysis(projects, total_commits, total_added, total_removed, earliest, latest, notes):
    duration_days = (latest - earliest).days if earliest and latest else 0
    duration_months = duration_days // 30

    lines = []
    lines.append("# Job Wrap — Contribution Analysis")
    lines.append(f"\n_Generated: {datetime.now().strftime('%Y-%m-%d')}_")

    lines.append("\n## Overview")
    lines.append(f"- **Start:** {earliest.strftime('%B %Y') if earliest else 'N/A'}")
    lines.append(f"- **Duration:** {duration_months} months ({duration_days} days)")
    lines.append(f"- **Unique projects:** {len(projects)}")
    lines.append(f"- **Total commits:** {total_commits}  _(merge commits excluded)_")
    lines.append(f"- **Lines added:** {total_added:,}  _(lock files and generated code excluded)_")
    lines.append(f"- **Lines removed:** {total_removed:,}")
    lines.append(f"- **Net change:** {'+' if total_added - total_removed >= 0 else ''}{total_added - total_removed:,}")

    lines.append("\n## Projects\n")
    for p in projects:
        lines.append(f"### {p['name']}")
        lines.append(f"- **Remote:** `{p['remote']}`")
        lines.append(f"- **Period:** {p['first_commit']} → {p['last_commit']}")
        lines.append(f"- **Commits:** {p['commit_count']}")
        lines.append(f"- **Lines added:** {p['lines_added']:,} / removed: {p['lines_removed']:,}")
        if len(p["repos"]) > 1:
            lines.append(f"- **Repo paths:** {', '.join(p['repos'])}")
        lines.append("\n**Commit messages:**\n")
        for c in p["commits"]:
            lines.append(f"- `{c['date_str']}` {c['subject']}")
        lines.append("")

    if notes:
        lines.append("## Additional Context\n")
        for note in notes:
            lines.append(f"> {note}\n")

    return "\n".join(lines)


IM_FORMATTING = {
    "teams": (
        "Microsoft Teams — plain paragraphs only; **bold** and [link text](url) render correctly; "
        "do not use # headers, --- dividers, or bullet lists."
    ),
    "slack": (
        "Slack — plain paragraphs; *bold* (single asterisks), _italic_, and <url|link text> for hyperlinks; "
        "bullet lists with • work; do not use # headers or --- dividers."
    ),
    "email": (
        "Email — full markdown is supported; headers, bullet lists, **bold**, *italic*, and [links](url) all render correctly."
    ),
    "plain": (
        "Plain text — no markdown formatting at all; include hyperlinks as bare URLs."
    ),
}


def format_contact(contact):
    LABELS = {
        "email": "Email",
        "linkedin": "LinkedIn",
        "github": "GitHub",
        "phone": "Phone",
    }
    lines = []
    for key, label in LABELS.items():
        value = contact.get(key, "").strip()
        if value:
            lines.append(f"- **{label}:** {value}")
    # Include any extra keys not in the standard set
    for key, value in contact.items():
        if key not in LABELS and isinstance(value, str) and value.strip():
            lines.append(f"- **{key.capitalize()}:** {value.strip()}")
    return lines


def format_context(analysis_path, mode, supplementary_paths, contact=None, farewell_config=None):
    template = load_prompt_template(mode)
    lines = [
        f"Read `{analysis_path}` for the full contribution analysis, then complete the task below.",
    ]
    if supplementary_paths:
        lines.append("\n**Supplementary files** — read these for additional context:\n")
        for p in supplementary_paths:
            lines.append(f"- {p}")
    if contact:
        contact_lines = format_contact(contact)
        if contact_lines:
            lines.append("\n**Contact details** — use these in the output where relevant:\n")
            lines.extend(contact_lines)
    if mode == "farewell" and farewell_config:
        im = farewell_config.get("im", "").strip().lower()
        formatting_note = IM_FORMATTING.get(im)
        if formatting_note:
            lines.append(f"\n**Target platform:** {formatting_note}")
    lines += [
        "",
        "---",
        "",
        "## Your Task",
        "",
        template or f"(no prompt template found for mode: {mode})",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze git contribution history across workspaces")
    parser.add_argument("directories", nargs="*", help="Workspace directories to scan")
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--email", action="append", default=[], metavar="EMAIL",
                        help="Additional author email to include (repeatable)")
    parser.add_argument("--note", action="append", default=[], metavar="TEXT",
                        help="Extra context to include in output (repeatable)")
    parser.add_argument("--mode", choices=["cv", "farewell", "all", "raw"], default="all",
                        help="Output mode (default: all)")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN",
                        help="Additional regex patterns for files to exclude from line counts")
    parser.add_argument("--exclude-project", action="append", default=[], metavar="PROJECT",
                        help="Project names to exclude from analysis (repeatable)")
    parser.add_argument("--output-dir", default="output", help="Directory to write output files (default: output/)")
    args = parser.parse_args()

    # Load config
    config = {}
    if args.config:
        config = load_config(args.config)
    elif Path("config.local.toml").exists():
        config = load_config("config.local.toml")
    elif Path("config.toml").exists():
        config = load_config("config.toml")
        print("Warning: config.toml detected — consider renaming to config.local.toml to keep it gitignored", file=sys.stderr)

    dirs = args.directories or config.get("workspace_dirs", [])
    if not dirs:
        print("Error: no workspace directories specified. Pass as arguments or set workspace_dirs in config.yaml", file=sys.stderr)
        sys.exit(1)

    extra_emails = set(args.email) | set(config.get("extra_emails") or [])
    notes = args.note + (config.get("notes") or [])
    exclude_patterns = DEFAULT_EXCLUDE_PATTERNS + args.exclude + (config.get("exclude_patterns") or [])
    exclude_projects = set(args.exclude_project) | set(config.get("exclude_projects") or [])
    supplementary_paths = resolve_supplementary(config.get("supplementary") or [])
    contact = config.get("contact") or {}
    farewell_config = config.get("farewell") or {}
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Discover repos
    print("Scanning directories...", file=sys.stderr)
    all_repos = []
    for d in dirs:
        repos = find_git_repos(d)
        all_repos.extend(repos)
        print(f"  {d}: {len(repos)} repos found", file=sys.stderr)
    print(f"Total repos: {len(all_repos)}", file=sys.stderr)

    # Group by remote (deduplicate same project across paths)
    project_groups = defaultdict(list)
    for repo_path in all_repos:
        key = get_repo_remote_key(repo_path)
        project_groups[key].append(repo_path)

    print(f"Unique projects: {len(project_groups)}", file=sys.stderr)

    # Analyze each project
    projects = []
    for remote_key, repos in project_groups.items():
        # Skip excluded projects
        if remote_key in exclude_projects:
            print(f"  Excluding: {remote_key}", file=sys.stderr)
            continue
        
        # Collect author emails across all instances
        emails = set(extra_emails)
        for repo_path in repos:
            local_email = get_local_author_email(repo_path)
            if local_email:
                emails.add(local_email)

        if not emails:
            print(f"  Skipping {remote_key}: no author email found", file=sys.stderr)
            continue

        # Collect commits from all instances, deduplicate by hash
        all_commits = []
        seen_hashes = set()
        for repo_path in repos:
            commits = get_commits_and_stats(repo_path, emails, exclude_patterns)
            for c in commits:
                if c["hash"] not in seen_hashes:
                    seen_hashes.add(c["hash"])
                    all_commits.append(c)

        if not all_commits:
            continue

        all_commits.sort(key=lambda c: c["date"] or datetime.min)

        project_name = remote_key.split("/")[-1] if not remote_key.startswith("local:") else remote_key[6:]
        projects.append({
            "name": project_name,
            "remote": remote_key,
            "repos": [str(r) for r in repos],
            "commit_count": len(all_commits),
            "first_commit": all_commits[0]["date_str"],
            "last_commit": all_commits[-1]["date_str"],
            "lines_added": sum(c["lines_added"] for c in all_commits),
            "lines_removed": sum(c["lines_removed"] for c in all_commits),
            "commits": all_commits,
        })

    projects.sort(key=lambda p: p["first_commit"])

    # Aggregate totals
    all_commits_flat = [c for p in projects for c in p["commits"]]
    total_commits = len(all_commits_flat)
    total_added = sum(p["lines_added"] for p in projects)
    total_removed = sum(p["lines_removed"] for p in projects)
    dates = [c["date"] for c in all_commits_flat if c["date"]]
    earliest = min(dates) if dates else None
    latest = max(dates) if dates else None

    if not projects:
        print("No commits found. Check your directories and email addresses.", file=sys.stderr)
        sys.exit(1)

    # Always write analysis.md
    analysis_path = output_dir / "analysis.md"
    analysis_path.write_text(format_analysis(
        projects, total_commits, total_added, total_removed,
        earliest, latest, notes,
    ))
    print(f"Written: {analysis_path}", file=sys.stderr)

    # Write context files for cv/farewell modes
    context_modes = ["cv", "farewell"] if args.mode == "all" else ([] if args.mode == "raw" else [args.mode])
    for mode in context_modes:
        out_path = output_dir / f"{mode}-context.md"
        out_path.write_text(format_context(analysis_path, mode, supplementary_paths, contact, farewell_config))
        print(f"Written: {out_path}", file=sys.stderr)

    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
