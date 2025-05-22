#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        echo "错误: 端口 $port 已被占用"
        exit 1
    fi
}

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 检查 gunicorn 是否安装
if ! pip show gunicorn > /dev/null; then
    echo "安装 gunicorn..."
    pip install gunicorn
fi

# 进程ID文件
PID_FILE="$SCRIPT_DIR/gunicorn.pid"
PORT=2531
HOST="0.0.0.0"  # 允许所有IP访问

# 启动服务
start_service() {
    if [ -f "$PID_FILE" ]; then
        echo "服务已经在运行中 (PID: $(cat $PID_FILE))"
        return
    fi
    
    # 检查端口
    check_port $PORT
    
    echo "启动 HeyGem Web 服务..."
    echo "监听地址: $HOST:$PORT"
    
    # 使用 nohup 确保进程在后台运行
    nohup gunicorn -w 4 -b $HOST:$PORT app:demo.server \
        --pid "$PID_FILE" \
        --daemon \
        --log-file logs/gunicorn.log \
        --access-logfile logs/access.log \
        --error-logfile logs/error.log \
        --capture-output \
        --enable-stdio-inheritance \
        --timeout 120 \
        --keep-alive 5 \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --worker-class sync \
        --workers 4 \
        --threads 2 \
        --worker-connections 1000 \
        --backlog 2048 \
        --graceful-timeout 30 \
        --reload > logs/startup.log 2>&1
    
    # 等待服务启动
    sleep 2
    
    if [ -f "$PID_FILE" ]; then
        echo "服务已启动，PID: $(cat $PID_FILE)"
        echo "访问地址: http://服务器IP:$PORT"
        echo "日志文件: logs/gunicorn.log"
    else
        echo "服务启动失败，请检查日志文件"
        exit 1
    fi
}

# 停止服务
stop_service() {
    if [ ! -f "$PID_FILE" ]; then
        echo "服务未运行"
        return
    fi
    
    PID=$(cat "$PID_FILE")
    echo "停止服务 (PID: $PID)..."
    
    # 尝试优雅停止
    kill -TERM $PID
    
    # 等待进程结束
    for i in {1..10}; do
        if ! ps -p $PID > /dev/null; then
            break
        fi
        sleep 1
    done
    
    # 如果进程还在运行，强制结束
    if ps -p $PID > /dev/null; then
        echo "服务未能在10秒内停止，强制结束进程..."
        kill -9 $PID
    fi
    
    rm -f "$PID_FILE"
    echo "服务已停止"
}

# 重启服务
restart_service() {
    stop_service
    sleep 2
    start_service
}

# 查看服务状态
status_service() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null; then
            echo "服务正在运行 (PID: $PID)"
            echo "监听地址: $HOST:$PORT"
            echo "日志文件: logs/gunicorn.log"
        else
            echo "服务进程已停止，但PID文件仍存在"
            rm "$PID_FILE"
        fi
    else
        echo "服务未运行"
    fi
}

# 查看日志
view_logs() {
    if [ -f "$PID_FILE" ]; then
        tail -f logs/gunicorn.log
    else
        echo "服务未运行，无法查看日志"
    fi
}

# 确保日志目录存在
mkdir -p logs

# 命令行参数处理
case "$1" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        status_service
        ;;
    logs)
        view_logs
        ;;
    *)
        echo "使用方法: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac

exit 0 