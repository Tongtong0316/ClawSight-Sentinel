"""
自然语言描述生成器 - 将日志/事件转换为人类可读的描述
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


# MAC 地址前缀到厂商的映射
MAC_VENDOR_MAP = {
    "00:1a:2b": "Apple",
    "00:1c:b3": "Apple",
    "00:21:e9": "Apple",
    "00:25:00": "Apple",
    "00:26:08": "Apple",
    "00:26:b0": "Apple",
    "00:26:bb": "Apple",
    "00:cd:fe": "Apple",
    "00:e0:4c": "Realtek",
    "dc:a6:32": "Raspberry Pi",
    "b8:27:eb": "Raspberry Pi",
    "e4:5f:01": "Raspberry Pi",
    "00:1a:22": "Cisco/Linksys",
    "00:17:88": "Philips Hue",
    "ac:cf:85": "ESP8266",
    "5c:cf:7f": "ESP8266",
    "bc:dd:c2": "ESP8266",
    "00:1c:7b": "OnePlus",
    "00:1a:48": "OnePlus",
    "00:24:45": "TP-Link",
    "00:27:19": "TP-Link",
    "00:50:18": "TP-Link",
    "14:cc:20": "TP-Link",
    "14:cf:92": "TP-Link",
    "50:c7:bf": "TP-Link",
    "54:c8:0f": "TP-Link",
    "60:e3:27": "TP-Link",
    "64:66:b3": "TP-Link",
    "64:70:02": "TP-Link",
    "6c:5a:b5": "TP-Link",
    "78:a1:06": "TP-Link",
    "90:f6:52": "TP-Link",
    "94:0c:6d": "TP-Link",
    "98:da:c4": "TP-Link",
    "a0:f3:c1": "TP-Link",
    "ac:84:c6": "TP-Link",
    "b0:4e:26": "TP-Link",
    "b0:95:75": "TP-Link",
    "bc:46:99": "TP-Link",
    "c0:25:e9": "TP-Link",
    "c4:6e:1f": "TP-Link",
    "c8:3a:35": "TP-Link",
    "c8:3a:e3": "TP-Link",
    "d8:07:b6": "TP-Link",
    "d8:0d:17": "TP-Link",
    "e8:de:27": "TP-Link",
    "ec:08:6b": "TP-Link",
    "ec:17:2f": "TP-Link",
    "f0:f3:36": "TP-Link",
    "f4:ec:38": "TP-Link",
    "f8:1a:67": "TP-Link",
    "f8:d1:11": "TP-Link",
    "18:d6:c7": "Xiaomi",
    "34:80:b3": "Xiaomi",
    "38:a4:ed": "Xiaomi",
    "3c:bd:d8": "Xiaomi",
    "44:23:7c": "Xiaomi",
    "4c:63:71": "Xiaomi",
    "50:64:2b": "Xiaomi",
    "54:48:e6": "Xiaomi",
    "58:44:98": "Xiaomi",
    "5c:92:5e": "Xiaomi",
    "64:09:80": "Xiaomi",
    "64:b4:73": "Xiaomi",
    "68:df:dd": "Xiaomi",
    "6c:5a:b3": "Xiaomi",
    "74:23:44": "Xiaomi",
    "78:02:f8": "Xiaomi",
    "7c:1d:d9": "Xiaomi",
    "80:ad:16": "Xiaomi",
    "84:f3:eb": "Xiaomi",
    "88:c3:97": "Xiaomi",
    "8c:be:19": "Xiaomi",
    "94:b5:49": "Xiaomi",
    "98:fa:e3": "Xiaomi",
    "9c:99:a0": "Xiaomi",
    "a4:77:33": "Xiaomi",
    "a8:9c:ed": "Xiaomi",
    "ac:c1:ee": "Xiaomi",
    "b0:e2:35": "Xiaomi",
    "b4:39:d6": "Xiaomi",
    "b8:2a:72": "Xiaomi",
    "bc:62:0e": "Xiaomi",
    "c4:0b:cb": "Xiaomi",
    "c8:58:c0": "Xiaomi",
    "d4:97:0b": "Xiaomi",
    "d8:5d:e2": "Xiaomi",
    "dc:53:7c": "Xiaomi",
    "e8:71:8d": "Xiaomi",
    "f0:b4:79": "Xiaomi",
    "f4:f5:d8": "Xiaomi",
    "fc:64:ba": "Xiaomi",
    "00:db:70": "Xiaomi",
    "08:98:20": "Google",
    "3c:5a:b4": "Google",
    "54:60:09": "Google",
    "94:eb:2c": "Google",
    "98:d2:93": "Google",
    "d0:17:c2": "Google",
    "d4:f5:47": "Google",
    "f8:c8:49": "Google",
    "1c:f2:9a": "Amazon",
    "2c:f0:5d": "Amazon",
    "34:d2:70": "Amazon",
    "38:f7:3d": "Amazon",
    "40:4d:8e": "Amazon",
    "44:65:0d": "Amazon",
    "50:dc:e7": "Amazon",
    "50:f5:da": "Amazon",
    "68:37:e9": "Amazon",
    "68:54:fd": "Amazon",
    "74:75:48": "Amazon",
    "78:e1:03": "Amazon",
    "84:d6:d0": "Amazon",
    "8c:c8:cd": "Amazon",
    "a0:02:dc": "Amazon",
    "ac:63:be": "Amazon",
    "b4:7c:9c": "Amazon",
    "bc:3b:af": "Amazon",
    "c8:3d:d4": "Amazon",
    "cc:9e:a2": "Amazon",
    "f0:27:2d": "Amazon",
    "f0:81:73": "Amazon",
    "f0:d5:bf": "Amazon",
    "dc:97:58": "XGIMI",
    "28:6c:07": "OnePlus",
    "30:59:b7": "OnePlus",
    "10:2a:b3": "OnePlus",
    "d0:59:e4": "OnePlus",
    "e8:b1:fc": "OnePlus",
    "48:55:19": "Xiaomi (IoT)",
    "00:19:15": "Cisco",
    "00:1b:2b": "Cisco",
    "00:1d:70": "Cisco",
    "00:1e:13": "Cisco",
    "00:1e:68": "Cisco",
    "00:1f:6c": "Cisco",
    "00:1f:9e": "Cisco",
    "00:21:55": "Cisco",
    "00:21:9c": "Cisco",
    "00:22:55": "Cisco",
    "00:23:33": "Cisco",
    "00:23:69": "Cisco",
    "00:23:9c": "Cisco",
    "00:24:14": "Cisco",
    "00:24:63": "Cisco",
    "00:24:97": "Cisco",
    "00:25:45": "Cisco",
    "00:25:64": "Cisco",
    "00:25:84": "Cisco",
    "00:25:b3": "Cisco",
    "00:26:0c": "Cisco",
    "00:26:52": "Cisco",
    "00:26:b8": "Cisco",
    "00:26:ca": "Cisco",
    "00:27:0c": "Cisco",
    "00:27:1a": "Cisco",
    "00:27:5b": "Cisco",
    "00:27:8a": "Cisco",
    "00:27:c4": "Cisco",
    "00:f8:1c": "Cisco",
    "00:f8:2c": "Cisco",
    "14:20:5a": "Honor",
    "50:01:6b": "Honor",
    "00:1e:08": "Samsung",
    "00:21:19": "Samsung",
    "00:23:39": "Samsung",
    "00:23:d6": "Samsung",
    "00:24:90": "Samsung",
    "00:25:66": "Samsung",
    "00:26:37": "Samsung",
    "00:26:5d": "Samsung",
    "08:08:c2": "Samsung",
    "10:1d:c0": "Samsung",
    "14:32:d1": "Samsung",
    "14:49:e0": "Samsung",
    "18:3a:2d": "Samsung",
    "1c:5a:6e": "Samsung",
    "20:d5:bf": "Samsung",
    "24:4b:81": "Samsung",
    "28:98:7b": "Samsung",
    "30:cd:a7": "Samsung",
    "34:23:ba": "Samsung",
    "38:01:95": "Samsung",
    "38:19:e4": "Samsung",
    "40:0e:85": "Samsung",
    "40:33:1a": "Samsung",
    "44:4e:1a": "Samsung",
    "48:44:f7": "Samsung",
    "4c:3c:16": "Samsung",
    "50:01:bb": "Samsung",
    "50:a4:d0": "Samsung",
    "54:40:ad": "Samsung",
    "58:c3:8b": "Samsung",
    "5c:0a:5b": "Samsung",
    "60:6b:bd": "Samsung",
    "64:b3:10": "Samsung",
    "68:27:37": "Samsung",
    "78:25:ad": "Samsung",
    "78:d7:52": "Samsung",
    "80:65:6d": "Samsung",
    "84:11:9e": "Samsung",
    "88:32:9b": "Samsung",
    "8c:71:f8": "Samsung",
    "90:18:7c": "Samsung",
    "94:01:a2": "Samsung",
    "98:52:b1": "Samsung",
    "a0:07:98": "Samsung",
    "a4:07:b6": "Samsung",
    "ac:36:13": "Samsung",
    "b0:47:bf": "Samsung",
    "b4:3a:28": "Samsung",
    "b8:5a:73": "Samsung",
    "bc:14:01": "Samsung",
    "bc:44:86": "Samsung",
    "c0:97:27": "Samsung",
    "c4:57:6e": "Samsung",
    "d0:17:c2": "Samsung",
    "d0:22:be": "Samsung",
    "d4:87:d8": "Samsung",
    "d8:90:e8": "Samsung",
    "e0:99:71": "Samsung",
    "e4:12:1d": "Samsung",
    "e8:e5:d6": "Samsung",
    "ec:1f:72": "Samsung",
    "f0:25:b7": "Samsung",
    "f4:09:d8": "Samsung",
    "f8:04:2e": "Samsung",
    "fc:a1:83": "Samsung",
    "00:50:56": "VMware",
    "00:0c:29": "VMware",
    "08:00:27": "VirtualBox",
    "52:54:00": "QEMU/KVM",
    "00:16:3e": "Xen",
    "00:18:71": "Dell",
    "00:19:b9": "Dell",
    "00:1a:a0": "Dell",
    "00:1d:09": "Dell",
    "00:1e:4f": "Dell",
    "00:1e:c9": "Dell",
    "00:21:70": "Dell",
    "00:21:9b": "Dell",
    "00:22:19": "Dell",
    "00:24:e8": "Dell",
    "00:25:64": "Dell",
    "00:26:b9": "Dell",
    "00:a0:97": "Dell",
    "14:18:77": "Dell",
    "14:58:d0": "Dell",
    "18:03:73": "Dell",
    "18:66:da": "Dell",
    "18:a9:9b": "Dell",
    "1c:40:24": "Dell",
    "24:6e:96": "Dell",
    "24:b6:fd": "Dell",
    "28:f1:0e": "Dell",
    "34:17:eb": "Dell",
    "34:e6:d7": "Dell",
    "38:63:bb": "Dell",
    "44:a8:42": "Dell",
    "4c:76:25": "Dell",
    "54:9f:35": "Dell",
    "5c:26:0a": "Dell",
    "5c:f9:6a": "Dell",
    "64:00:6a": "Dell",
    "6c:29:ed": "Dell",
    "70:10:6f": "Dell",
    "74:86:7a": "Dell",
    "74:e6:e2": "Dell",
    "78:2b:cb": "Dell",
    "78:45:c4": "Dell",
    "84:2b:2b": "Dell",
    "84:7b:eb": "Dell",
    "88:88:3f": "Dell",
    "8c:ec:4b": "Dell",
    "98:90:96": "Dell",
    "98:ee:cb": "Dell",
    "9c:b6:54": "Dell",
    "a4:1f:72": "Dell",
    "a4:ba:db": "Dell",
    "a8:06:21": "Dell",
    "ac:b5:7d": "Dell",
    "b0:83:fe": "Dell",
    "b4:e1:0f": "Dell",
    "bc:30:5b": "Dell",
    "bc:ee:7b": "Dell",
    "c8:1f:66": "Dell",
    "c8:bc:c8": "Dell",
    "c8:f7:50": "Dell",
    "d4:81:d7": "Dell",
    "d4:be:d9": "Dell",
    "d8:9d:67": "Dell",
    "d8:cb:99": "Dell",
    "e0:db:55": "Dell",
    "ec:f4:bb": "Dell",
    "f0:1f:af": "Dell",
    "f4:8e:38": "Dell",
    "f8:bc:12": "Dell",
    "f8:ca:b8": "Dell",
    "fc:f8:ae": "Dell",
    "00:14:22": "Intel",
    "00:15:00": "Intel",
    "00:16:6f": "Intel",
    "00:16:76": "Intel",
    "00:16:ea": "Intel",
    "00:18:de": "Intel",
    "00:19:d1": "Intel",
    "00:1b:21": "Intel",
    "00:1b:77": "Intel",
    "00:1c:bf": "Intel",
    "00:1d:e0": "Intel",
    "00:1e:64": "Intel",
    "00:1f:3b": "Intel",
    "00:20:e0": "Intel",
    "00:21:5c": "Intel",
    "00:22:fa": "Intel",
    "00:23:14": "Intel",
    "00:24:d6": "Intel",
    "00:26:c6": "Intel",
    "00:26:e1": "Intel",
    "00:27:10": "Intel",
    "e0:07:1b": "HP",
    "e0:91:f5": "HP",
    "e0:db:55": "HP",
    "e4:11:5b": "HP",
    "e8:39:35": "HP",
    "ec:9a:74": "HP",
    "f0:03:8c": "HP",
    "f0:62:81": "HP",
    "f4:03:43": "HP",
    "f8:b1:56": "HP",
    "fc:3f:db": "HP",
    "f4:ce:46": "HP",
    "b8:2a:72": "Unknown"
}


def identify_device(mac: str) -> str:
    """通过 MAC 地址识别设备厂商/类型"""
    if not mac:
        return "未知设备"
    
    # 标准化 MAC 地址
    mac = mac.upper().replace("-", ":")
    prefix = ":".join(mac.split(":")[:3])
    
    return MAC_VENDOR_MAP.get(prefix, "未知设备")


def format_mac(mac: str) -> str:
    """标准化 MAC 地址格式"""
    if not mac:
        return "00:00:00:00:00:00"
    return mac.upper().replace("-", ":")


def format_duration(seconds: int) -> str:
    """将秒数转换为人类可读的时长"""
    if seconds < 60:
        return f"{seconds} 秒"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} 分钟"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours} 小时 {minutes} 分钟"
        return f"{hours} 小时"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        if hours > 0:
            return f"{days} 天 {hours} 小时"
        return f"{days} 天"


def format_timestamp(ts: datetime) -> str:
    """格式化时间戳"""
    return ts.strftime("%Y-%m-%d %H:%M:%S")


class EventNarrator:
    """事件解说员 - 将事件转换为自然语言"""
    
    def __init__(self, dhcp_server: str = "192.168.100.1"):
        self.dhcp_server = dhcp_server
    
    # ========== DHCP 事件 ==========
    
    def describe_dhcp_allocate(self, mac: str, ip: str, hostname: Optional[str] = None, lease_hours: int = 12) -> str:
        """描述 DHCP 分配事件"""
        device_type = identify_device(mac)
        formatted_mac = format_mac(mac)
        
        if hostname:
            return f"{formatted_mac}（{device_type}，主机名: {hostname}）通过 {self.dhcp_server} 的 DHCP 服务器获得 {ip} 的 IP 地址，租约为 {lease_hours} 小时"
        else:
            return f"{formatted_mac}（{device_type}）通过 {self.dhcp_server} 的 DHCP 服务器获得 {ip} 的 IP 地址，租约为 {lease_hours} 小时"
    
    def describe_dhcp_renew(self, mac: str, ip: str, hostname: Optional[str] = None, lease_hours: int = 12) -> str:
        """描述 DHCP 续租事件"""
        device_type = identify_device(mac)
        formatted_mac = format_mac(mac)
        
        if hostname:
            return f"{formatted_mac}（{device_type}，主机名: {hostname}）从 {self.dhcp_server} 续租了 {ip} IP 地址，租约更新为 {lease_hours} 小时"
        else:
            return f"{formatted_mac}（{device_type}）从 {self.dhcp_server} 续租了 {ip} IP 地址，租约更新为 {lease_hours} 小时"
    
    def describe_dhcp_release(self, mac: str, ip: str) -> str:
        """描述 DHCP 释放事件"""
        device_type = identify_device(mac)
        formatted_mac = format_mac(mac)
        return f"{formatted_mac}（{device_type}）释放了 IP 地址 {ip}，从网络断开"
    
    def describe_dhcp_expired(self, mac: str, ip: str) -> str:
        """描述 DHCP 租约过期"""
        device_type = identify_device(mac)
        formatted_mac = format_mac(mac)
        return f"{formatted_mac}（{device_type}）的 IP 地址 {ip} 租约已过期，设备可能已离线"
    
    # ========== 设备状态事件 ==========
    
    def describe_device_online(self, mac: str, ip: str, hostname: Optional[str] = None) -> str:
        """描述设备上线"""
        device_type = identify_device(mac)
        formatted_mac = format_mac(mac)
        
        if hostname:
            return f"{formatted_mac}（{device_type}，主机名: {hostname}）通过 {ip} 上线了"
        else:
            return f"{formatted_mac}（{device_type}）通过 {ip} 上线了"
    
    def describe_device_offline(self, mac: str, ip: str, duration_seconds: Optional[int] = None) -> str:
        """描述设备离线"""
        device_type = identify_device(mac)
        formatted_mac = format_mac(mac)
        
        if duration_seconds:
            duration = format_duration(duration_seconds)
            return f"{formatted_mac}（{device_type}）已离线，持续时间: {duration}"
        else:
            return f"{formatted_mac}（{device_type}，IP: {ip}）离线了"
    
    def describe_device_offline_duration(self, mac: str, duration_hours: int, duration_minutes: int) -> str:
        """描述设备离线持续时间"""
        device_type = identify_device(mac)
        formatted_mac = format_mac(mac)
        
        if duration_hours > 0:
            return f"{formatted_mac}（{device_type}）离线持续 {duration_hours} 小时 {duration_minutes} 分钟"
        else:
            return f"{formatted_mac}（{device_type}）离线持续 {duration_minutes} 分钟"
    
    # ========== 异常事件 ==========
    
    def describe_abnormal_broadcast(self, mac: str, ip: str, packet_count: int, threshold: int, duration: str = "5秒") -> str:
        """描述广播风暴异常"""
        device_type = identify_device(mac)
        formatted_mac = format_mac(mac)
        
        if device_type != "未知设备":
            return f"检测到 {formatted_mac}（{device_type}）IP 地址为 {ip} 行为异常，异常被定义为：广播风暴（{duration} 内发送 {packet_count} 个广播包，超过阈值 {threshold}）"
        else:
            return f"检测到 {formatted_mac}（未知设备）IP 地址为 {ip} 行为异常，异常被定义为：广播风暴（{duration} 内发送 {packet_count} 个广播包，超过阈值 {threshold}）"
    
    def describe_high_packet_loss(self, ip: str, packet_loss_percent: float, threshold: float = 5.0) -> str:
        """描述高丢包率异常"""
        return f"检测到设备 {ip} 丢包率异常，当前丢包率为 {packet_loss_percent:.1f}%，超过阈值 {threshold}%"
    
    def describe_high_latency(self, ip: str, latency_ms: float, threshold_ms: int = 100) -> str:
        """描述高延迟异常"""
        return f"检测到设备 {ip} 延迟异常，当前延迟 {latency_ms:.1f}ms，超过阈值 {threshold_ms}ms"
    
    def describe_port_scan(self, source_ip: str, target_ips: List[str], port_count: int) -> str:
        """描述端口扫描行为"""
        return f"检测到设备 {source_ip} 正在进行端口扫描，扫描了 {len(target_ips)} 个目标IP，共 {port_count} 个端口"
    
    def describe_dhcp_starvation(self, attacker_mac: str, ip_range: str, attempt_count: int) -> str:
        """描述 DHCP 饥饿攻击"""
        device_type = identify_device(attacker_mac)
        formatted_mac = format_mac(attacker_mac)
        return f"检测到 {formatted_mac}（{device_type}）正在发起 DHCP 饥饿攻击，尝试占用 {ip_range} 范围内的 IP，已尝试 {attempt_count} 次"
    
    # ========== 网络状态事件 ==========
    
    def describe_bandwidth_spike(self, interface: str, current_mbps: float, avg_mbps: float) -> str:
        """描述带宽突增"""
        return f"网络接口 {interface} 带宽突增，当前 {current_mbps:.1f}Mbps（平均: {avg_mbps:.1f}Mbps）"
    
    def describe_connection_limit(self, device_ip: str, current: int, limit: int) -> str:
        """描述连接数达到上限"""
        return f"设备 {device_ip} 连接数达到上限，当前 {current} 个连接，最大允许 {limit} 个"
    
    def describe_wifi_clients_exceeded(self, ssid: str, count: int, threshold: int) -> str:
        """描述 WiFi 设备过多"""
        return f"WiFi 网络 {ssid} 当前连接设备数为 {count}，超过建议阈值 {threshold}"
    
    # ========== 汇总描述 ==========
    
    def describe_network_health(self, data: Dict[str, Any]) -> str:
        """描述网络整体健康状态"""
        summary = data.get("summary", {})
        
        online = summary.get("online_devices", 0)
        offline = summary.get("offline_devices", 0)
        total = summary.get("total_devices", 0)
        wifi_clients = summary.get("wifi_clients", 0)
        packet_loss = summary.get("packet_loss", 0)
        latency = summary.get("avg_latency_ms", 0)
        
        parts = []
        
        # 设备状态
        if offline > 0:
            offline_list = summary.get("offline_list", [])
            offline_macs = [identify_device(m) for m in offline_list[:3]]
            parts.append(f"网络中有 {offline} 台设备离线（{', '.join(offline_macs)}...）")
        else:
            parts.append(f"所有 {total} 台设备在线")
        
        # WiFi
        parts.append(f"WiFi 连接了 {wifi_clients} 台设备")
        
        # 网络质量
        if packet_loss > 1.0:
            parts.append(f"⚠️ 丢包率 {packet_loss}% 偏高")
        else:
            parts.append(f"✓ 丢包率正常（{packet_loss}%）")
        
        if latency > 100:
            parts.append(f"⚠️ 延迟 {latency}ms 偏高")
        else:
            parts.append(f"✓ 延迟正常（{latency}ms）")
        
        return "；".join(parts) + "。"
    
    def describe_issue(self, issue: Dict[str, Any]) -> str:
        """描述单个问题 - 扩展支持所有问题类型"""
        issue_type = issue.get("type", "")
        title = issue.get("title", "")
        description = issue.get("description", "")
        severity = issue.get("severity", "info")
        details = issue.get("details", [])
        
        # 严重程度前缀
        severity_prefix = {
            "critical": "🔴 严重：",
            "warning": "🟡 警告：",
            "info": "ℹ️ 信息："
        }.get(severity, "")
        
        # ========== 设备相关问题 ==========
        
        if issue_type == "device_offline":
            if details:
                descriptions = []
                for d in details[:5]:  # 最多描述5个
                    mac = d.get("mac", "")
                    ip = d.get("ip", "")
                    device_type = identify_device(mac)
                    offline_time = d.get("offline_duration_seconds", 0)
                    
                    if offline_time > 0:
                        duration = format_duration(offline_time)
                        descriptions.append(f"{device_type}（{ip}）已离线 {duration}")
                    else:
                        descriptions.append(f"{device_type}（{ip}）离线")
                
                suffix = f"等共 {len(details)} 台设备离线" if len(details) > 5 else ""
                return f"{severity_prefix}设备离线：{'；'.join(descriptions)}。{suffix}"
            return f"{severity_prefix}设备离线：{description}"
        
        elif issue_type == "device_online":
            if details:
                descriptions = []
                for d in details[:3]:
                    mac = d.get("mac", "")
                    ip = d.get("ip", "")
                    device_type = identify_device(mac)
                    descriptions.append(f"{device_type}（{ip}）")
                return f"{severity_prefix}新设备上线：{'，'.join(descriptions)} 等 {len(details)} 台设备上线"
            return f"{severity_prefix}设备上线：{description}"
        
        elif issue_type == "device_new":
            if details:
                descriptions = []
                for d in details:
                    mac = d.get("mac", "")
                    ip = d.get("ip", "")
                    hostname = d.get("hostname", "")
                    device_type = identify_device(mac)
                    
                    if hostname:
                        descriptions.append(f"{device_type} {hostname}（{ip}）")
                    else:
                        descriptions.append(f"{device_type}（{ip}）")
                return f"{severity_prefix}发现新设备：{'；'.join(descriptions)}"
            return f"{severity_prefix}发现新设备：{description}"
        
        # ========== 网络性能问题 ==========
        
        elif issue_type == "packet_loss":
            loss = issue.get("packet_loss", 0)
            threshold = issue.get("threshold", 1.0)
            if severity == "critical":
                return f"{severity_prefix}丢包率严重过高：当前丢包率 {loss}%，已超过严重阈值 {threshold}%。这可能导致网络连接不稳定、视频卡顿、文件传输失败。建议立即检查网络设备或物理连接。"
            return f"{severity_prefix}丢包率偏高：当前丢包率 {loss}%，超过阈值 {threshold}%。建议监控网络拥塞情况。"
        
        elif issue_type == "latency":
            latency = issue.get("latency_ms", 0)
            threshold = issue.get("threshold_ms", 100)
            if severity == "critical":
                return f"{severity_prefix}延迟严重过高：当前平均延迟 {latency}ms，已超过严重阈值 {threshold}ms。这会导致视频通话卡顿、游戏延迟高、网页加载慢。建议检查网络拥塞或设备负载。"
            return f"{severity_prefix}延迟偏高：当前平均延迟 {latency}ms，超过阈值 {threshold}ms。建议持续监控。"
        
        elif issue_type == "jitter":
            jitter = issue.get("jitter_ms", 0)
            return f"{severity_prefix}抖动过大：当前抖动 {jitter}ms。抖动过大会影响实时应用（如视频通话、游戏）的体验。"
        
        elif issue_type == "bandwidth":
            current = issue.get("current_mbps", 0)
            max_bw = issue.get("max_mbps", 0)
            usage = (current / max_bw * 100) if max_bw > 0 else 0
            if usage > 90:
                return f"{severity_prefix}带宽即将耗尽：当前使用 {current:.1f}Mbps，占总带宽的 {usage:.0f}%。建议升级带宽或优化流量。"
            return f"{severity_prefix}带宽使用率较高：当前使用 {current:.1f}Mbps，占总带宽的 {usage:.0f}%"
        
        # ========== WiFi 相关问题 ==========
        
        elif issue_type == "wifi_congestion":
            count = issue.get("client_count", 0)
            threshold = issue.get("threshold", 100)
            ssid = issue.get("ssid", "当前网络")
            return f"{severity_prefix}WiFi 设备过多：{ssid} 当前有 {count} 个设备连接，超过建议阈值 {threshold}。建议考虑增加 AP 或启用负载均衡。"
        
        elif issue_type == "wifi_signal_weak":
            device_ip = issue.get("ip", "")
            signal = issue.get("signal_dbm", 0)
            return f"{severity_prefix}WiFi 信号弱：设备 {device_ip} 信号强度仅 {signal} dBm，可能导致连接不稳定或速度慢。建议调整设备位置或增加 AP。"
        
        elif issue_type == "wifi_channel_congested":
            channel = issue.get("channel", 0)
            congestion = issue.get("congestion_percent", 0)
            ssid = issue.get("ssid", "")
            return f"{severity_prefix}WiFi 信道拥塞：{ssid} 的信道 {channel} 拥塞程度达 {congestion}%。建议更换到更空闲的信道。"
        
        elif issue_type == "wifi_interference":
            channel = issue.get("channel", 0)
            interferer = issue.get("interferer", "未知设备")
            return f"{severity_prefix}WiFi 信道干扰：信道 {channel} 受到 {interferer} 干扰。建议更换信道或调整 AP 设置。"
        
        # ========== DHCP 相关问题 ==========
        
        elif issue_type == "dhcp_pool_exhausted":
            used = issue.get("used_ips", 0)
            total = issue.get("total_ips", 0)
            return f"{severity_prefix}DHCP 地址池耗尽：已分配 {used}/{total} 个 IP，剩余 {total - used} 个可用。建议扩大地址池或清理过期租约。"
        
        elif issue_type == "dhcp_lease_expired":
            count = issue.get("count", 0)
            return f"{severity_prefix}DHCP 租约集中过期：近期有 {count} 个租约过期，可能导致设备批量离线。"
        
        elif issue_type == "dhcp_starvation":
            attacker = issue.get("attacker_mac", "")
            device_type = identify_device(attacker)
            attempts = issue.get("attempts", 0)
            return f"{severity_prefix}检测到 DHCP 饥饿攻击：{device_type}（{attacker}）尝试了大量 DHCP 请求（{attempts} 次），试图耗尽地址池。建议封禁该设备。"
        
        # ========== 安全相关问题 ==========
        
        elif issue_type == "broadcast_storm":
            source_ip = issue.get("source_ip", "")
            source_mac = issue.get("source_mac", "")
            packet_count = issue.get("packet_count", 0)
            device_type = identify_device(source_mac)
            duration = issue.get("duration", "5秒")
            return f"{severity_prefix}广播风暴异常：检测到 {device_type}（{source_ip}）在 {duration} 内发送了 {packet_count} 个广播包，远超正常水平。这会严重占用网络带宽，建议检查该设备。"
        
        elif issue_type == "port_scan":
            source_ip = issue.get("source_ip", "")
            target_count = issue.get("target_count", 0)
            port_count = issue.get("port_count", 0)
            return f"{severity_prefix}端口扫描行为：设备 {source_ip} 正在扫描网络，访问了 {target_count} 个目标IP的 {port_count} 个端口。这可能是恶意行为，建议密切关注。"
        
        elif issue_type == "arp_spoofing":
            attacker_ip = issue.get("attacker_ip", "")
            attacker_mac = issue.get("attacker_mac", "")
            victim_ip = issue.get("victim_ip", "")
            return f"{severity_prefix}ARP 欺骗攻击：检测到 {attacker_ip}（{attacker_mac}）试图欺骗 {victim_ip} 的 ARP 表。这可能是中间人攻击的前兆，建议立即阻断。"
        
        elif issue_type == "unknown_device":
            if details:
                descriptions = []
                for d in details[:3]:
                    mac = d.get("mac", "")
                    ip = d.get("ip", "")
                    descriptions.append(f"{mac}（{ip}）")
                return f"{severity_prefix}发现未知设备：{'，'.join(descriptions)} 等 {len(details)} 个设备无法识别。建议确认是否为可信设备。"
            return f"{severity_prefix}发现未知设备：{description}"
        
        # ========== 系统相关问题 ==========
        
        elif issue_type == "cpu_high":
            usage = issue.get("cpu_percent", 0)
            device = issue.get("device", "路由器")
            return f"{severity_prefix}{device} CPU 负载过高：当前使用率 {usage}%。高负载可能导致性能下降或服务中断。"
        
        elif issue_type == "memory_high":
            usage = issue.get("memory_percent", 0)
            device = issue.get("device", "路由器")
            return f"{severity_prefix}{device} 内存使用过高：当前使用率 {usage}%。内存不足可能导致服务崩溃。"
        
        elif issue_type == "disk_full":
            usage = issue.get("disk_percent", 0)
            device = issue.get("device", "路由器")
            return f"{severity_prefix}{device} 存储空间不足：当前使用率 {usage}%。建议清理日志或扩展存储。"
        
        elif issue_type == "service_down":
            service = issue.get("service", "")
            return f"{severity_prefix}服务异常：{service} 服务已停止或无法访问。建议检查服务状态。"
        
        # ========== 连接相关问题 ==========
        
        elif issue_type == "connection_limit":
            device_ip = issue.get("ip", "")
            current = issue.get("current", 0)
            limit = issue.get("limit", 0)
            return f"{severity_prefix}连接数超限：设备 {device_ip} 当前 {current} 个连接，已达上限 {limit}。可能存在异常连接。"
        
        elif issue_type == "nat_table_full":
            usage = issue.get("usage_percent", 0)
            return f"{severity_prefix}NAT 表满：当前使用率 {usage}%。新连接可能被拒绝，建议优化 NAT 设置或升级设备。"
        
        # ========== 正常状态 ==========
        
        elif issue_type == "healthy":
            return "✅ 网络运行正常，所有指标在正常范围内。"
        
        elif issue_type == "recovered":
            issue_name = issue.get("previous_issue", "问题")
            return f"✅ 已恢复：{issue_name} 已恢复正常运行"
        
        # ========== 默认处理 ==========
        
        else:
            return f"{severity_prefix}{title}：{description}"
    
    # ========== 批量描述 ==========
    
    def describe_all_issues(self, issues: List[Dict[str, Any]]) -> List[str]:
        """批量描述所有问题"""
        return [self.describe_issue(issue) for issue in issues]
    
    def generate_report(self, analysis_result: Dict[str, Any]) -> str:
        """生成完整的分析报告（自然语言）"""
        lines = []
        
        # 标题
        lines.append("📊 网络监控分析报告")
        lines.append("=" * 40)
        
        # 时间
        timestamp = analysis_result.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                lines.append(f"📅 分析时间：{dt.strftime('%Y-%m-%d %H:%M:%S')}")
            except:
                lines.append(f"📅 分析时间：{timestamp}")
        
        lines.append("")
        
        # 整体状态
        summary = analysis_result.get("summary", {})
        health_description = self.describe_network_health(analysis_result)
        lines.append(f"🏥 整体状态：{health_description}")
        lines.append("")
        
        # 详细指标
        lines.append("📈 详细指标：")
        lines.append(f"  • 在线设备：{summary.get('online_devices', 0)} 台")
        lines.append(f"  • 离线设备：{summary.get('offline_devices', 0)} 台")
        lines.append(f"  • WiFi 设备：{summary.get('wifi_clients', 0)} 台")
        lines.append(f"  • 丢包率：{summary.get('packet_loss', 0)}%")
        lines.append(f"  • 平均延迟：{summary.get('avg_latency_ms', 0)} ms")
        lines.append(f"  • 带宽下行：{summary.get('bandwidth_in_mbps', 0):.1f} Mbps")
        lines.append(f"  • 带宽上行：{summary.get('bandwidth_out_mbps', 0):.1f} Mbps")
        lines.append("")
        
        # 问题列表
        issues = analysis_result.get("issues", [])
        if issues:
            lines.append("⚠️ 发现的问题：")
            for i, issue in enumerate(issues, 1):
                desc = self.describe_issue(issue)
                lines.append(f"  {i}. {desc}")
            lines.append("")
        
        # 离线设备详情
        device_status = analysis_result.get("device_status", {})
        offline_devices = [d for d in device_status.get("devices", []) if d.get("status") == "offline"]
        if offline_devices:
            lines.append("📴 离线设备详情：")
            for d in offline_devices[:10]:  # 最多10个
                mac = d.get("mac", "")
                ip = d.get("ip", "")
                device_type = identify_device(mac)
                offline_time = d.get("offline_duration_seconds", 0)
                if offline_time > 0:
                    duration = format_duration(offline_time)
                    lines.append(f"  • {device_type}（{ip}）- 已离线 {duration}")
                else:
                    lines.append(f"  • {device_type}（{ip}）")
            lines.append("")
        
        # WiFi 详情
        wifi_stats = analysis_result.get("wifi_stats", {})
        if wifi_stats:
            lines.append("📶 WiFi 状态：")
            for ap in wifi_stats.get("aps", []):
                ap_name = ap.get("name", "未知")
                clients = ap.get("clients", 0)
                band = ap.get("band", "")
                channel = ap.get("channel", 0)
                lines.append(f"  • {ap_name}（{band}，信道 {channel}）：{clients} 台设备")
            lines.append("")
        
        # 趋势
        trends = analysis_result.get("trends", {})
        if trends and trends.get("data_points", 0) > 0:
            lines.append("📉 趋势分析：")
            pl_trend = trends.get("packet_loss", {})
            if pl_trend:
                lines.append(f"  • 丢包率趋势：{pl_trend.get('trend', 'unknown')}（平均 {pl_trend.get('avg', 0):.2f}%）")
            lat_trend = trends.get("latency", {})
            if lat_trend:
                lines.append(f"  • 延迟趋势：{lat_trend.get('trend', 'unknown')}（平均 {lat_trend.get('avg', 0):.1f}ms）")
            lines.append("")
        
        # 建议
        lines.append("💡 建议：")
        critical_count = sum(1 for i in issues if i.get("severity") == "critical")
        warning_count = sum(1 for i in issues if i.get("severity") == "warning")
        
        if critical_count > 0:
            lines.append(f"  ⚠️ 存在 {critical_count} 个严重问题，建议立即处理")
        if warning_count > 0:
            lines.append(f"  ⚡ 存在 {warning_count} 个警告，建议关注")
        if not issues or (critical_count == 0 and warning_count == 0):
            lines.append("  ✓ 当前无需要特别关注的问题")
        
        return "\n".join(lines)
    
    def generate_daily_summary(self, daily_stats: Dict[str, Any]) -> str:
        """生成每日摘要"""
        lines = []
        
        lines.append("📅 每日网络摘要")
        lines.append("=" * 40)
        
        # 日期
        date = daily_stats.get("date", "")
        lines.append(f"日期：{date}")
        lines.append("")
        
        # 统计
        stats = daily_stats.get("stats", {})
        lines.append("📊 统计数据：")
        lines.append(f"  • 总在线设备数：{stats.get('peak_devices', 0)} 台（峰值）")
        lines.append(f"  • 离线设备数：{stats.get('offline_events', 0)} 次")
        lines.append(f"  • 离线时长：{format_duration(stats.get('total_offline_seconds', 0))}")
        lines.append(f"  • 平均延迟：{stats.get('avg_latency_ms', 0):.1f} ms")
        lines.append(f"  • 最大延迟：{stats.get('max_latency_ms', 0):.1f} ms")
        lines.append(f"  • 平均丢包率：{stats.get('avg_packet_loss', 0):.2f}%")
        lines.append("")
        
        # 事件
        events = daily_stats.get("events", [])
        if events:
            lines.append("📋 重大事件：")
            for event in events[:10]:
                event_type = event.get("type", "")
                count = event.get("count", 0)
                lines.append(f"  • {event_type}：{count} 次")
        
        return "\n".join(lines)


# ========== 便捷函数 ==========

_default_narrator = EventNarrator()


def describe_dhcp_allocate(mac: str, ip: str, hostname: Optional[str] = None, lease_hours: int = 12) -> str:
    """描述 DHCP 分配事件"""
    return _default_narrator.describe_dhcp_allocate(mac, ip, hostname, lease_hours)


def describe_device_offline(mac: str, duration_hours: int = 0, duration_minutes: int = 0) -> str:
    """描述设备离线"""
    return _default_narrator.describe_device_offline_duration(mac, duration_hours, duration_minutes)


def describe_abnormal_broadcast(mac: str, ip: str, packet_count: int, threshold: int) -> str:
    """描述广播风暴异常"""
    return _default_narrator.describe_abnormal_broadcast(mac, ip, packet_count, threshold)


def describe_network_health(data: Dict[str, Any]) -> str:
    """描述网络整体健康状态"""
    return _default_narrator.describe_network_health(data)
