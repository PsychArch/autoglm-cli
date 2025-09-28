# AutoGLM CLI

AutoGLM API 的命令行工具，用于发送自动化任务并监控手机应用操作。

## 配置

设置 API 密钥：
```bash
export AUTOGLM_API_KEY="your_api_key"
```

或创建 `.env` 文件：
```
AUTOGLM_API_KEY=your_api_key
```

## 使用

```bash
# 基本用法
uv run autoglm task "打开高德地图查询从望京到三里屯的通勤时间"

# 带对话ID
uv run autoglm task "搜索附近的咖啡店" --conversation-id "your_conversation_id"
```
