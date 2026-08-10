# HeyGemWeb 中文说明

[English README](../README.md)

HeyGemWeb 是一个独立维护的 Gradio Web 界面与工作流层，用于连接自行部署的 HeyGem 兼容数字人服务。它将模型训练素材、语音合成、视频生成任务、进度和作品管理集中在一个界面中。

> **项目状态：维护恢复阶段。** 后端适配器仍处于实验阶段，尚未通过完整 HeyGem 部署的端到端测试。当前重点是处理真实部署问题、增加可重复测试和 CI、完善文档，并加强自托管场景的安全性。

HeyGemWeb **不包含** HeyGem 后端、模型权重或媒体生成服务。你必须单独部署兼容的语音和视频服务；这些服务与模型可能适用独立的许可证和使用条款。

## 当前能力

- Gradio 服务端认证与管理界面
- 模型训练、语音合成和视频生成工作流
- 支持状态、优先级、重试、超时和取消的本地任务队列
- 按用户组织媒体文件与生成作品
- MP4 上传校验、大小限制、文件清理和缩略图生成
- 通过环境变量配置后端、存储、账号和服务器

## 环境要求

- Python 3.10 或更高版本
- 当前经过验证的部署路径为 Linux
- 系统已安装 `ffmpeg` 和 `ffprobe`
- 单独部署的 TTS 服务，默认端口 `18180`
- 单独部署的视频生成服务，默认端口 `8383`
- 足够的媒体文件存储空间

`ffmpeg-python` 依赖不能替代系统中的 `ffmpeg` 和 `ffprobe` 命令。

## 快速开始

```bash
git clone https://github.com/jiahao6635/HeyGemWeb.git
cd HeyGemWeb

python3.10 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

cp .env.example .env
```

启动前编辑 `.env`，至少配置一个登录账号以及与你的后端部署一致的地址：

当前 TTS 与视频适配器面向已有 HeyGem 兼容部署所使用的接口契约。正式依赖前，请使用非敏感测试素材对你的具体后端版本进行验证。

```dotenv
USER_1_NAME=admin
USER_1_PASSWORD=请替换为足够长的随机密码

HEYGEM_TTS_URL=http://localhost:18180
HEYGEM_VIDEO_URL=http://localhost:8383
HEYGEM_BASE_DIR=./heygem_data
```

运行：

```bash
python app.py
```

默认访问地址为 `http://localhost:2531`。项目没有默认账号密码；可以通过 `USER_1_NAME` / `USER_1_PASSWORD` 到 `USER_10_NAME` / `USER_10_PASSWORD` 配置最多十组凭据。至少要提供一组完整配置，否则服务会拒绝启动。每个登录用户名也会作为对应媒体文件的存储命名空间。

## 配置项

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `HEYGEM_TTS_URL` | `http://localhost:18180` | 兼容的语音服务地址 |
| `HEYGEM_VIDEO_URL` | `http://localhost:8383` | 兼容的视频生成服务地址 |
| `HEYGEM_BASE_DIR` | Linux 为 `/root/heygem_data` | 上传文件、生成媒体、任务状态和日志目录 |
| `HEYGEM_HOST` | `0.0.0.0` | Gradio 监听地址 |
| `HEYGEM_PORT` | `2531` | Gradio 端口 |
| `HEYGEM_LOG_LEVEL` | `INFO` | 日志级别 |
| `HEYGEM_MAX_UPLOAD_MB` | `500` | MP4 最大上传大小 |
| `USER_1_NAME` ... `USER_10_NAME` | 未设置 | 登录用户名 |
| `USER_1_PASSWORD` ... `USER_10_PASSWORD` | 未设置 | 登录密码 |

## 开发与验证

自动化测试不会访问真实 HeyGem 服务、执行媒体生成或要求 GPU：

```bash
python -m compileall -q app.py config.py services
python -m unittest discover -s tests -v
bash -n deploy.sh manage.sh
```

提交改动前请阅读 [CONTRIBUTING.md](../CONTRIBUTING.md)。

## 安全提示

- 上传媒体、生成媒体、日志和账号凭据都应按敏感数据处理。
- 不要提交 `.env` 或真实密码。
- 对外提供服务前，应配置 HTTPS、反向代理和额外访问控制。
- Gradio 服务端认证会保护界面和 API 端点，但不包含 MFA、登录限速或完整的公网多租户安全边界。
- 当前应用只接受 MP4 上传。
- 安全问题请按照 [SECURITY.md](../SECURITY.md) 私下报告。

## 当前限制

- 自动化验证目前只覆盖 Linux 部署路径。
- 后端兼容性取决于单独部署服务的 API 行为。
- CI 使用 mock 和冒烟检查，不执行端到端 TTS/视频生成、真实 FFmpeg、GPU、大文件或浏览器工作流。
- 多用户隔离与并发仍需要更多安全和负载测试。
- `deploy.sh` 和 `manage.sh` 是保留的旧版辅助脚本，生产使用前必须针对具体发行版重新审查。

## 许可证与项目关系

本仓库中的代码和文档采用 [Apache License 2.0](../LICENSE)。

HeyGemWeb 是独立的社区项目，与 HeyGem 维护方不存在隶属或背书关系。本仓库的 Apache-2.0 许可证不覆盖单独获取的后端、模型、商标或媒体资产，详见 [NOTICE](../NOTICE)。
