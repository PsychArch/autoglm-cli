import typer
import json
import time
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from dotenv import load_dotenv

from .client import AutoGLMClient

# Load environment variables from .env file
load_dotenv()

app = typer.Typer(help="AutoGLM API 命令行工具")
console = Console()


class AutoGLMLogger:
    def __init__(self, task_instruction: str):
        # Create logs directory
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)

        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_instruction = "".join(c for c in task_instruction[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_instruction = safe_instruction.replace(' ', '_')

        self.log_file = self.logs_dir / f"{timestamp}_{safe_instruction}.json"

        # Initialize log data
        self.log_data = {
            "timestamp": datetime.now().isoformat(),
            "task_instruction": task_instruction,
            "messages": []
        }

        # Save initial log
        self._save_log()

    def log_request(self, message: dict):
        """Log outgoing request"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "request",
            "data": message
        }
        self.log_data["messages"].append(log_entry)
        self._save_log()

    def log_response(self, message: dict):
        """Log incoming response"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "response",
            "data": message
        }
        self.log_data["messages"].append(log_entry)
        self._save_log()

    def _save_log(self):
        """Save log data to file"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.log_data, f, ensure_ascii=False, indent=2)


def format_response(data: dict) -> str:
    """格式化 API 响应以供显示"""
    if "error" in data:
        return f"❌ 错误: {data['error']}"

    if "raw_message" in data:
        return f"📨 原始消息: {data['raw_message']}"

    msg_type = data.get("msg_type", "unknown")

    if msg_type == "server_init":
        return "✅ 已连接到 AutoGLM"

    elif msg_type == "server_session":
        session_data = data.get("data", {})
        biz_type = session_data.get("biz_type", "unknown")
        vm_state = session_data.get("vm_state", "unknown")
        vm_id = session_data.get("vm_id", "unknown")
        uid = session_data.get("uid", "")

        if biz_type == "init_vm":
            return f"🔧 虚拟机初始化中: {vm_state}"
        elif biz_type == "init_session":
            return f"🖥️  虚拟机 {vm_state} (ID: {vm_id[:12]}{'...' if len(vm_id) > 12 else ''})"
        else:
            return f"🖥️  虚拟机 {vm_state} (ID: {vm_id})"

    elif msg_type == "client_test":
        test_data = data.get("data", {})
        instruction = test_data.get("instruction", "")
        session_id = test_data.get("session_id", "")
        metadata = test_data.get("metadata", "")

        if session_id:
            return f"📋 任务: {instruction} (会话: {session_id[:16]}{'...' if len(session_id) > 16 else ''})"
        else:
            return f"📋 任务: {instruction}"

    elif msg_type == "server_task":
        task_data = data.get("data", {})
        biz_type = task_data.get("biz_type", "unknown")
        agent_data = task_data.get("data_agent", {})
        action = agent_data.get("action", "unknown")
        message = agent_data.get("message", "")
        round_num = agent_data.get("round", 1)

        # Handle special business types
        if biz_type == "take_over":
            return f"⏸️  第{round_num}轮: 需要手动操作 - {message}"
        elif biz_type == "notify_task":
            return f"📢 第{round_num}轮: 通知 - {message}"

        # Handle different action types
        if action == "launch":
            app_name = agent_data.get("app_name", "")
            package_name = agent_data.get("package_name", "")
            if package_name:
                return f"🚀 第{round_num}轮: 启动 {app_name} ({package_name})"
            else:
                return f"🚀 第{round_num}轮: 启动 {app_name}"
        elif action == "tap":
            center_point = agent_data.get("center_point", [0, 0])
            return f"👆 第{round_num}轮: 点击 {center_point}"
        elif action == "type":
            argument = agent_data.get("argument", "")
            return f"⌨️ 第{round_num}轮: 输入 '{argument}'"
        elif action == "swipe":
            # Check if we have direction info
            swipe_direction = data.get("swipe_direction_info", "")
            if swipe_direction:
                return f"👋 第{round_num}轮: {swipe_direction}"
            else:
                return f"👋 第{round_num}轮: 滑动手势"
        elif action == "back":
            return f"⬅️  第{round_num}轮: 返回导航"
        elif action == "call_api":
            # Truncate long API responses for readability
            display_msg = message[:100] + "..." if len(message) > 100 else message
            return f"🔗 第{round_num}轮: API 调用 - {display_msg}"
        elif action == "take_over":
            return f"⏸️  第{round_num}轮: 需要手动操作 - {message}"
        elif action == "finish":
            # Show full finish message - this is the final result users want to see
            return f"✅ 第{round_num}轮: {message}"
        else:
            return f"🔄 第{round_num}轮: {action} - {message}"

    return f"📨 {msg_type}: {json.dumps(data, ensure_ascii=False)}"


@app.command()
def task(
    instruction: str = typer.Argument(..., help="要发送的任务指令"),
    api_key: str = typer.Option(..., envvar="AUTOGLM_API_KEY", help="AutoGLM API 密钥"),
    conversation_id: str = typer.Option("", help="对话ID（用于上下文）")
):
    """向 AutoGLM API 发送任务并监控响应"""

    # Initialize logger
    logger = AutoGLMLogger(instruction)
    console.print(f"📝 日志记录到: {logger.log_file}")

    client = AutoGLMClient(api_key)
    take_over_requested = False
    task_completed = False

    def signal_handler(sig, frame):
        console.print("\n🛑 接收到中断信号，正在关闭连接...")
        client.close()
        sys.exit(0)

    # Setup signal handlers for CTRL-C
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    def message_handler(data: dict):
        nonlocal take_over_requested, task_completed

        # Log the response
        logger.log_response(data)

        response = format_response(data)
        console.print(response)

        # Check if task is completed
        if data.get("msg_type") == "server_task":
            agent_data = data.get("data", {}).get("data_agent", {})
            action = agent_data.get("action", "")
            if action == "finish":
                task_completed = True
                return
            elif action == "take_over":
                take_over_requested = True

    console.print("🔗 正在连接 AutoGLM API...")

    if not client.connect(message_handler, logger.log_request):
        console.print("❌ 连接 AutoGLM API 失败")
        raise typer.Exit(1)

    console.print(f"📤 发送任务: {instruction}")

    if not client.send_task(instruction, conversation_id):
        console.print("❌ 发送任务失败")
        client.close()
        raise typer.Exit(1)

    console.print("⏳ 等待响应中...")
    console.print("─" * 60)

    try:
        while not task_completed:
            time.sleep(1)

            # Handle take_over request
            if take_over_requested:
                console.print("\n📱 需要在手机上手动操作！")
                console.print("💡 请在 AutoGLM 应用中完成所需操作")
                console.print("⏭️  完成手动操作后请按 ENTER 键...")

                try:
                    input()  # Wait for user input
                    console.print("▶️  恢复自动化操作...")
                    console.print("─" * 60)
                    take_over_requested = False
                except KeyboardInterrupt:
                    console.print("\n🛑 任务被用户中断")
                    client.close()
                    raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n🛑 任务被用户中断")
        client.close()
        raise typer.Exit(1)

    client.close()
    console.print("─" * 60)
    console.print("✅ 任务完成")


@app.command()
def info():
    """显示 AutoGLM API 信息"""

    table = Table(title="AutoGLM API 信息")
    table.add_column("属性", style="cyan")
    table.add_column("值", style="white")

    table.add_row("端点", "wss://autoglm-api.zhipuai.cn/openapi/v1/autoglm/developer")
    table.add_row("认证", "Authorization 头中的 Bearer 令牌")
    table.add_row("消息类型", "client_test")
    table.add_row("业务类型", "test_agent")
    table.add_row("环境配置", "在 .env 文件中设置 AUTOGLM_API_KEY 或使用 --api-key")

    console.print(table)

    console.print("\n📝 使用示例:")
    console.print("  autoglm task '打开高德地图查询从望京到三里屯的通勤时间'")
    console.print("  autoglm task '通过小红书搜索下北京开在公园里的咖啡馆'")




if __name__ == "__main__":
    app()
