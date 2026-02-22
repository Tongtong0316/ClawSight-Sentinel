import os
from copy import deepcopy
from typing import Any, Dict, List, Optional

import httpx
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ClawSight-Sentinel API", version="0.2.0")

CONFIG_PATH = os.getenv("SENTINEL_CONFIG", "/app/config/config.yaml")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")

DEFAULT_CONFIG: Dict[str, Any] = {
    "ui": {"language": "zh-CN"},
    "system": {
        "cpu_affinity": {"enabled": True, "cores": [0, 1]},
        "resources": {"ollama": {"default_model": "tinyllama"}},
    },
    "wifi": {
        "interfaces": [
            {"name": "wlan0", "driver": "rtl8812au", "mode": "monitor", "band": "5g"}
        ]
    },
    "automation": {"scripts": []},
}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
        return deep_merge(DEFAULT_CONFIG, user_cfg)
    return deepcopy(DEFAULT_CONFIG)


config = load_config()


@app.get("/healthz")
async def healthz():
    return {"ok": True, "service": "clawsight-sentinel"}


@app.get("/agent/bootstrap")
async def get_instruction():
    lang = config.get("ui", {}).get("language", "zh-CN")

    instructions = {
        "zh-CN": """
# 🛡️ ClawSight-Sentinel 网络守护系统
您已成功接入 Sentinel 智控中枢。
## 可用指令集:
1. **环境监测**: `GET /api/v1/wifi/scan`
2. **日志检索**: `GET /api/v1/logs?level=error`
3. **智能诊断**: `POST /api/v1/ai/diagnose`
4. **危机修复**: `POST /api/v1/fix/{script_id}`
""",
        "en-US": """
# 🛡️ ClawSight-Sentinel Network Guardian
Connected to Sentinel.
## Capabilities:
1. `GET /api/v1/wifi/scan`
2. `GET /api/v1/logs`
3. `POST /api/v1/ai/diagnose`
4. `POST /api/v1/fix/{script_id}`
""",
    }

    return {
        "instruction": instructions.get(lang, instructions["en-US"]),
        "config": config,
    }


class SystemConfig(BaseModel):
    cpu_affinity: Optional[List[int]] = None
    ollama_model: Optional[str] = None
    language: Optional[str] = None


@app.get("/api/v1/config")
async def get_config():
    return config


@app.post("/api/v1/config")
async def update_config(new_config: SystemConfig):
    global config
    if new_config.cpu_affinity:
        config.setdefault("system", {}).setdefault("cpu_affinity", {})["cores"] = new_config.cpu_affinity
    if new_config.ollama_model:
        config.setdefault("system", {}).setdefault("resources", {}).setdefault("ollama", {})[
            "default_model"
        ] = new_config.ollama_model
    if new_config.language:
        config.setdefault("ui", {})["language"] = new_config.language

    return {"status": "updated", "config": config}


@app.get("/api/v1/wifi/scan")
async def scan_wifi():
    wifi_cfg = config.get("wifi", {}).get("interfaces", [])
    if not wifi_cfg:
        return {"error": "No WiFi interface configured"}

    active = wifi_cfg[0]
    driver = active.get("driver", "unknown")

    if driver == "rtl8812au":
        return {
            "driver": driver,
            "interface": active.get("name", "wlan0"),
            "networks": [
                {"ssid": "OpenWrt_5G", "signal": -45, "channel": 149, "congestion": "low"},
                {"ssid": "Neighbor", "signal": -70, "channel": 36, "congestion": "medium"},
            ],
        }
    if driver in {"mt7601u", "ath9k_htc", "rt2800usb"}:
        return {"driver": driver, "status": "driver profile loaded", "networks": []}

    return {"driver": driver, "status": "unsupported-driver-profile"}


class DiagnosisRequest(BaseModel):
    logs: str


@app.post("/api/v1/ai/diagnose")
async def diagnose_logs(req: DiagnosisRequest):
    model = (
        config.get("system", {})
        .get("resources", {})
        .get("ollama", {})
        .get("default_model", "deepseek-r1:1.5b")
    )

    prompt = (
        "You are a network expert. Analyze these OpenWrt logs and return: "
        "root cause, impact, and action plan.\n\n" + req.logs[:6000]
    )

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            r = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 160, "temperature": 0.2},
                },
            )
            r.raise_for_status()
            data = r.json()
            text = data.get("response", "")
    except Exception as e:
        text = f"本地模型暂不可用：{type(e).__name__}: {e}"

    return {"model": model, "diagnosis": text, "confidence": 0.8}


@app.post("/api/v1/fix/{script_id}")
async def trigger_fix(script_id: str):
    scripts = config.get("automation", {}).get("scripts", [])
    target_script = next((s for s in scripts if s.get("id") == script_id), None)
    if not target_script:
        raise HTTPException(status_code=404, detail="Script not found")

    return {
        "status": "queued",
        "target": target_script.get("target"),
        "action": target_script.get("actions", []),
        "note": "Playwright executor will run this action in worker service.",
    }
