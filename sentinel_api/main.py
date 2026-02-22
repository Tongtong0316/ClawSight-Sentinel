"""
ClawSight-Sentinel v3.0 主程序
- 日志整合 + 时间对齐
- 脚本化分析
- 自建 WebUI
- 外部 API
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .collector import DataCollector
from .analyzer import NetworkAnalyzer
from .narrator import EventNarrator, identify_device, describe_dhcp_allocate, describe_device_offline, describe_abnormal_broadcast, describe_network_health

# ========== 配置 ==========

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

DEFAULT_CONFIG: Dict[str, Any] = {
    "openwrt": {
        "ip": "192.168.100.1",
        "snmp_community": "public",
        "snmp_port": 161
    },
    "storage": {
        "log_path": "/data/sentinel",
        "retention_days": 30
    },
    "analysis": {
        "offline_threshold_minutes": 30,
        "packet_loss_warning": 1.0,
        "packet_loss_critical": 5.0,
        "latency_warning_ms": 100,
        "latency_critical_ms": 500
    },
    "webui": {
        "port": 8080,
        "title": "ClawSight Sentinel"
    }
}

# ========== 初始化 ==========

app = FastAPI(
    title="ClawSight Sentinel API",
    version="3.0.0",
    description="网络监控日志整合 + 脚本化分析"
)

# 挂载静态文件
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 全局状态
config: Dict[str, Any] = {}
collector: Optional[DataCollector] = None
analyzer: Optional[NetworkAnalyzer] = None
narrator: Optional[EventNarrator] = None
analysis_task: Optional[asyncio.Task] = None
last_analysis: Optional[Dict] = None


def load_config() -> Dict[str, Any]:
    """加载配置"""
    config_path = os.getenv("SENTINEL_CONFIG", "/data/sentinel/config/config.yaml")
    config_file = Path(config_path)
    
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        
        # 深度合并
        def deep_merge(base: Dict, override: Dict) -> Dict:
            result = base.copy()
            for key, value in override.items():
                if isinstance(value, dict) and key in result:
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        return deep_merge(DEFAULT_CONFIG, user_config)
    
    return DEFAULT_CONFIG.copy()


def init_services():
    """初始化服务"""
    global config, collector, analyzer, narrator
    
    config = load_config()
    
    # 创建存储目录
    storage_path = Path(config.get("storage", {}).get("log_path", "/data/sentinel"))
    storage_path.mkdir(parents=True, exist_ok=True)
    (storage_path / "logs").mkdir(exist_ok=True)
    
    # 初始化采集器
    collector = DataCollector(config)
    
    # 初始化分析器
    analyzer = NetworkAnalyzer(collector, config.get("analysis", {}))
    
    # 初始化解说员
    dhcp_server = config.get("openwrt", {}).get("ip", "192.168.100.1")
    narrator = EventNarrator(dhcp_server=dhcp_server)


# ========== 前端路由 ==========

@app.get("/", response_class=HTMLResponse)
async def root():
    """主页面"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    
    # 如果没有前端文件，返回内置 HTML
    return HTMLResponse(BUILTIN_HTML)


@app.get("/dashboard")
async def dashboard_page():
    """仪表盘页面"""
    return await root()


# ========== API v2 端点 ==========

@app.get("/api/v2/metrics/summary")
async def get_metrics_summary():
    """网络健康摘要 - 供外部 LLM/Agent 调用"""
    if not analyzer:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    result = await analyzer.analyze_network_health()
    return result["summary"]


@app.get("/api/v2/metrics/full")
async def get_metrics_full():
    """完整指标"""
    if not analyzer:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return await analyzer.analyze_network_health()


@app.get("/api/v2/metrics/device/{ip}")
async def get_device_metrics(ip: str):
    """单设备指标"""
    if not analyzer:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    device = await analyzer.get_device_details(ip)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return device


@app.get("/api/v2/devices")
async def get_devices(status: Optional[str] = None):
    """设备列表"""
    if not collector:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    device_status = await collector.refresh_device_status()
    devices = device_status.get("devices", [])
    
    if status:
        devices = [d for d in devices if d.get("status") == status]
    
    return {
        "total": len(devices),
        "devices": devices
    }


@app.get("/api/v2/devices/offline")
async def get_offline_devices():
    """离线设备列表"""
    if not analyzer:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return await analyzer.get_offline_devices_report()


@app.get("/api/v2/wifi/stats")
async def get_wifi_stats():
    """WiFi 统计"""
    if not collector:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return await collector.get_wifi_stats()


@app.get("/api/v2/bandwidth")
async def get_bandwidth():
    """带宽使用"""
    if not collector:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return await collector.get_bandwidth_usage()


@app.get("/api/v2/logs/recent")
async def get_recent_logs(
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = None
):
    """最近日志"""
    if not collector:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return {
        "count": limit,
        "logs": collector.get_recent_logs(limit, level)
    }


@app.get("/api/v2/analysis")
async def get_analysis(limit: int = Query(10, ge=1, le=50)):
    """历史分析结果"""
    global last_analysis
    
    if not last_analysis:
        # 执行一次分析
        if analyzer:
            last_analysis = await analyzer.analyze_network_health()
    
    # 返回历史趋势
    trends = analyzer.get_trends(24) if analyzer else {}
    
    return {
        "latest": last_analysis,
        "trends": trends
    }


@app.get("/api/v2/trends")
async def get_trends(hours: int = Query(24, ge=1, le=168)):
    """趋势数据"""
    if not analyzer:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return analyzer.get_trends(hours)


# ========== 旧版兼容 API ==========

@app.get("/api/v1/dashboard")
async def dashboard_v1():
    """旧版仪表盘兼容"""
    if not analyzer:
        return {"error": "not initialized"}
    
    result = await analyzer.analyze_network_health()
    return result


@app.get("/api/v1/wifi/scan")
async def wifi_scan_v1():
    """旧版 WiFi 扫描兼容"""
    if not collector:
        return {"error": "not initialized"}
    
    return await collector.get_wifi_stats()


# ========== 自然语言描述 API ==========

@app.get("/api/v2/narrator/health")
async def narrator_health():
    """网络健康状态自然语言描述"""
    global last_analysis
    
    if not last_analysis:
        if analyzer:
            last_analysis = await analyzer.analyze_network_health()
    
    if not last_analysis or not narrator:
        return {"error": "not initialized"}
    
    description = narrator.describe_network_health(last_analysis)
    return {"description": description, "data": last_analysis}


@app.get("/api/v2/narrator/issues")
async def narrator_issues():
    """问题列表自然语言描述"""
    global last_analysis
    
    if not last_analysis or not narrator:
        return {"error": "not initialized"}
    
    issues = last_analysis.get("issues", [])
    descriptions = [narrator.describe_issue(issue) for issue in issues]
    
    return {"descriptions": descriptions, "issues": issues}


@app.get("/api/v2/narrator/device/{ip}")
async def narrator_device(ip: str):
    """设备状态自然语言描述"""
    if not analyzer or not narrator:
        return {"error": "not initialized"}
    
    device = await analyzer.get_device_details(ip)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    mac = device.get("mac", "")
    status = device.get("status", "unknown")
    
    if status == "offline":
        description = narrator.describe_device_offline(mac, ip)
    else:
        device_type = identify_device(mac)
        description = f"{mac}（{device_type}）IP 地址 {ip} 当前在线"
    
    return {"ip": ip, "description": description, "device": device}


@app.get("/api/v2/narrator/offline")
async def narrator_offline_devices():
    """离线设备自然语言描述"""
    global last_analysis
    
    if not last_analysis or not narrator:
        return {"error": "not initialized"}
    
    device_status = last_analysis.get("device_status", {})
    offline_devices = [d for d in device_status.get("devices", []) if d.get("status") == "offline"]
    
    descriptions = []
    for dev in offline_devices:
        mac = dev.get("mac", "")
        duration = dev.get("offline_duration_seconds", 0)
        
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        
        desc = narrator.describe_device_offline_duration(mac, hours, minutes)
        descriptions.append({
            "ip": dev.get("ip"),
            "description": desc
        })
    
    return {"count": len(descriptions), "devices": descriptions}


@app.post("/api/v2/narrator/dhcp")
async def narrator_dhcp_event(event: Dict):
    """DHCP 事件自然语言描述"""
    if not narrator:
        return {"error": "not initialized"}
    
    event_type = event.get("type", "")
    mac = event.get("mac", "")
    ip = event.get("ip", "")
    hostname = event.get("hostname")
    lease_hours = event.get("lease_hours", 12)
    
    if event_type == "allocate":
        description = narrator.describe_dhcp_allocate(mac, ip, hostname, lease_hours)
    elif event_type == "renew":
        description = narrator.describe_dhcp_renew(mac, ip, hostname, lease_hours)
    elif event_type == "release":
        description = narrator.describe_dhcp_release(mac, ip)
    elif event_type == "expired":
        description = narrator.describe_dhcp_expired(mac, ip)
    else:
        description = f"未知 DHCP 事件类型: {event_type}"
    
    return {"type": event_type, "description": description}


@app.post("/api/v2/narrator/abnormal")
async def narrator_abnormal_event(event: Dict):
    """异常事件自然语言描述"""
    if not narrator:
        return {"error": "not initialized"}
    
    event_type = event.get("type", "")
    mac = event.get("mac", "")
    ip = event.get("ip", "")
    
    if event_type == "broadcast_storm":
        packet_count = event.get("packet_count", 0)
        threshold = event.get("threshold", 60)
        description = narrator.describe_abnormal_broadcast(mac, ip, packet_count, threshold)
    elif event_type == "packet_loss":
        packet_loss = event.get("packet_loss_percent", 0)
        description = narrator.describe_high_packet_loss(ip, packet_loss)
    elif event_type == "latency":
        latency = event.get("latency_ms", 0)
        description = narrator.describe_high_latency(ip, latency)
    else:
        description = f"未知异常类型: {event_type}"
    
    return {"type": event_type, "description": description}


@app.get("/api/v2/narrator/report")
async def narrator_full_report():
    """完整分析报告（自然语言）"""
    global last_analysis
    
    if not last_analysis:
        if analyzer:
            last_analysis = await analyzer.analyze_network_health()
    
    if not last_analysis or not narrator:
        return {"error": "not initialized"}
    
    report = narrator.generate_report(last_analysis)
    return {"report": report, "data": last_analysis}


@app.get("/api/v2/narrator/daily")
async def narrator_daily_summary():
    """每日摘要"""
    # TODO: 实现每日统计
    return {"error": "not implemented"}


# ========== 管理接口 ==========

@app.get("/healthz")
async def healthz():
    """健康检查"""
    return {
        "ok": True,
        "service": "clawsight-sentinel",
        "version": "3.0.0"
    }


@app.get("/api/v1/config")
async def get_config():
    """获取配置"""
    return config


# ========== 定时分析任务 ==========

async def scheduled_analysis():
    """定时分析任务"""
    global last_analysis, analysis_task
    
    while True:
        await asyncio.sleep(300)  # 5 分钟
        
        if analyzer:
            try:
                last_analysis = await analyzer.analyze_network_health()
                print(f"[{datetime.now().isoformat()}] Analysis completed")
            except Exception as e:
                print(f"Analysis error: {e}")


# ========== 启动/关闭事件 ==========

@app.on_event("startup")
async def startup():
    """启动"""
    init_services()
    
    # 启动定时分析
    global analysis_task
    analysis_task = asyncio.create_task(scheduled_analysis())
    
    # 立即执行一次分析
    if analyzer:
        global last_analysis
        last_analysis = await analyzer.analyze_network_health()


@app.on_event("shutdown")
async def shutdown():
    """关闭"""
    global analysis_task
    if analysis_task:
        analysis_task.cancel()


# ========== 内置简单前端 ==========

BUILTIN_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ClawSight Sentinel</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
        }
        .header {
            background: #1e293b;
            padding: 1rem 2rem;
            border-bottom: 1px solid #334155;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { font-size: 1.5rem; color: #38bdf8; }
        .header .status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #22c55e;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 1.5rem;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }
        .card {
            background: #1e293b;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #334155;
        }
        .card h2 {
            font-size: 0.875rem;
            color: #94a3b8;
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 0;
            border-bottom: 1px solid #334155;
        }
        .metric:last-child { border-bottom: none; }
        .metric-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: #38bdf8;
        }
        .metric-value.warning { color: #f59e0b; }
        .metric-value.critical { color: #ef4444; }
        .metric-value.success { color: #22c55e; }
        .metric-label { color: #94a3b8; }
        .alert {
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
        }
        .alert.critical { background: #7f1d1d; border: 1px solid #ef4444; }
        .alert.warning { background: #78350f; border: 1px solid #f59e0b; }
        .alert.info { background: #1e3a5f; border: 1px solid #38bdf8; }
        .device-list {
            max-height: 300px;
            overflow-y: auto;
        }
        .device-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem;
            border-radius: 6px;
            margin-bottom: 0.25rem;
        }
        .device-item:hover { background: #334155; }
        .device-ip { font-family: monospace; }
        .device-status {
            font-size: 0.75rem;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
        }
        .device-status.online { background: #166534; color: #86efac; }
        .device-status.offline { background: #7f1d1d; color: #fca5a5; }
        .refresh-btn {
            background: #38bdf8;
            color: #0f172a;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
        }
        .refresh-btn:hover { background: #0ea5e9; }
        .chart-placeholder {
            height: 150px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #64748b;
            background: #0f172a;
            border-radius: 8px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ ClawSight Sentinel</h1>
        <div class="status">
            <div class="status-dot"></div>
            <span>运行中</span>
            <button class="refresh-btn" onclick="refreshData()">刷新</button>
        </div>
    </div>
    
    <div class="container">
        <!-- 告警区域 -->
        <div id="alerts"></div>
        
        <!-- 核心指标 -->
        <div class="grid">
            <div class="card">
                <h2>📊 设备状态</h2>
                <div class="metric">
                    <span class="metric-label">在线设备</span>
                    <span class="metric-value success" id="online-devices">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">离线设备</span>
                    <span class="metric-value" id="offline-devices">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">总设备</span>
                    <span class="metric-value" id="total-devices">-</span>
                </div>
            </div>
            
            <div class="card">
                <h2>🌐 网络指标</h2>
                <div class="metric">
                    <span class="metric-label">丢包率</span>
                    <span class="metric-value" id="packet-loss">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">平均延迟</span>
                    <span class="metric-value" id="latency">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">带宽下行</span>
                    <span class="metric-value" id="bandwidth-in">-</span>
                </div>
            </div>
            
            <div class="card">
                <h2>📶 WiFi 状态</h2>
                <div class="metric">
                    <span class="metric-label">2.4G 设备</span>
                    <span class="metric-value" id="wifi-2g">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">5G 设备</span>
                    <span class="metric-value" id="wifi-5g">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">总连接数</span>
                    <span class="metric-value" id="wifi-total">-</span>
                </div>
            </div>
        </div>
        
        <!-- 设备列表 -->
        <div class="grid">
            <div class="card">
                <h2>🖥️ 在线设备</h2>
                <div class="device-list" id="online-list"></div>
            </div>
            <div class="card">
                <h2>📴 离线设备</h2>
                <div class="device-list" id="offline-list"></div>
            </div>
        </div>
    </div>
    
    <script>
        async function refreshData() {
            try {
                const resp = await fetch('/api/v2/metrics/full');
                const data = await resp.json();
                
                const summary = data.summary;
                
                // 更新指标
                document.getElementById('online-devices').textContent = summary.online_devices;
                document.getElementById('offline-devices').textContent = summary.offline_devices;
                document.getElementById('total-devices').textContent = summary.total_devices;
                
                // 网络指标
                const plEl = document.getElementById('packet-loss');
                plEl.textContent = summary.packet_loss + '%';
                plEl.className = 'metric-value' + (summary.packet_loss > 1 ? ' warning' : '');
                
                document.getElementById('latency').textContent = summary.avg_latency_ms + ' ms';
                document.getElementById('bandwidth-in').textContent = summary.bandwidth_in_mbps.toFixed(1) + ' Mbps';
                
                // WiFi
                document.getElementById('wifi-2g').textContent = data.wifi_stats.band_2g_clients;
                document.getElementById('wifi-5g').textContent = data.wifi_stats.band_5g_clients;
                document.getElementById('wifi-total').textContent = data.wifi_stats.total_clients;
                
                // 告警
                const alertsEl = document.getElementById('alerts');
                alertsEl.innerHTML = summary.alerts.map(a => 
                    `<div class="alert info">${a}</div>`
                ).join('');
                
                // 设备列表
                const devices = data.device_status.devices;
                const online = devices.filter(d => d.status === 'online').slice(0, 10);
                const offline = devices.filter(d => d.status === 'offline');
                
                document.getElementById('online-list').innerHTML = online.map(d => 
                    `<div class="device-item"><span class="device-ip">${d.ip}</span><span class="device-status online">在线</span></div>`
                ).join('') || '<div class="device-item">无</div>';
                
                document.getElementById('offline-list').innerHTML = offline.map(d => 
                    `<div class="device-item"><span class="device-ip">${d.ip}</span><span class="device-status offline">离线</span></div>`
                ).join('') || '<div class="device-item">无</div>';
                
            } catch (e) {
                console.error(e);
            }
        }
        
        // 初始加载
        refreshData();
        // 每 30 秒刷新
        setInterval(refreshData, 30000);
    </script>
</body>
</html>
"""

# 初始化
init_services()
