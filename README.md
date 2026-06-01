# job-wrap

Analyze your git commit history across workspace directories to understand your contributions — then generate AI-ready context for updating your CV or drafting a farewell letter.

## Setup

Requires Python 3.11+ (no external dependencies).

Copy `config.example.toml` to `config.local.toml` and fill in your details. The local file is gitignored so your personal config stays off the repo.

```bash
cp config.example.toml config.local.toml
```

### Config file (`config.local.toml`)

| Field | Required | Description |
|---|---|---|
| `workspace_dirs` | Yes | Directories to scan recursively for git repos |
| `extra_emails` | Recommended | Work emails beyond what `git config user.email` returns per repo — ensures all your commits are captured |
| `notes` | Optional | Freeform context injected into the AI prompt (achievements, scope, tenure dates) |
| `supplementary` | Optional | Paths to text files (standup logs, achievement notes) appended as extra context |
| `exclude_projects` | Optional | Repo names to skip (personal projects, third-party libraries you have cloned) |
| `exclude_patterns` | Optional | Extra regex patterns for filenames to exclude from line counts |

Example:

```toml
workspace_dirs = ["~/workspace", "~/work"]

extra_emails = ["work@company.com", "old-work@previouscompany.com"]

notes = [
  "Led the platform migration Jan–Aug 2024",
  "Mentored two junior developers",
]

supplementary = ["~/notes/standups.md", "~/notes/achievements.txt"]

exclude_projects = ["azure-sdk-for-python", "kafka"]

exclude_patterns = ["^src/generated/"]
```

## Run

```bash
python analyze.py
```

This writes to `output/`:
- `analysis.md` — full commit history and stats (always written)
- `cv-context.md` — pointer to analysis + prompt for CV bullet points
- `farewell-context.md` — pointer to analysis + prompt for a farewell letter

### Options

```
python3 analyze.py [dirs...] [options]

  --config PATH              Config file (default: config.local.toml if present)
  --email EMAIL              Additional author email (repeatable)
  --note TEXT                Extra context to include in output (repeatable)
  --mode MODE                cv | farewell | all | raw  (default: all)
  --exclude PATTERN          Extra regex pattern for files to exclude from line counts
  --exclude-project PROJECT  Project name to exclude from analysis (repeatable)
  --output-dir DIR           Where to write output files (default: output/)
```

### What gets excluded from line counts

Lock files and generated files committed by convention are excluded:
`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `go.sum`, `Gemfile.lock`,
`poetry.lock`, `composer.lock`, `Cargo.lock`, `*.snap`, `*.pb.go`, `*_pb2.py`, etc.

Add project-specific patterns via `--exclude` or `exclude_patterns` in config.

### Handling migrated projects

If a project was migrated between organizations or remotes, job-wrap identifies projects by their **repository name** (not the full remote URL). This means if you have clones of the same project at different remotes—e.g., `github.com/old-org/my-project` and `github.com/new-org/my-project`—they'll be treated as a single project, with commits deduplicated by commit hash.

The output will list all local paths for that project, so you can see where each clone is located.

### Excluding projects

If you have clones of personal projects, third-party libraries, or other repos that shouldn't be included in your analysis, list them in your config:

```toml
exclude_projects = ["azure-sdk-for-python", "kafka", "spark", "my-personal-project"]
```

Or pass them on the command line:

```bash
python analyze.py --exclude-project azure-sdk-for-python --exclude-project kafka
```

Excluded projects won't appear in the output or contribute to statistics.

## AI prompt usage

Open an AI coding assistant in this folder:

```bash
claude  # Claude Code
# or
opencode
```

Then point it at an output file:

```
Read output/cv-context.md and do the task described at the bottom.
```

The context file points the AI to `analysis.md` and any supplementary files, then gives it the task. Direct it to write results wherever you need — your CV file, a new draft, etc.

### Customizing prompts

Edit `prompts/cv.md` or `prompts/farewell.md` to tune the AI instructions for your needs.
