# ClawSight-Sentinel Project Structure

/root/.openclaw/workspace/ClawSight-Sentinel/
├── docker-compose.yml
├── sentinel_api/
│   ├── main.py         # FastAPI App
│   ├── routes/
│   │   ├── agent.py    # /agent/bootstrap
│   │   ├── monitor.py  # Logs & WiFi
│   │   └── actions.py  # Playwright & Scripts
│   ├── services/
│   │   ├── ai.py       # Ollama integration
│   │   └── scan.py     # WiFi scanning logic
│   └── requirements.txt
├── playwright_scripts/
│   ├── openwrt_reboot.js
│   └── modem_reset.js
└── docs/
    └── AGENT_GUIDE.md
