# HeyGem Video Processing Interface

这是一个使用Gradio构建的Web界面，用于与HeyGem后端API进行交互。该界面提供了以下功能：

1. 模型训练：上传视频文件进行训练
2. 音频合成：使用训练好的模型生成音频
3. 视频合成：将生成的音频与原始视频结合
4. 进度查询：查看异步任务的执行进度

## 安装

### 本地开发环境

1. 克隆项目到本地
2. 安装依赖：
```bash
pip install -r requirements.txt
```

### Linux服务器部署

1. 克隆项目到服务器
2. 给部署脚本添加执行权限：
```bash
chmod +x deploy.sh
```
3. 运行部署脚本：
```bash
./deploy.sh
```

部署脚本会自动：
- 创建必要的目录结构
- 设置适当的文件权限
- 安装依赖
- 创建并启动systemd服务

## 配置

在 `config.py` 文件中配置以下内容：

- API_BASE_URL：后端API的基础URL
- BASE_DIR：部署目录（默认为 /opt/heygem）
- SERVER_HOST：服务器监听地址（默认为 0.0.0.0）
- SERVER_PORT：服务器端口（默认为 7860）

## 运行

### 本地开发环境
```bash
python app.py
```

### Linux服务器
服务会自动启动并运行在后台。可以通过以下命令管理服务：

- 查看服务状态：
```bash
sudo systemctl status heygem
```

- 查看服务日志：
```bash
sudo journalctl -u heygem -f
```

- 重启服务：
```bash
sudo systemctl restart heygem
```

- 停止服务：
```bash
sudo systemctl stop heygem
```

## 使用说明

1. 模型训练
   - 在"Model Training"标签页上传视频文件
   - 点击"Start Training"开始训练
   - 保存返回的Task ID用于后续操作

2. 音频合成
   - 在"Audio Synthesis"标签页输入Task ID和要合成的文本
   - 点击"Synthesize Audio"开始合成
   - 保存返回的新Task ID

3. 视频合成
   - 在"Video Combination"标签页输入Task ID
   - 点击"Combine Video"开始合成
   - 保存返回的新Task ID

4. 进度查询
   - 在"Progress Check"标签页输入Task ID
   - 点击"Check Progress"查看进度

## 注意事项

- 确保后端服务正在运行
- 支持的视频格式：MP4, AVI, MOV, MKV
- 所有文件操作都在服务器上进行，请确保有足够的存储空间
- 默认情况下，Web界面可以通过 http://服务器IP:7860 访问
- 如果需要更改端口，请修改 config.py 中的 SERVER_PORT
- 建议在生产环境中配置反向代理（如Nginx）和SSL证书 