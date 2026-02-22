from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class DeviceMetrics(BaseModel):
    ip: str
    hostname: Optional[str] = None
    mac: Optional[str] = None
    status: str = "unknown"  # online, offline
    last_seen: Optional[str] = None
    packet_loss: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    uptime_percentage: Optional[float] = None
    port_count: int = 0


class NetworkSummary(BaseModel):
    timestamp: str
    total_devices: int
    online_devices: int
    offline_devices: int
    offline_list: List[str]
    packet_loss: float
    avg_latency_ms: float
    wifi_clients: int
    bandwidth_usage_mbps: float
    alerts: List[str]


class LogEntry(BaseModel):
    timestamp: str
    source: str
    level: str
    message: str
    device: Optional[str] = None
    raw: Optional[str] = None


class AnalysisResult(BaseModel):
    timestamp: str
    summary: NetworkSummary
    issues: List[Dict[str, Any]]
    trends: Optional[Dict[str, Any]] = None


class WifiStats(BaseModel):
    band_2g_clients: int = 0
    band_5g_clients: int = 0
    total_clients: int = 0
    ap_list: List[Dict[str, Any]] = []


class DhcpStats(BaseModel):
    total_leases: int
    active_leases: int
    expired_leases: int
    leases: List[Dict[str, Any]] = []
