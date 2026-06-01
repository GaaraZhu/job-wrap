# job-wrap

Analyze your git commit history across workspace directories to understand your contributions — then generate AI-ready context for updating your CV or drafting a farewell letter.

## Workflow

**Step 1 — Configure**

Copy `config.example.yaml` to `config.local.yaml` and fill in your details. The local file is gitignored so your personal config stays off the repo.

```bash
cp config.example.yaml config.local.yaml
```

**Step 2 — Generate output files**

```bash
python3 analyze.py
```

This writes to `output/`:
- `cv-context.md` — commit history + prompt for CV bullet points
- `farewell-context.md` — commit history + prompt for a farewell letter

**Step 3 — Open an AI coding assistant in this folder**

```bash
claude  # Claude Code
# or
opencode
```

Then ask it to action the file, for example:

```
Read output/cv-context.md and do the task described at the bottom.
```

The AI gets the full commit history, supplementary context, and instructions all in one file. Direct it to write results wherever you need — your CV file, a new draft, etc.

## Setup

```bash
mise install       # installs Python 3.12
mise run install   # installs pyyaml
```

## Options

```
python3 analyze.py [dirs...] [options]

  --config PATH       Config file (default: config.yaml if present)
  --email EMAIL       Additional author email (repeatable)
  --note TEXT         Extra context to include in output (repeatable)
  --mode MODE         cv | farewell | all | raw  (default: all)
  --exclude PATTERN   Extra regex pattern for files to exclude from line counts
  --output-dir DIR    Where to write output files (default: output/)
```

## Config file (`config.local.yaml`)

```yaml
workspace_dirs:
  - ~/workspace
extra_emails:
  - work@company.com
supplementary:
  - ~/notes/standups.md
notes:
  - "Led the platform migration Jan–Aug 2024"
```

## What gets excluded from line counts

Lock files and generated files committed by convention are excluded:
`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `go.sum`, `Gemfile.lock`,
`poetry.lock`, `composer.lock`, `Cargo.lock`, `*.snap`, `*.pb.go`, `*_pb2.py`, etc.

Add project-specific patterns via `--exclude` or `exclude_patterns` in config.

## Customizing prompts

Edit `prompts/cv.md` or `prompts/farewell.md` to tune the AI instructions for your needs.
