"""
脚本化分析器 - 设备状态、丢包率、延迟等分析
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .collector import DataCollector


@dataclass
class AnalysisConfig:
    offline_threshold_minutes: int = 30
    packet_loss_warning: float = 1.0  # 1%
    packet_loss_critical: float = 5.0  # 5%
    latency_warning_ms: int = 100
    latency_critical_ms: int = 500


class NetworkAnalyzer:
    """网络分析器"""
    
    def __init__(self, collector: DataCollector, config: Optional[Dict] = None):
        self.collector = collector
        self.config = config or {}
        self.analysis_config = AnalysisConfig(
            offline_threshold_minutes=self.config.get("offline_threshold_minutes", 30),
            packet_loss_warning=self.config.get("packet_loss_warning", 1.0),
            packet_loss_critical=self.config.get("packet_loss_critical", 5.0),
            latency_warning_ms=self.config.get("latency_warning_ms", 100),
            latency_critical_ms=self.config.get("latency_critical_ms", 500)
        )
        
        # 历史数据用于趋势分析
        self._history: List[Dict] = []
        self._max_history = 288  # 5分钟一次，24小时
        
    async def analyze_network_health(self) -> Dict[str, Any]:
        """网络健康分析 - 核心方法"""
        # 1. 刷新设备状态
        device_status = await self.collector.refresh_device_status()
        
        # 2. 获取带宽
        bandwidth = await self.collector.get_bandwidth_usage()
        
        # 3. 获取 WiFi 统计
        wifi_stats = await self.collector.get_wifi_stats()
        
        # 4. 获取丢包和延迟 (模拟/从 SNMP 计算)
        network_metrics = self._calculate_network_metrics()
        
        # 5. 检测问题
        issues = self._detect_issues(
            device_status, 
            network_metrics,
            wifi_stats
        )
        
        # 6. 生成摘要
        summary = self._build_summary(
            device_status,
            bandwidth,
            wifi_stats,
            network_metrics,
            issues
        )
        
        # 7. 保存到历史
        self._save_to_history(summary)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "issues": issues,
            "device_status": device_status,
            "wifi_stats": wifi_stats,
            "bandwidth": bandwidth,
            "network_metrics": network_metrics
        }
    
    def _calculate_network_metrics(self) -> Dict[str, Any]:
        """计算网络指标 (丢包率、延迟)"""
        # 实际应该从 SNMP / ping / mtr 获取
        # 这里简化处理，返回模拟数据 + 实际逻辑
        
        # TODO: 实现真实的丢包率计算
        # 从 Prometheus 或 SNMP 获取 interface errors
        
        return {
            "packet_loss": 0.0,  # %
            "avg_latency_ms": 5.2,
            "max_latency_ms": 45.0,
            "jitter_ms": 1.2,
            "tcp_retries": 0,
            "udp_errors": 0
        }
    
    def _detect_issues(
        self, 
        device_status: Dict, 
        network_metrics: Dict,
        wifi_stats: Dict
    ) -> List[Dict[str, Any]]:
        """检测问题"""
        issues = []
        
        # 1. 离线设备检测
        offline_devices = [
            d for d in device_status.get("devices", [])
            if d.get("status") == "offline"
        ]
        
        if offline_devices:
            offline_ips = [d["ip"] for d in offline_devices]
            issues.append({
                "severity": "warning",
                "type": "device_offline",
                "title": f"{len(offline_devices)} 台设备离线",
                "description": f"离线设备: {', '.join(offline_ips[:5])}",
                "details": offline_devices,
                "recommendation": "检查设备电源和网络连接"
            })
            
        # 2. 丢包检测
        packet_loss = network_metrics.get("packet_loss", 0)
        if packet_loss >= self.analysis_config.packet_loss_critical:
            issues.append({
                "severity": "critical",
                "type": "packet_loss",
                "title": f"丢包率过高: {packet_loss}%",
                "description": f"当前丢包率 {packet_loss}%",
                "recommendation": "检查网络拥塞或物理连接"
            })
        elif packet_loss >= self.analysis_config.packet_loss_warning:
            issues.append({
                "severity": "warning",
                "type": "packet_loss",
                "title": f"丢包率偏高: {packet_loss}%",
                "description": f"当前丢包率 {packet_loss}%",
                "recommendation": "监控趋势，检查网络负载"
            })
            
        # 3. 延迟检测
        avg_latency = network_metrics.get("avg_latency_ms", 0)
        if avg_latency >= self.analysis_config.latency_critical_ms:
            issues.append({
                "severity": "critical",
                "type": "latency",
                "title": f"延迟过高: {avg_latency}ms",
                "description": f"平均延迟 {avg_latency}ms",
                "recommendation": "检查网络拥塞或设备负载"
            })
        elif avg_latency >= self.analysis_config.latency_warning_ms:
            issues.append({
                "severity": "warning",
                "type": "latency",
                "title": f"延迟偏高: {avg_latency}ms",
                "description": f"平均延迟 {avg_latency}ms",
                "recommendation": "持续监控"
            })
            
        # 4. WiFi 客户端过多
        total_clients = wifi_stats.get("total_clients", 0)
        if total_clients > 100:
            issues.append({
                "severity": "warning",
                "type": "wifi_congestion",
                "title": f"WiFi 设备过多: {total_clients}",
                "description": f"当前 {total_clients} 个 WiFi 设备连接",
                "recommendation": "考虑增加 AP 或负载均衡"
            })
            
        # 5. 无严重问题时添加正常状态
        if not issues:
            issues.append({
                "severity": "info",
                "type": "healthy",
                "title": "网络运行正常",
                "description": "所有指标正常",
                "recommendation": "保持当前状态"
            })
            
        return issues
    
    def _build_summary(
        self,
        device_status: Dict,
        bandwidth: Dict,
        wifi_stats: Dict,
        network_metrics: Dict,
        issues: List[Dict]
    ) -> Dict[str, Any]:
        """构建摘要"""
        offline_devices = [
            d["ip"] for d in device_status.get("devices", [])
            if d.get("status") == "offline"
        ]
        
        # 生成告警消息
        alerts = []
        critical_count = sum(1 for i in issues if i.get("severity") == "critical")
        warning_count = sum(1 for i in issues if i.get("severity") == "warning")
        
        if critical_count > 0:
            alerts.append(f"⚠️ {critical_count} 个严重问题需要处理")
        if warning_count > 0:
            alerts.append(f"⚡ {warning_count} 个警告")
        if offline_devices:
            alerts.append(f"📴 {len(offline_devices)} 台设备离线")
            
        if not alerts:
            alerts.append("✅ 网络运行正常")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_devices": device_status.get("total", 0),
            "online_devices": device_status.get("online", 0),
            "offline_devices": device_status.get("offline", 0),
            "offline_list": offline_devices,
            "packet_loss": network_metrics.get("packet_loss", 0),
            "avg_latency_ms": network_metrics.get("avg_latency_ms", 0),
            "wifi_clients": wifi_stats.get("total_clients", 0),
            "bandwidth_in_mbps": bandwidth.get("in_mbps", 0),
            "bandwidth_out_mbps": bandwidth.get("out_mbps", 0),
            "alerts": alerts
        }
    
    def _save_to_history(self, summary: Dict):
        """保存到历史"""
        self._history.append(summary)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def get_trends(self, hours: int = 24) -> Dict[str, Any]:
        """获取趋势数据"""
        # 过滤指定时间范围
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [
            h for h in self._history
            if datetime.fromisoformat(h["timestamp"]) > cutoff
        ]
        
        if not recent:
            return {"trend": "no_data", "message": "暂无历史数据"}
        
        # 计算趋势
        packet_losses = [h["packet_loss"] for h in recent]
        latencies = [h["avg_latency_ms"] for h in recent]
        
        # 简单趋势: 比较前半和后半
        mid = len(recent) // 2
        first_half = recent[:mid]
        second_half = recent[mid:]
        
        avg_pl_first = sum(p["packet_loss"] for p in first_half) / len(first_half) if first_half else 0
        avg_pl_second = sum(p["packet_loss"] for p in second_half) / len(second_half) if second_half else 0
        
        avg_lat_first = sum(p["avg_latency_ms"] for p in first_half) / len(first_half) if first_half else 0
        avg_lat_second = sum(p["avg_latency_ms"] for p in second_half) / len(second_half) if second_half else 0
        
        return {
            "period_hours": hours,
            "data_points": len(recent),
            "packet_loss": {
                "avg": sum(packet_losses) / len(packet_losses),
                "max": max(packet_losses),
                "min": min(packet_losses),
                "trend": "increasing" if avg_pl_second > avg_pl_first * 1.2 else "stable" if avg_pl_second < avg_pl_first * 0.8 else "decreasing"
            },
            "latency": {
                "avg": sum(latencies) / len(latencies),
                "max": max(latencies),
                "min": min(latencies),
                "trend": "increasing" if avg_lat_second > avg_lat_first * 1.2 else "stable" if avg_lat_second < avg_lat_first * 0.8 else "decreasing"
            }
        }
    
    # ========== 外部查询接口 ==========
    
    async def get_device_details(self, ip: str) -> Optional[Dict]:
        """获取设备详情"""
        device_status = await self.collector.refresh_device_status()
        
        for device in device_status.get("devices", []):
            if device.get("ip") == ip:
                # 获取更多信息
                return {
                    **device,
                    "packet_loss": 0.0,  # TODO: 从历史计算
                    "avg_latency_ms": 5.2,  # TODO: 从 ping 历史
                    "uptime_percentage": 99.5,  # TODO: 从在线时间计算
                    "first_seen": device.get("last_seen"),  # TODO: 从 ARP 首次发现
                    "last_reboot": None  # TODO: 从 syslog 检测
                }
                
        return None
    
    async def get_offline_devices_report(self) -> Dict:
        """离线设备报告"""
        device_status = await self.collector.refresh_device_status()
        
        offline = [
            d for d in device_status.get("devices", [])
            if d.get("status") == "offline"
        ]
        
        return {
            "count": len(offline),
            "devices": offline,
            "recommendation": "检查这些设备的电源和网络连接" if offline else "所有设备在线"
        }
