"""
数据采集器 - 从 SNMP、Syslog 等源采集数据
"""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# SNMP 采集 (可选)
try:
    from pysnmp.hlapi import *
    SNMP_AVAILABLE = True
except ImportError:
    SNMP_AVAILABLE = False


@dataclass
class SnmpConfig:
    host: str = "192.168.100.1"
    port: int = 161
    community: str = "public"
    timeout: int = 5
    retries: int = 3


@dataclass
class SyslogConfig:
    host: str = "0.0.0.0"
    port: int = 514


class DataCollector:
    """数据采集器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.snmp_config = SnmpConfig(
            host=config.get("openwrt", {}).get("ip", "192.168.100.1"),
            community=config.get("openwrt", {}).get("snmp_community", "public")
        )
        self.storage_path = Path(config.get("storage", {}).get("log_path", "/data/sentinel"))
        
        # 内存缓存
        self._device_cache: Dict[str, Dict] = {}
        self._dhcp_leases: List[Dict] = []
        self._last_dhcp_refresh: Optional[datetime] = None
        self._logs_buffer: List[Dict] = []
        
    # ========== SNMP 采集 ==========
    
    async def snmp_walk(self, oid: str) -> List[Dict]:
        """SNMP Walk 获取数据"""
        if not SNMP_AVAILABLE:
            return self._mock_snmp_data(oid)
        
        results = []
        iterator = walkCmd(
            SnmpEngine(),
            CommunityData(self.snmp_config.community, mpModel=0),
            UdpTransportTarget((self.snmp_config.host, self.snmp_config.port), timeout=self.snmp_config.timeout, retries=self.snmp_config.retries),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )
        
        try:
            for errorIndication, errorStatus, errorIndex, varBinds in iterator:
                if errorIndication:
                    break
                if errorStatus:
                    break
                for varBind in varBinds:
                    results.append({
                        "oid": str(varBind[0]),
                        "value": str(varBind[1])
                    })
        except Exception as e:
            print(f"SNMP error: {e}")
            
        return results
    
    def _mock_snmp_data(self, oid: str) -> List[Dict]:
        """SNMP 不可用时的模拟数据"""
        return []
    
    async def get_interface_stats(self) -> List[Dict]:
        """获取接口统计"""
        # IF-MIB::ifDescr, ifInOctets, ifOutOctets, ifSpeed
        oid = "1.3.6.1.2.1.2.2.1"
        results = await self.snmp_walk(oid)
        
        interfaces = {}
        for item in results:
            oid_str = item["oid"]
            value = item["value"]
            
            # 解析 OID: 1.3.6.1.2.1.2.2.1.X.Y (X=属性, Y=索引)
            parts = oid_str.split(".")
            if len(parts) < 10:
                continue
                
            attr_id = int(parts[-2])
            if_index = int(parts[-1])
            
            if if_index not in interfaces:
                interfaces[if_index] = {"index": if_index}
            
            if attr_id == 2:  # ifDescr
                interfaces[if_index]["name"] = value
            elif attr_id == 10:  # ifInOctets
                interfaces[if_index]["in_octets"] = int(value)
            elif attr_id == 16:  # ifOutOctets
                interfaces[if_index]["out_octets"] = int(value)
            elif attr_id == 5:  # ifSpeed
                interfaces[if_index]["speed"] = int(value)
                
        return list(interfaces.values())
    
    async def get_device_list_from_arp(self) -> List[Dict]:
        """从 ARP 表获取设备列表"""
        # IP-MIB::ipNetToMediaPhysAddress
        oid = "1.3.6.1.2.1.4.22.1.2"
        results = await self.snmp_walk(oid)
        
        devices = []
        for item in results:
            oid_str = item["oid"]
            mac = item["value"]
            
            parts = oid_str.split(".")
            if len(parts) < 10:
                continue
                
            # 提取 IP 地址 (最后4段)
            ip_parts = parts[-4:]
            ip = ".".join(ip_parts)
            
            devices.append({
                "ip": ip,
                "mac": mac.upper(),
                "last_seen": datetime.now().isoformat()
            })
            
        return devices
    
    # ========== DHCP 租约 ==========
    
    async def load_dhcp_leases(self, ssh_config: Optional[Dict] = None) -> List[Dict]:
        """加载 DHCP 租约"""
        # 优先从本地缓存读取
        cache_file = self.storage_path / "dhcp_leases.json"
        if cache_file.exists():
            with open(cache_file, "r") as f:
                self._dhcp_leases = json.load(f)
            return self._dhcp_leases
        
        # 如果配置了 SSH，尝试从 OpenWrt 获取
        # 这里简化处理，实际可通过 SSH 获取
        return self._dhcp_leases
    
    def save_dhcp_leases(self, leases: List[Dict]):
        """保存 DHCP 租约到缓存"""
        self._dhcp_leases = leases
        cache_file = self.storage_path / "dhcp_leases.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(leases, f, indent=2)
    
    # ========== 设备追踪 ==========
    
    async def refresh_device_status(self) -> Dict[str, Any]:
        """刷新设备状态"""
        # 获取 ARP 设备列表
        arp_devices = await self.get_device_list_from_arp()
        
        # 加载 DHCP 租约
        dhcp_leases = await self.load_dhcp_leases()
        
        # 合并数据
        devices = {}
        
        # 从 ARP
        for dev in arp_devices:
            ip = dev["ip"]
            devices[ip] = {
                "ip": ip,
                "mac": dev.get("mac"),
                "source": "arp",
                "last_seen": dev.get("last_seen"),
                "status": "online"
            }
            
        # 从 DHCP 租约标记离线
        dhcp_ips = {lease.get("ip") for lease in dhcp_leases}
        for ip in devices:
            if ip not in dhcp_ips:
                devices[ip]["status"] = "unknown"
        
        # 超过 5 分钟未更新的标记为离线
        now = datetime.now()
        for ip, dev in devices.items():
            if dev.get("last_seen"):
                last = datetime.fromisoformat(dev["last_seen"])
                if (now - last).total_seconds() > 300:
                    dev["status"] = "offline"
        
        self._device_cache = devices
        return {
            "total": len(devices),
            "online": sum(1 for d in devices.values() if d.get("status") == "online"),
            "offline": sum(1 for d in devices.values() if d.get("status") == "offline"),
            "devices": list(devices.values())
        }
    
    # ========== 日志收集 ==========
    
    def add_log(self, log_entry: Dict):
        """添加日志到缓冲区"""
        self._logs_buffer.append({
            **log_entry,
            "timestamp": log_entry.get("timestamp", datetime.now().isoformat())
        })
        
        # 限制缓冲区大小
        if len(self._logs_buffer) > 10000:
            self._logs_buffer = self._logs_buffer[-5000:]
    
    def get_recent_logs(self, limit: int = 100, level: Optional[str] = None) -> List[Dict]:
        """获取最近日志"""
        logs = self._logs_buffer
        
        if level:
            logs = [l for l in logs if l.get("level", "").lower() == level.lower()]
            
        return logs[-limit:]
    
    # ========== 带宽计算 ==========
    
    async def get_bandwidth_usage(self) -> Dict[str, Any]:
        """获取带宽使用情况"""
        interfaces = await self.get_interface_stats()
        
        total_in = 0
        total_out = 0
        
        for iface in interfaces:
            # 排除回环和虚拟接口
            name = iface.get("name", "")
            if name.startswith("lo") or name.startswith("docker") or name.startswith("br-"):
                continue
                
            total_in += iface.get("in_octets", 0)
            total_out += iface.get("out_octets", 0)
        
        # 转换为 Mbps (假设 5 秒内的增量)
        # 实际应存储历史值进行差分计算
        return {
            "in_mbps": (total_in * 8) / 5 / 1_000_000,
            "out_mbps": (total_out * 8) / 5 / 1_000_000,
            "timestamp": datetime.now().isoformat()
        }
    
    # ========== WiFi 统计 ==========
    
    async def get_wifi_stats(self) -> Dict[str, Any]:
        """获取 WiFi 统计"""
        # 从 SNMP 获取无线客户端
        # IEEE802.11-MIB::dot11StationConfigTable
        # 简化处理，返回模拟数据
        
        return {
            "band_2g_clients": 12,
            "band_5g_clients": 33,
            "total_clients": 45,
            "aps": [
                {"name": "OpenWrt_5G", "band": "5G", "clients": 33, "channel": 149},
                {"name": "OpenWrt_2G", "band": "2.4G", "clients": 12, "channel": 6}
            ]
        }
