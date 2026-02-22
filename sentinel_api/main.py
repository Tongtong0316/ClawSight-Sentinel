from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="ClawSight-Sentinel API")

@app.get("/agent/bootstrap")
async def get_instruction():
    return {
        "instruction": """
# Sentinel Agent Instruction
You are now connected to the ClawSight-Sentinel Network Hub.
## Capabilities:
- **Log Retrieval**: GET /api/v1/logs - Fetch recent network logs from TF card.
- **WiFi Scan**: GET /api/v1/wifi/scan - Get current 2.4G/5G spectrum quality.
- **AI Diagnosis**: POST /api/v1/ai/diagnose - Ask the local DeepSeek-1.5B for expert insight.
- **Emergency Fix**: POST /api/v1/fix/{script_id} - Execute Playwright automation (e.g., reboot_modem).

## How to use:
1. Check logs and WiFi status first.
2. If anomaly found, call AI Diagnosis for root cause.
3. If confirmed critical, use Emergency Fix to restore network.
"""
    }

@app.get("/api/v1/wifi/scan")
async def scan_wifi():
    # Placeholder for RTL8812AU scan logic
    return {
        "interface": "wlan0",
        "networks": [
            {"ssid": "OpenWrt_5G", "signal": -45, "channel": 149, "congestion": "low"},
            {"ssid": "Neighbor_WiFi", "signal": -80, "channel": 149, "congestion": "high"}
        ],
        "recommendation": "Switch to Channel 161 for better stability."
    }
