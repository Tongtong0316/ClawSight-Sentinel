import asyncio
import json
import os
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="ClawSight-Sentinel API", version="0.3.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse(BASE_DIR / "static" / "index.html")

CONFIG_PATH = os.getenv("SENTINEL_CONFIG", "/app/config/config.yaml")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")

DEFAULT_CONFIG: Dict[str, Any] = {
    "ui": {"language": "zh-CN", "theme": "dark"},
    "system": {
        "cpu_affinity": {"enabled": True, "cores": [0, 1]},
        "resources": {"ollama": {"default_model": "gemma:2b"}},
    },
    "wifi": {
        "interfaces": [
            {"name": "wlan0", "driver": "rtl8812au", "mode": "monitor", "band": "5g"}
        ]
    },
    "automation": {"scripts": []},
    "storage": {"log_path": "/mnt/tf_card/sentinel", "retention": {"days": 30, "max_size_gb": 28}},
    "analysis": {"frequency_minutes": 5, "max_logs_per_run": 2000, "enabled": True},
    "notifications": {"enabled": False, "webhook_url": ""},
}

config: Dict[str, Any]

analysis_state: Dict[str, Any] = {"last_run": None, "next_run": None, "running": False}
analysis_task: Optional[asyncio.Task] = None


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config() -> Dict[str, Any]:
    if Path(CONFIG_PATH).exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return deep_merge(DEFAULT_CONFIG, data)
    return deepcopy(DEFAULT_CONFIG)


def persist_config(data: Dict[str, Any]) -> None:
    Path(CONFIG_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True)


def storage_dirs() -> Dict[str, Path]:
    storage_root = Path(config.get("storage", {}).get("log_path", "/mnt/tf_card/sentinel"))
    raw_dir = storage_root / "raw_logs"
    analysis_dir = storage_root / "analysis"
    for d in (storage_root, raw_dir, analysis_dir):
        d.mkdir(parents=True, exist_ok=True)
    return {"root": storage_root, "raw": raw_dir, "analysis": analysis_dir}


def ensure_within_limit(amount: int, root: Path, max_bytes: int) -> None:
    files = sorted(root.rglob("*"), key=lambda p: p.stat().st_mtime)
    used = sum(p.stat().st_size for p in files if p.is_file())
    for path in files:
        if not path.is_file():
            continue
        if used <= max_bytes:
            break
        try:
            size = path.stat().st_size
            path.unlink()
            used -= size
        except OSError:
            continue


def store_raw_log(text: str) -> Path:
    dirs = storage_dirs()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = dirs["raw"] / f"raw_{timestamp}.log"
    with open(filename, "w", encoding="utf-8") as fh:
        fh.write(text)
    max_size = config.get("storage", {}).get("retention", {}).get("max_size_gb", 28)
    ensure_within_limit(max_size, dirs["root"], max_size * 1024**3)
    return filename


def load_analysis_file(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def list_files(directory: Path, limit: int = 20) -> List[Dict[str, Any]]:
    files = sorted(directory.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    summaries = []
    for entry in files[:limit]:
        summaries.append(
            {
                "name": entry.name,
                "size": entry.stat().st_size,
                "mtime": datetime.fromtimestamp(entry.stat().st_mtime).isoformat(),
            }
        )
    return summaries


def store_analysis_entry(entry: Dict[str, Any]) -> Path:
    dirs = storage_dirs()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = dirs["analysis"] / f"analysis_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as fh:
        json.dump(entry, fh, ensure_ascii=False, indent=2)
    max_size = config.get("storage", {}).get("retention", {}).get("max_size_gb", 28)
    ensure_within_limit(max_size, dirs["root"], max_size * 1024**3)
    return filename


def severity_from_text(text: str) -> str:
    lower = text.lower()
    if any(keyword in lower for keyword in ["critical", "panic", "failure"]):
        return "critical"
    if any(keyword in lower for keyword in ["warn", "retry", "timeout", "error"]):
        return "warning"
    return "info"


def standardize_diagnosis(raw: str, model: str, logs_count: int) -> Dict[str, Any]:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    summary = lines[0] if lines else "分析完成，暂无高亮"
    severity = severity_from_text(raw)
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "model": model,
        "context_lines": logs_count,
        "summary": summary,
        "issues": [
            {
                "severity": severity,
                "description": summary,
                "recommendation": "请查看详细日志并依照建议处置。",
            }
        ],
        "metrics": {"lines": logs_count, "model": model},
    }


def scan_wifi_interface() -> Dict[str, Any]:
    wifi_cfg = config.get("wifi", {}).get("interfaces", [])
    if not wifi_cfg:
        return {"error": "No WiFi interface configured"}
    active = wifi_cfg[0]
    driver = active.get("driver", "unknown")
    if driver == "rtl8812au":
        networks = [
            {"ssid": "OpenWrt_5G", "signal": -45, "channel": 149, "congestion": 15},
            {"ssid": "Neighbor", "signal": -70, "channel": 36, "congestion": 55},
        ]
        return {
            "driver": driver,
            "interface": active.get("name", "wlan0"),
            "mode": active.get("mode", "monitor"),
            "band": active.get("band", "5g"),
            "networks": networks,
        }
    if driver in {"mt7601u", "ath9k_htc", "rt2800usb"}:
        return {"driver": driver, "status": "driver profile loaded", "networks": []}
    return {"driver": driver, "status": "unsupported-driver-profile"}


def build_wifi_analysis() -> Dict[str, Any]:
    state = scan_wifi_interface()
    networks = state.get("networks", [])
    best_signal = min((n["signal"] for n in networks), default=-100)
    severity = "info"
    if best_signal < -70:
        severity = "warning"
    if best_signal < -85:
        severity = "critical"
    return {
        "interface": state.get("interface"),
        "mode": state.get("mode"),
        "band": state.get("band"),
        "analysis": {
            "signal_strength": {
                "status": "good" if best_signal >= -60 else "fair",
                "current_dbm": best_signal,
                "avg_dbm": best_signal,
            },
            "neighbors": networks,
            "issues": [
                {
                    "severity": severity,
                    "description": "信号较弱" if severity != "info" else "信道良好",
                    "recommendation": "建议调整天线或信道" if severity != "info" else "继续观察",
                }
            ],
        },
    }


def get_dashboard_snapshot() -> Dict[str, Any]:
    return {
        "config": config,
        "logs": list_files(storage_dirs()["raw"], limit=3),
        "analysis": list_analyses(limit=3),
    }


def gather_recent_logs() -> str:
    dirs = storage_dirs()
    raw = dirs["raw"]
    if not raw.exists():
        return ""
    files = sorted(raw.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    max_count = config.get("analysis", {}).get("max_logs_per_run", 2000)
    lines = []
    for f in files[:5]:
        try:
            content = f.read_text(encoding="utf-8")
            lines.extend(content.splitlines())
        except Exception:
            continue
        if len(lines) >= max_count:
            break
    return "\n".join(lines[:max_count])


async def run_scheduled_analysis():
    global analysis_state
    if analysis_state.get("running"):
        return
    analysis_state["running"] = True
    try:
        logs = gather_recent_logs()
        if not logs:
            return
        model = config.get("system", {}).get("resources", {}).get("ollama", {}).get("default_model", "gemma:2b")
        prompt = "You are a network expert. Analyze these OpenWrt logs and return: root cause, impact, and action plan.\n\n" + logs[:6000]
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(
                    f"{OLLAMA_HOST}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False, "options": {"num_predict": 20, "temperature": 0.1}},
                )
                resp.raise_for_status()
                diagnosis_text = resp.json().get("response", "")
        except Exception as e:
            diagnosis_text = f"Error: {e}"
        logs_count = len([l for l in logs.splitlines() if l.strip()])
        entry = standardize_diagnosis(diagnosis_text, model, logs_count)
        entry["logs_file"] = str(store_raw_log(logs))
        entry["source"] = "scheduled"
        store_analysis_entry(entry)
        analysis_state["last_run"] = datetime.utcnow().isoformat()
    finally:
        analysis_state["running"] = False
        update_next_run()


def update_next_run():
    freq = config.get("analysis", {}).get("frequency_minutes", 5)
    if config.get("analysis", {}).get("enabled", True):
        analysis_state["next_run"] = (datetime.utcnow() + timedelta(minutes=freq)).isoformat()
    else:
        analysis_state["next_run"] = None


async def scheduler_loop():
    while True:
        await asyncio.sleep(10)
        if not config.get("analysis", {}).get("enabled", True):
            continue
        next_run = analysis_state.get("next_run")
        if not next_run:
            continue
        try:
            target = datetime.fromisoformat(next_run)
        except Exception:
            continue
        if datetime.utcnow() >= target:
            asyncio.create_task(run_scheduled_analysis())
            update_next_run()


def initialize():
    global config
    config = load_config()
    storage_dirs()
    update_next_run()
    global analysis_task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    analysis_task = loop.create_task(scheduler_loop())


initialize()


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
2. **日志检索**: `GET /api/v1/logs`
3. **智能诊断**: `POST /api/v1/ai/diagnose`
4. **危机修复**: `POST /api/v1/fix/{script_id}`
""",
        "en-US": """
# 🛡️ ClawSight-Sentinel Network Guardian
1. `GET /api/v1/wifi/scan`
2. `GET /api/v1/logs`
3. `POST /api/v1/ai/diagnose`
4. `POST /api/v1/fix/{script_id}`
""",
    }
    return {"instruction": instructions.get(lang, instructions["en-US"]), "config": config}


class SystemConfig(BaseModel):
    cpu_affinity: Optional[List[int]] = None
    ollama_model: Optional[str] = None
    language: Optional[str] = None
    scheduler_enabled: Optional[bool] = None
    scheduler_frequency: Optional[int] = None


class DiagnosisRequest(BaseModel):
    logs: str


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
    if new_config.scheduler_enabled is not None:
        config.setdefault("analysis", {})["enabled"] = new_config.scheduler_enabled
    if new_config.scheduler_frequency is not None:
        config.setdefault("analysis", {})["frequency_minutes"] = new_config.scheduler_frequency
    persist_config(config)
    update_next_run()
    return {"status": "updated", "config": config}


@app.get("/api/v1/logs")
async def fetch_logs(limit: int = Query(10, ge=1, le=50)):
    return list_files(storage_dirs()["raw"], limit)


@app.get("/api/v1/logs/{name}")
async def fetch_log_content(name: str):
    dirs = storage_dirs()
    path = dirs["raw"] / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    return FileResponse(path, media_type="text/plain")


@app.get("/api/v1/analysis")
async def fetch_analysis(limit: int = Query(10, ge=1, le=30)):
    return list_analyses(limit)


@app.get("/api/v1/analysis/{name}")
async def fetch_analysis_detail(name: str):
    dirs = storage_dirs()
    path = dirs["analysis"] / name
    data = load_analysis_file(path)
    if not data:
        raise HTTPException(status_code=404, detail="Analysis entry not found")
    return data


@app.post("/api/v1/ai/diagnose")
async def diagnose_logs(req: DiagnosisRequest):
    model = (
        config.get("system", {}).get("resources", {}).get("ollama", {}).get("default_model", "gemma:2b")
    )
    prompt = (
        "You are a network expert. Analyze these OpenWrt logs and return: root cause, impact, and action plan.\n\n"
        + req.logs[:6000]
    )
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 20, "temperature": 0.1},
                },
            )
            response.raise_for_status()
            data = response.json()
            diagnosis_text = data.get("response", "")
    except Exception as exc:
        diagnosis_text = f"本地模型暂不可用：{type(exc).__name__}: {exc}"
    logs_count = len([line for line in req.logs.splitlines() if line.strip()])
    entry = standardize_diagnosis(diagnosis_text, model, logs_count)
    entry["raw_response"] = diagnosis_text
    entry["logs_file"] = str(store_raw_log(req.logs))
    store_analysis_entry(entry)
    return {"model": model, "diagnosis": entry, "confidence": 0.8}


@app.get("/api/v1/wifi/scan")
async def wifi_scan():
    return scan_wifi_interface()


@app.get("/api/v1/wifi/analysis")
async def wifi_analysis():
    return build_wifi_analysis()


@app.get("/api/v1/dashboard")
async def dashboard():
    return get_dashboard_snapshot()


@app.get("/api/v1/scheduler/status")
async def scheduler_status():
    return {"enabled": config.get("analysis", {}).get("enabled", True), "frequency_minutes": config.get("analysis", {}).get("frequency_minutes", 5), "last_run": analysis_state.get("last_run"), "next_run": analysis_state.get("next_run"), "running": analysis_state.get("running", False)}


class SchedulerConfig(BaseModel):
    enabled: Optional[bool] = None
    frequency_minutes: Optional[int] = None


@app.post("/api/v1/scheduler/config")
async def update_scheduler_config(cfg: SchedulerConfig):
    global config
    config.setdefault("analysis", {})
    if cfg.enabled is not None:
        config["analysis"]["enabled"] = cfg.enabled
    if cfg.frequency_minutes is not None:
        config["analysis"]["frequency_minutes"] = cfg.frequency_minutes
    persist_config(config)
    update_next_run()
    return {"status": "updated", "config": config.get("analysis")}


@app.post("/api/v1/scheduler/run")
async def trigger_manual_analysis():
    if analysis_state.get("running"):
        return {"status": "already_running"}
    asyncio.create_task(run_scheduled_analysis())
    return {"status": "started"}


@app.post("/api/v1/fix/{script_id}")
async def trigger_fix(script_id: str):
    scripts = config.get("automation", {}).get("scripts", [])
    target = next((s for s in scripts if s.get("id") == script_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Script not found")
    return {
        "status": "queued",
        "target": target.get("target"),
        "actions": target.get("actions", []),
        "note": "Playwright executor will run this action in worker service.",
    }
