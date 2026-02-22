import yaml
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path

app = FastAPI(title="ClawSight-Sentinel API")

# 配置加载器
CONFIG_PATH = os.getenv("SENTINEL_CONFIG", "/app/config/config.yaml")

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {
        "ui": {"language": "zh-CN"},
        "system": {"resources": {"ollama": {"default_model": "deepseek-r1:1.5b"}}}
    }

config = load_config()

# ============ Agent Bootstrap 接口 ============

@app.get("/agent/bootstrap")
async def get_instruction():
    lang = config.get("ui", {}).get("language", "zh-CN")
    
    instructions = {
        "zh-CN": """
# 🛡️ ClawSight-Sentinel 网络守护系统
您已成功接入 Sentinel 智控中枢。
## 可用指令集:
1. **环境监测**: `GET /api/v1/wifi/scan` - 获取 2.4G/5G 频谱质量。
2. **日志检索**: `GET /api/v1/logs?level=error` - 获取最近系统日志。
3. **智能诊断**: `POST /api/v1/ai/diagnose` - 调用本地大模型分析日志。
4. **危机修复**: `POST /api/v1/fix/{script_id}` - 执行 WebUI 自动化修复。

## 使用流程:
1. 调用 WiFi 扫描确认物理层状态。
2. 调阅错误日志。
3. 如需深度分析，请调用 AI 诊断接口。
4. 确认为重大故障时，使用 fix 接口重启设备。
""",
        "en-US": """
# 🛡️ ClawSight-Sentinel Network Guardian
Connected to Sentinel.
## Capabilities:
1. **Environment**: `GET /api/v1/wifi/scan` - Spectrum analysis.
2. **Logs**: `GET /api/v1/logs` - System logs.
3. **Diagnosis**: `POST /api/v1/ai/diagnose` - Local LLM analysis.
4. **Fix**: `POST /api/v1/fix/{script_id}` - Execute automation.
"""
    }
    
    return {
        "instruction": instructions.get(lang, instructions["en-US"]),
        "config": config
    }

# ============ 系统配置接口 ============

class SystemConfig(BaseModel):
    cpu_affinity: Optional[List[int]] = None
    ollama_model: Optional[str] = None

@app.get("/api/v1/config")
async def get_config():
    """获取当前系统配置"""
    return config

@app.post("/api/v1/config")
async def update_config(new_config: SystemConfig):
    """更新系统配置 (WebUI 调用)"""
    global config
    # 此处应加入写入逻辑
    if new_config.cpu_affinity:
        config['system']['cpu_affinity']['cores'] = new_config.cpu_affinity
    if new_config.ollama_model:
        config['system']['resources']['ollama']['default_model'] = new_config.ollama_model
    
    return {"status": "updated", "config": config}

# ============ WiFi 扫描接口 (支持多驱动) ============

@app.get("/api/v1/wifi/scan")
async def scan_wifi():
    """
    扫描 WiFi 环境。
    支持根据 config.yaml 中定义的 driver 自动选择扫描策略。
    """
    wifi_cfg = config.get("wifi", {}).get("interfaces", [])
    active_driver = wifi_cfg[0].get("driver", "rtl8812au") if wifi_cfg else "unknown"
    
    # 模拟多驱动适配逻辑
    if "rtl8812au" in active_driver:
        return {
            "driver": "rtl8812au",
            "interface": "wlan0",
            "networks": [
                {"ssid": "OpenWrt_5G", "signal": -45, "channel": 149, "congestion": "low"},
                {"ssid": "Neighbor", "signal": -70, "channel": 36, "congestion": "medium"}
            ]
        }
    elif "mt7601u" in active_driver:
        # MediaTek 驱动逻辑
        return {"driver": "mt7601u", "status": "scanning..."}
    
    return {"error": "Unsupported driver"}

# ============ 诊断接口 ============

class DiagnosisRequest(BaseModel):
    logs: str

@app.post("/api/v1/ai/diagnose")
async def diagnose_logs(req: DiagnosisRequest):
    model = config.get("system", {}).get("resources", {}).get("ollama", {}).get("default_model", "deepseek-r1:1.5b")
    # 此处接入 Ollama API
    return {
        "model": model,
        "diagnosis": "日志分析：检测到防火墙规则触发频繁，建议检查 DPI 设置。",
        "confidence": 0.85
    }

# ============ 修复接口 ============

@app.post("/api/v1/fix/{script_id}")
async def trigger_fix(script_id: str):
    scripts = config.get("automation", {}).get("scripts", [])
    target_script = next((s for s in scripts if s.get("id") == script_id), None)
    
    if not target_script:
        raise HTTPException(status_code=404, detail="Script not found")
        
    # 此处调用 Playwright 执行自动化
    return {
        "status": "executing",
        "target": target_script.get("target"),
        "action": "reboot"
    }
