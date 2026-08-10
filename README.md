# HeyGemWeb

[![CI](https://github.com/jiahao6635/HeyGemWeb/actions/workflows/ci.yml/badge.svg)](https://github.com/jiahao6635/HeyGemWeb/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

[中文说明](docs/README.zh-CN.md)

HeyGemWeb is an independent, community-maintained Gradio web interface and workflow layer for self-hosted HeyGem-compatible digital-human services. It provides one place to manage model-training inputs, speech synthesis, video-generation tasks, progress, and generated media.

> **Project status:** maintenance revival. The backend adapters are experimental and are not yet covered by an end-to-end HeyGem deployment test. The current focus is resolving reported deployment problems, adding deterministic tests and CI, improving documentation, and strengthening safe self-hosted operation.

HeyGemWeb does **not** include a HeyGem backend, model weights, or media-generation services. You must deploy compatible TTS and video services separately. Those services and assets may have their own licenses and usage terms.

## What it provides

- Gradio server-side authentication and a management interface
- Model-training, speech-synthesis, and video-generation workflows
- A local task queue with status, priority, retry, timeout, and cancellation support
- Per-user media directories and generated-work management
- MP4 upload validation, size limits, cleanup tools, and thumbnail generation
- Environment-based configuration for backend endpoints, storage, accounts, and server settings

## Requirements

- Python 3.10 or later
- Linux for the currently verified deployment path
- System installations of `ffmpeg` and `ffprobe`
- A separately deployed TTS service, normally on port `18180`
- A separately deployed video-generation service, normally on port `8383`
- Sufficient disk space for uploaded and generated media

The Python package `ffmpeg-python` does not replace the system `ffmpeg` and `ffprobe` executables.

## Quick start

```bash
git clone https://github.com/jiahao6635/HeyGemWeb.git
cd HeyGemWeb

python3.10 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

cp .env.example .env
```

Edit `.env` before starting. At minimum, configure one username/password pair and the paths or URLs used by your deployment.

The TTS and video adapters currently target the API contracts used by existing HeyGem-compatible deployments. Validate them against your exact backend version with non-sensitive test media before relying on the service.

```dotenv
USER_1_NAME=admin
USER_1_PASSWORD=replace-with-a-long-random-password

HEYGEM_TTS_URL=http://localhost:18180
HEYGEM_VIDEO_URL=http://localhost:8383
HEYGEM_BASE_DIR=./heygem_data
```

Start the web interface:

```bash
python app.py
```

The default address is `http://localhost:2531`. There is no default username or password; credentials come from `USER_1_NAME` / `USER_1_PASSWORD` through `USER_10_NAME` / `USER_10_PASSWORD`. At least one complete pair is required or the server refuses to start. Each authenticated username is also used as its media-storage namespace.

## Configuration

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `HEYGEM_TTS_URL` | `http://localhost:18180` | Compatible speech service |
| `HEYGEM_VIDEO_URL` | `http://localhost:8383` | Compatible video-generation service |
| `HEYGEM_BASE_DIR` | `/root/heygem_data` on Linux | Uploaded files, generated media, task state, and logs |
| `HEYGEM_HOST` | `0.0.0.0` | Gradio bind address |
| `HEYGEM_PORT` | `2531` | Gradio port |
| `HEYGEM_LOG_LEVEL` | `INFO` | Application log level |
| `HEYGEM_MAX_UPLOAD_MB` | `500` | Maximum uploaded MP4 size |
| `USER_1_NAME` ... `USER_10_NAME` | unset | Login usernames |
| `USER_1_PASSWORD` ... `USER_10_PASSWORD` | unset | Login passwords |

## Development

The automated test path does not call real HeyGem services, execute media generation, or require a GPU.

```bash
python -m compileall -q app.py config.py services
python -m unittest discover -s tests -v
bash -n deploy.sh manage.sh
```

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Security and deployment notes

- Treat uploaded media, generated media, logs, and credentials as sensitive.
- Use long, unique passwords; never commit `.env` or real credentials.
- Put the service behind HTTPS and an authenticated reverse proxy before exposing it outside a trusted network.
- Gradio server-side authentication protects the UI and API endpoints, but it does not provide MFA, rate limiting, or a complete public multi-tenant security boundary.
- Only MP4 uploads are currently accepted by the application.
- Review [SECURITY.md](SECURITY.md) before reporting a vulnerability.

## Current limitations

- Linux is the only deployment path currently covered by automated verification.
- Backend compatibility depends on the separately deployed services and their API behavior.
- CI uses mocks and smoke checks; it does not execute end-to-end TTS/video generation, real FFmpeg, GPU, large-file, or browser workflows.
- Multi-user isolation and concurrency behavior need additional security and load testing.
- `deploy.sh` and `manage.sh` are retained as legacy helpers and should be reviewed for your distribution before production use.

## License and project relationship

Code and documentation in this repository are licensed under the [Apache License 2.0](LICENSE).

HeyGemWeb is an independent community project. It is not affiliated with or endorsed by the maintainers of HeyGem, and the Apache-2.0 license in this repository does not grant rights to separately obtained backends, models, trademarks, or media assets. See [NOTICE](NOTICE).
