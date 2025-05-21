#!/bin/bash

# 设置错误时退出
set -e

# 创建必要的目录
sudo mkdir -p /opt/heygem/face2face/{temp,result,log}
sudo mkdir -p /opt/heygem/voice/data/{origin_audio,processed_audio}
sudo chown -R $USER:$USER /opt/heygem
sudo chmod -R 755 /opt/heygem

# 安装系统依赖
sudo yum update -y
sudo yum install -y python3 python3-pip python3-devel gcc ffmpeg ffmpeg-devel

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装Python依赖
pip install --upgrade pip
pip install -r requirements.txt

# 创建systemd服务文件
sudo tee /etc/systemd/system/heygem-web.service << EOF
[Unit]
Description=HeyGem Web Interface
After=network.target

[Service]
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin"
ExecStart=$(pwd)/venv/bin/gunicorn -w 4 -b 0.0.0.0:2531 app:demo.server
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 重新加载systemd配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl enable heygem-web
sudo systemctl start heygem-web

# 检查服务状态
sudo systemctl status heygem-web

echo "部署完成！服务已启动在 http://服务器IP:2531" 