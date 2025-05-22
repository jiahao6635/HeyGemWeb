#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

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

# 启动服务
start_service() {
    if [ -f "$PID_FILE" ]; then
        echo "服务已经在运行中 (PID: $(cat $PID_FILE))"
        return
    fi
    
    echo "启动 HeyGem Web 服务..."
    gunicorn -w 4 -b 0.0.0.0:2531 app:demo.server --pid "$PID_FILE" --daemon
    echo "服务已启动，PID: $(cat $PID_FILE)"
    echo "访问地址: http://localhost:2531"
}

# 停止服务
stop_service() {
    if [ ! -f "$PID_FILE" ]; then
        echo "服务未运行"
        return
    fi
    
    PID=$(cat "$PID_FILE")
    echo "停止服务 (PID: $PID)..."
    kill $PID
    rm "$PID_FILE"
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
            echo "访问地址: http://localhost:2531"
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
        tail -f logs/app.log
    else
        echo "服务未运行，无法查看日志"
    fi
}

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