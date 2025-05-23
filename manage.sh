#!/bin/bash

# 设置错误时退出
set -e

# 获取进程ID的函数
get_pid() {
    pgrep -f "gunicorn.*app:demo.server" || echo ""
}

# 启动服务
start_service() {
    echo "正在启动服务..."
    source venv/bin/activate
    
    # 确保日志目录存在
    mkdir -p logs
    
    # 使用 Gunicorn 启动应用
    gunicorn -w 4 -b 0.0.0.0:2531 \
        --access-logfile logs/access.log \
        --error-logfile logs/error.log \
        --capture-output \
        --log-level info \
        --daemon \
        app:demo.server
    
    sleep 2
    if [ -n "$(get_pid)" ]; then
        echo "服务已成功启动，运行在 http://localhost:2531"
        echo "查看日志文件："
        echo "- 访问日志: logs/access.log"
        echo "- 错误日志: logs/error.log"
    else
        echo "服务启动失败，请检查日志文件"
    fi
}

# 停止服务
stop_service() {
    echo "正在停止服务..."
    PID=$(get_pid)
    if [ -n "$PID" ]; then
        kill $PID
        echo "服务已停止"
    else
        echo "服务未在运行"
    fi
}

# 重启服务
restart_service() {
    stop_service
    sleep 2
    start_service
}

# 查看服务状态
status_service() {
    PID=$(get_pid)
    if [ -n "$PID" ]; then
        echo "服务正在运行 (PID: $PID)"
    else
        echo "服务未在运行"
    fi
}

# 主程序
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
    *)
        echo "使用方法: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit 0