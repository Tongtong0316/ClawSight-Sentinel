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
        """描述单个问题"""
        issue_type = issue.get("type", "")
        title = issue.get("title", "")
        description = issue.get("description", "")
        
        if issue_type == "device_offline":
            details = issue.get("details", [])
            if details:
                macs = [d.get("mac", "") for d in details[:3]]
                types = [identify_device(m) for m in macs]
                return f"设备离线问题：{', '.join(types)} 等共 {len(details)} 台设备离线。{description}"
            return f"设备离线问题：{description}"
        
        elif issue_type == "packet_loss":
            return f"网络丢包问题：{description}"
        
        elif issue_type == "latency":
            return f"网络延迟问题：{description}"
        
        elif issue_type == "wifi_congestion":
            return f"WiFi 拥塞问题：{description}"
        
        elif issue_type == "healthy":
            return "网络运行正常，所有指标正常"
        
        return f"{title}：{description}"


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
