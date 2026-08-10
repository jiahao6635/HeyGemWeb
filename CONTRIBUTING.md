# Contributing to HeyGemWeb

Thank you for helping improve HeyGemWeb. The project prioritizes reproducible fixes for real self-hosted deployments, clear evidence, and changes that can be reviewed without access to private media or credentials.

## Before opening an issue

- Search existing issues first.
- Remove credentials, private URLs, personal media, and access tokens from logs.
- Include your operating system, Python version, Gradio version, backend version, and exact reproduction steps.
- Explain whether `ffmpeg` and `ffprobe` are installed and available on `PATH`.

## Development setup

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Use non-production credentials and a disposable `HEYGEM_BASE_DIR` while developing.

## Validation

Run the checks relevant to every pull request:

```bash
python -m compileall -q app.py config.py services
python -m unittest discover -s tests -v
bash -n deploy.sh manage.sh
```

Tests must not contact real backend services, require a GPU, or use private media. Mock external HTTP and FFmpeg behavior where needed.

## Pull requests

- Keep each pull request focused on one problem.
- Add or update tests for deterministic behavior.
- Update both English and Chinese documentation when user-facing behavior changes.
- Describe validation commands and any untested deployment assumptions.
- Do not include generated media, task-state files, logs, credentials, or model artifacts.

By submitting a contribution, you agree that it may be licensed under the Apache License 2.0 used by this repository.
