# AutoGLM API Cheatsheet

## Quick Start

**Endpoint:** `wss://autoglm-api.zhipuai.cn/openapi/v1/autoglm/developer`

**Headers:**
```
Authorization: Bearer <API_KEY>
```

**Flow:**
1. Connect WebSocket
2. Send task message
3. Listen for responses

## Authentication

Get API key:
1. Register at AutoGLM app
2. Settings → Developer Program
3. Apply for key (email delivery)

## Request Format

```json
{
  "timestamp": 1747885994523,
  "conversation_id": "",
  "msg_type": "client_test",
  "msg_id": "",
  "data": {
    "biz_type": "test_agent",
    "instruction": "your task instruction"
  }
}
```

## Response Types

**Init Connection:**
```json
{"msg_type": "server_init", "data": {"biz_type": "init_chat"}}
```

**VM Session:**
```json
{"msg_type": "server_session", "data": {"biz_type": "init_vm|init_session", "vm_state": "vm_starting|vm_successful", "vm_id": "...", "uid": "..."}}
```

**Task Echo:**
```json
{"msg_type": "client_test", "data": {"instruction": "...", "session_id": "...", "metadata": "autoglm", "conversation_id": "...", "query_id": "..."}}
```

**Agent Actions:**
```json
{"msg_type": "server_task", "data": {"data_type": "data_agent", "biz_type": "agent_task|take_over|notify_task", "data_agent": {"action": "launch|tap|type|swipe|back|call_api|take_over|finish", "center_point": [x,y], "argument": "text", "package_name": "com.app.id", "app_name": "AppName", "session_id": "...", "request_id": "...", "message": "result", "round": 1}}}
```

**Action Types:**
- `launch`: Opens app (`app_name`, `package_name`, `session_id`)
- `tap`: Screen tap (`center_point: [x,y]`)
- `type`: Text input (`argument: "text"`)
- `swipe`: Screen swipe gesture
- `back`: Navigate back/return action
- `call_api`: Internal API call for data processing
- `take_over`: Manual operation required (`message: "reason"`)
- `finish`: Task complete (`message: "result"`)

**Business Types:**
- `init_chat`: Initial connection setup
- `init_vm`: Virtual machine initialization
- `init_session`: Session establishment
- `test_agent`: Agent task execution
- `agent_task`: Standard agent actions
- `take_over`: Manual intervention required
- `notify_task`: Task notifications

## Python Example

```python
import websocket

url = "wss://autoglm-api.zhipuai.cn/openapi/v1/autoglm/developer"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

def on_message(ws, message):
    print("Received:", message)

ws = websocket.WebSocketApp(url, header=headers, on_message=on_message)
ws.run_forever()
```

## Download Links

- **Android:** autoglm_v2.0.06_office-release.apk (110.74MB)
- **iOS:** App Store → "AutoGLM"

## Usage Rules

- ⚠️ **Non-commercial use only**
- Personal use permitted
- No resale/commercial integration
- Follow AutoGLM terms of service

## Manual Intervention

When `take_over` action occurs:
1. Agent pauses automation
2. User must manually operate phone
3. Complete required action in AutoGLM app
4. Agent resumes after manual step

Common triggers:
- App login required
- CAPTCHA verification
- Permission dialogs
- First-time app setup

## Monitoring

View task execution in AutoGLM app → Cloud Phone page