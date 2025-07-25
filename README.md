# HeyGem 数字人视频处理 Web端

HeyGem 是一个基于 Gradio 构建的 Web 界面，用于数字人视频的生成和处理。该平台提供了完整的数字人视频制作流程，从模型训练到最终视频生成。

## 功能特点

- 🎥 **模型训练**：上传视频文件，训练数字人模型
- 🎙️ **音频合成**：使用训练好的模型生成自然语音
- 🎬 **视频合成**：将生成的音频与原始视频结合
- 📊 **进度监控**：实时查看任务执行进度
- 📱 **作品管理**：查看和管理已生成的视频作品
- 👤 **模特管理**：管理数字人模特模型

## 待办清单

### 1. 界面优化
- [x] 优化整体UI/UX设计
- [x] 改进响应式布局
- [x] 统一设计风格
- [x] 优化移动端适配
- [x] 增加深色模式支持

### 2. 任务队列系统
- [x] 实现任务队列管理
- [x] 添加任务优先级
- [x] 支持任务状态追踪
- [x] 实现任务取消功能
- [x] 添加队列状态监控
- [x] 优化资源分配策略

### 3. 性能优化
- [x] 实现任务并发控制
- [x] 优化资源使用效率
- [x] 添加任务超时处理
- [x] 实现失败任务重试机制
- [x] 优化大文件处理性能

### 4. 用户体验
- [x] 添加任务进度实时显示
- [x] 优化错误提示信息
- [x] 增加操作引导
- [x] 完善帮助文档
- [x] 添加用户反馈功能

### 5. 使用React重构一个界面
- [ ] 创建React项目基础架构
- [ ] 设计组件层次结构
- [ ] 实现用户认证模块
- [ ] 开发模型训练界面
- [ ] 开发视频生成界面
- [ ] 开发作品管理界面
- [ ] 开发模特管理界面
- [ ] 开发任务队列管理界面
- [ ] 实现深色/浅色主题切换
- [ ] 优化移动端适配

### 6. 支持多用户同时操作
- [ ] 实现用户权限管理系统
- [ ] 添加用户注册功能
- [ ] 实现用户资源隔离
- [ ] 添加用户配额管理
- [ ] 实现管理员控制面板
- [ ] 添加用户活动日志
- [ ] 实现并发访问控制
- [ ] 优化数据库结构支持多用户
- [ ] 添加用户间资源共享功能
- [ ] 实现团队协作功能

> **优化完成**：所有计划的优化任务已全部完成！系统现在具有更好的用户界面、高效的任务队列管理、优化的性能和改进的用户体验。

## 系统要求

- Python 3.10+（注：Python 3.8 和 3.9 可能会出现错误，推荐使用 3.10 及以上版本）
- 足够的存储空间用于视频处理
- 支持的操作系统：Windows、Linux、macOS

## 快速开始

### 1. 安装

```bash
# 克隆项目
git clone [项目地址]
# 创建虚拟环境
python3.10 -m venv venv

source venv/bin/activate
# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

在 `config.py` 中配置以下参数：

```python
API_BASE_URL = "后端API地址"
BASE_DIR = "部署目录路径"
SERVER_HOST = "0.0.0.0"  # 服务器监听地址
SERVER_PORT = 2531      # 服务器端口
```

### 3. 运行

#### 本地开发环境
```bash
python3.10 app.py
```

#### Linux 服务器部署
```bash
# 1. 进入项目目录
cd /home/HeyGemWeb

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 后台运行
nohup python3.10 app.py > /home/HeyGemWeb/logs/app.log 2>&1 &

# 5. 检查运行状态
ps -ef | grep python3.10 | grep app.py

# 6. 停止运行
kill $(ps -ef | grep python3.10 | grep app.py | awk '{print $2}')

# 7. 查看实时日志
tail -f /home/HeyGemWeb/logs/app.log

```

## 使用指南

### 模型训练
1. 进入"模型训练"标签页
2. 上传视频文件
3. 输入模特名称
4. 点击"开始训练"
5. 保存返回的参考音频和文本信息

### 视频生成
1. 进入"视频生成"标签页
2. 选择数字人模特
3. 输入要合成的文本
4. 点击"生成视频"
5. 使用"检查状态"按钮查看进度

### 作品管理
- 在"我的作品"标签页查看所有生成的视频
- 支持视频预览和下载
- 使用"刷新作品列表"更新显示

### 模特管理
- 在"我的数字模特"标签页管理所有训练好的模型
- 支持模型预览和下载
- 使用"刷新模特列表"更新显示

## 文件管理

### 支持的文件格式
- 视频：MP4, AVI, MOV, MKV
- 音频：MP3, WAV
- 图片：JPG, PNG, WEBP

### 文件清理
- 使用"文件清理"功能删除指定天数前的临时文件
- 默认清理7天前的文件
- 可自定义清理时间范围（1-365天）

## 注意事项

1. **存储空间**
   - 确保服务器有足够的存储空间
   - 定期清理临时文件
   - 建议配置自动清理任务

2. **性能优化**
   - 建议使用 SSD 存储
   - 配置足够的内存
   - 考虑使用 GPU 加速

3. **安全建议**
   - 配置反向代理（如 Nginx）
   - 启用 SSL 证书
   - 定期备份重要数据

4. **访问控制**
   - 默认访问地址：http://服务器IP:2531
   - 建议配置访问权限控制
   - 避免直接暴露在公网

## 常见问题

1. **视频上传失败**
   - 检查文件格式是否支持
   - 确认文件大小是否超限
   - 验证存储空间是否充足

2. **模型训练失败**
   - 检查视频质量
   - 确认音频是否清晰
   - 查看日志文件排查问题

3. **视频生成失败**
   - 确认模型是否训练完成
   - 检查文本内容是否合适
   - 查看任务状态和错误信息

4. **Python版本问题**
   - 使用Python 3.10+版本运行程序
   - Python 3.8和3.9版本可能会出现兼容性错误
   - 如使用其他版本出现问题，请查看日志详细错误信息

## 技术支持

如有问题，请：
1. 查看日志文件：`/home/HeyGemWeb/logs/app.log`
2. 提交 Issue
3. 联系技术支持团队

