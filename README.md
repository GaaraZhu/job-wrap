# job-wrap

Analyze your git commit history across workspace directories to understand your contributions — then generate AI-ready context for updating your CV or drafting a farewell letter.

## Quick start

```bash
python analyze.py ~/workspace ~/work --email work@company.com
```

This writes two files:
- `cv-context.md` — commit history + prompt for CV bullet points
- `farewell-context.md` — commit history + prompt for a farewell message

Paste either file into Claude (or any LLM) to generate the output.

## Options

```
python analyze.py [dirs...] [options]

  --config PATH       Config file (default: config.yaml if present)
  --email EMAIL       Additional author email (repeatable)
  --note TEXT         Extra context to include in output (repeatable)
  --mode MODE         cv | farewell | all | raw  (default: all)
  --exclude PATTERN   Extra regex pattern for files to exclude from line counts
  --output-dir DIR    Where to write output files (default: current directory)
```

## Config file

Copy `config.yaml` and fill in your details — avoids passing flags every time.

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

## Requirements

- Python 3.8+
- `pyyaml` for config file support: `pip install pyyaml`
