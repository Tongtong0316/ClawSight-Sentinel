"""
WiFi 无线环境扫描器
使用连接在 Debian 上的 USB 无线网卡检测周围 WiFi 环境
"""
import asyncio
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class WifiNetwork:
    """WiFi 网络信息"""
    ssid: str
    bssid: str  # MAC 地址
    signal_dbm: int
    signal_percent: int
    channel: int
    frequency: int
    band: str  # 2.4G / 5G / 6G
    security: str  # WPA3, WPA2, WPA, WEP, Open
    hidden: bool = False


@dataclass
class ChannelStats:
    """信道统计"""
    channel: int
    frequency: int
    band: str
    utilization_percent: int  # 拥堵度 0-100
    networks_count: int
    networks: List[WifiNetwork]


@dataclass
class WifiScanResult:
    """扫描结果"""
    timestamp: str
    interface: str
    mode: str  # monitor / managed
    networks: List[WifiNetwork]
    channels_2g: List[ChannelStats]
    channels_5g: List[ChannelStats]
    channels_6g: List[ChannelStats]
    recommendations: List[str]


class WifiScanner:
    """WiFi 环境扫描器"""
    
    def __init__(self, interface: str = "wlan0", config: Optional[Dict] = None):
        self.interface = interface
        self.config = config or {}
        self.storage_path = Path(self.config.get("storage_path", "/data/sentinel"))
        
        # 信道定义
        self.channels_2g = [c for c in range(1, 14)]  # 1-11 常用
        self.channels_5g = [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144, 149, 153, 157, 161, 165]
        
        # 2.4G 信道中心频率
        self.freq_2g = {
            1: 2412, 2: 2417, 3: 2422, 4: 2427, 5: 2432, 6: 2437, 7: 2442, 
            8: 2447, 9: 2452, 10: 2457, 11: 2462, 12: 2467, 13: 2472
        }
        
    async def scan(self) -> WifiScanResult:
        """执行 WiFi 扫描"""
        # 获取接口模式
        mode = await self._get_interface_mode()
        
        # 切换到监听模式（如果需要）
        if mode != "monitor":
            await self._set_monitor_mode()
        
        # 执行扫描
        networks = await self._do_scan()
        
        # 分析信道拥堵
        channels_2g = await self._analyze_channels(networks, "2.4G")
        channels_5g = await self._analyze_channels(networks, "5G")
        channels_6g = await self._analyze_channels(networks, "6G")
        
        # 生成建议
        recommendations = self._generate_recommendations(channels_2g, channels_5g)
        
        return WifiScanResult(
            timestamp=datetime.now().isoformat(),
            interface=self.interface,
            mode=mode,
            networks=networks,
            channels_2g=channels_2g,
            channels_5g=channels_5g,
            channels_6g=channels_6g,
            recommendations=recommendations
        )
    
    async def _run_cmd(self, cmd: List[str], timeout: int = 30) -> str:
        """运行命令"""
        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=timeout)
            return stdout.decode() if stdout else ""
        except asyncio.TimeoutError:
            return ""
        except Exception as e:
            print(f"Command error: {e}")
            return ""
    
    async def _get_interface_mode(self) -> str:
        """获取接口模式"""
        output = await self._run_cmd(["iw", self.interface, "info"])
        if "type monitor" in output.lower():
            return "monitor"
        elif "type managed" in output.lower():
            return "managed"
        return "unknown"
    
    async def _set_monitor_mode(self) -> bool:
        """切换到监听模式"""
        # 先 down 接口
        await self._run_cmd(["ip", "link", "set", self.interface, "down"])
        # 设置监听模式
        await self._run_cmd(["iw", self.interface, "set", "type", "monitor"])
        # up 接口
        await self._run_cmd(["ip", "link", "set", self.interface, "up"])
        return True
    
    async def _do_scan(self) -> List[WifiNetwork]:
        """执行扫描"""
        networks = []
        
        # 方法1: 使用 iwlist (需要安装)
        output = await self._run_cmd(["iwlist", self.interface, "scan"])
        if output:
            networks = self._parse_iwlist_output(output)
        
        # 方法2: 使用 iw (更现代)
        if not networks:
            output = self._do_iw_scan_sync()
            if output:
                networks = self._parse_iw_output(output)
        
        # 方法3: 使用 airmon-ng + airodump-ng (需要 root)
        if not networks:
            networks = self._do_airodump_scan()
        
        return networks
    
    def _do_iw_scan_sync(self) -> str:
        """同步执行 iw 扫描"""
        try:
            result = subprocess.run(
                ["iw", self.interface, "scan", "dump"],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout
        except:
            return ""
    
    def _do_airodump_scan(self) -> List[WifiNetwork]:
        """使用 airodump-ng 扫描"""
        # 这是一个后台方法，实际生产环境可能需要单独进程
        return []
    
    def _parse_iwlist_output(self, output: str) -> List[WifiNetwork]:
        """解析 iwlist 输出"""
        networks = []
        current = {}
        
        for line in output.split("\n"):
            line = line.strip()
            
            if "Cell " in line:
                if current.get("bssid"):
                    networks.append(self._create_network(current))
                current = {"bssid": line.split("Address:")[1].strip()}
            
            elif "ESSID:" in line:
                ssid = line.split("ESSID:")[1].strip('"')
                current["ssid"] = ssid if ssid else ""
                current["hidden"] = ssid == ""
            
            elif "Signal level" in line:
                # Signal level=-45 dBm
                try:
                    signal = line.split("Signal level=")[1].split(" ")[0].replace("=", "")
                    current["signal_dbm"] = int(signal)
                except:
                    pass
            
            elif "Channel" in line and "Frequency" not in line:
                try:
                    current["channel"] = int(line.split("Channel")[1].strip().split(" ")[0])
                except:
                    pass
            
            elif "Frequency" in line:
                try:
                    freq = line.split("Frequency:")[1].split(" ")[0].strip()
                    current["frequency"] = int(float(freq.replace("GHz", "")) * 1000)
                except:
                    pass
            
            elif "Encryption key:off" in line:
                current["security"] = "Open"
            
            elif "WPA2" in line:
                current["security"] = "WPA2"
            elif "WPA3" in line:
                current["security"] = "WPA3"
            elif "WEP" in line:
                current["security"] = "WEP"
        
        if current.get("bssid"):
            networks.append(self._create_network(current))
        
        return networks
    
    def _parse_iw_output(self, output: str) -> List[WifiNetwork]:
        """解析 iw scan dump 输出"""
        networks = []
        current = {}
        
        for line in output.split("\n"):
            line = line.strip()
            
            if line.startswith("BSS "):
                if current.get("bssid"):
                    networks.append(self._create_network(current))
                bssid = line.split("(")[0].replace("BSS", "").strip()
                current = {"bssid": bssid.replace("'", "").upper()}
            
            elif "SSID:" in line:
                ssid = line.split("SSID:")[1].strip()
                current["ssid"] = ssid if ssid else ""
            
            elif "signal:" in line:
                try:
                    signal = line.split("signal:")[1].strip().split(" ")[0]
                    current["signal_dbm"] = float(signal)
                except:
                    pass
            
            elif "freq:" in line:
                try:
                    freq = line.split("freq:")[1].strip().split(" ")[0]
                    current["frequency"] = int(freq)
                except:
                    pass
            
            elif "channel:" in line:
                try:
                    channel = line.split("channel:")[1].strip().split(" ")[0]
                    current["channel"] = int(channel)
                except:
                    pass
        
        if current.get("bssid"):
            networks.append(self._create_network(current))
        
        return networks
    
    def _create_network(self, data: Dict) -> WifiNetwork:
        """创建网络对象"""
        # 计算信号百分比 (-100 dBm = 0%, -30 dBm = 100%)
        signal_dbm = data.get("signal_dbm", -100)
        signal_percent = max(0, min(100, (signal_dbm + 100) * 100 // 70))
        
        # 确定频段
        freq = data.get("frequency", 0)
        if freq < 3000:
            band = "2.4G"
        elif freq < 6000:
            band = "5G"
        else:
            band = "6G"
        
        # 确定信道
        channel = data.get("channel")
        if not channel:
            channel = self._freq_to_channel(freq)
        
        return WifiNetwork(
            ssid=data.get("ssid", ""),
            bssid=data.get("bssid", ""),
            signal_dbm=signal_dbm,
            signal_percent=signal_percent,
            channel=channel,
            frequency=freq,
            band=band,
            security=data.get("security", "Unknown"),
            hidden=data.get("hidden", False)
        )
    
    def _freq_to_channel(self, freq: int) -> int:
        """频率转信道"""
        if freq in self.freq_2g.values():
            for ch, f in self.freq_2g.items():
                if f == freq:
                    return ch
        # 5G 信道计算
        if freq > 5000:
            return (freq - 5000) // 5
        return 0
    
    async def _analyze_channels(self, networks: List[WifiNetwork], band: str) -> List[ChannelStats]:
        """分析信道拥堵"""
        if band == "2.4G":
            channel_list = self.channels_2g
        elif band == "5G":
            channel_list = self.channels_5g
        else:
            return []
        
        result = []
        
        for ch in channel_list:
            # 找到该信道上的所有网络
            ch_networks = [n for n in networks if n.channel == ch]
            
            if not ch_networks:
                result.append(ChannelStats(
                    channel=ch,
                    frequency=self.freq_2g.get(ch, 5000 + ch * 5),
                    band=band,
                    utilization_percent=0,
                    networks_count=0,
                    networks=[]
                ))
                continue
            
            # 计算拥堵度
            # 基于：网络数量 + 信号强度
            signal_avg = sum(n.signal_dbm for n in ch_networks) / len(ch_networks)
            
            # 信号强度权重 (-30dBm = 强, -90dBm = 弱)
            signal_weight = max(0, (signal_avg + 90) / 60)  # 0-1
            
            # 网络数量权重
            count_weight = min(1.0, len(ch_networks) / 5)  # 5个网络就满分
            
            utilization = int((signal_weight * 0.7 + count_weight * 0.3) * 100)
            utilization = min(100, utilization)
            
            result.append(ChannelStats(
                channel=ch,
                frequency=self.freq_2g.get(ch, 5000 + ch * 5),
                band=band,
                utilization_percent=utilization,
                networks_count=len(ch_networks),
                networks=ch_networks
            ))
        
        return result
    
    def _generate_recommendations(self, channels_2g: List[ChannelStats], channels_5g: List[ChannelStats]) -> List[str]:
        """生成建议"""
        recs = []
        
        # 2.4G 分析
        best_2g = min(channels_2g, key=lambda c: c.utilization_percent)
        if best_2g.utilization_percent > 70:
            recs.append(f"⚠️ 2.4G 频段拥堵严重，建议使用 5G 频段")
        elif best_2g.utilization_percent > 40:
            recs.append(f"ℹ️ 2.4G 推荐信道: {best_2g.channel}（拥堵度 {best_2g.utilization_percent}%）")
        
        # 5G 分析
        best_5g = min(channels_5g, key=lambda c: c.utilization_percent)
        if channels_5g:
            if best_5g.utilization_percent > 70:
                recs.append(f"⚠️ 5G 频段也较拥堵，推荐信道: {best_5g.channel}")
            else:
                recs.append(f"✅ 5G 推荐信道: {best_5g.channel}（拥堵度 {best_5g.utilization_percent}%）")
        
        # 检查隐藏网络
        hidden_count = sum(1 for c in channels_2g + channels_5g for n in c.networks if n.hidden)
        if hidden_count > 0:
            recs.append(f"ℹ️ 检测到 {hidden_count} 个隐藏网络")
        
        # 检查信道重叠
        overlapping = self._check_channel_overlap(channels_2g)
        if overlapping:
            recs.append(f"⚠️ 检测到信道重叠: {', '.join(overlapping)}")
        
        if not recs:
            recs.append("✅ WiFi 环境良好，无明显问题")
        
        return recs
    
    def _check_channel_overlap(self, channels: List[ChannelStats]) -> List[str]:
        """检查信道重叠（2.4G）"""
        issues = []
        for ch in channels:
            if ch.utilization_percent > 60:
                # 检查相邻信道
                neighbor_chs = [c for c in channels if abs(c.channel - ch.channel) <= 2 and c.utilization_percent > 40]
                if neighbor_chs:
                    issues.append(f"{ch.channel}信道与{[c.channel for c in neighbor_chs]}重叠")
        return issues[:3]
    
    # ========== 便捷方法 ==========
    
    async def quick_scan(self) -> Dict:
        """快速扫描 - 返回精简结果"""
        result = await self.scan()
        
        return {
            "timestamp": result.timestamp,
            "networks_count": len(result.networks),
            "best_channel_2g": min(result.channels_2g, key=lambda c: c.utilization_percent).channel if result.channels_2g else None,
            "best_channel_5g": min(result.channels_5g, key=lambda c: c.utilization_percent).channel if result.channels_5g else None,
            "recommendations": result.recommendations,
            "networks": [
                {
                    "ssid": n.ssid or "(隐藏)",
                    "bssid": n.bssid,
                    "signal": n.signal_dbm,
                    "channel": n.channel,
                    "band": n.band,
                    "security": n.security
                }
                for n in result.networks[:20]  # 最多20个
            ]
        }
    
    async def get_neighbors(self) -> List[Dict]:
        """获取邻近网络列表"""
        result = await self.scan()
        
        neighbors = []
        for net in result.networks:
            if net.ssid:  # 排除隐藏网络
                neighbors.append({
                    "ssid": net.ssid,
                    "bssid": net.bssid,
                    "signal_dbm": net.signal_dbm,
                    "signal_percent": net.signal_percent,
                    "channel": net.channel,
                    "band": net.band,
                    "security": net.security
                })
        
        # 按信号强度排序
        neighbors.sort(key=lambda x: x["signal_dbm"], reverse=True)
        return neighbors
    
    async def get_channel_status(self, band: str = "2.4G") -> List[Dict]:
        """获取信道状态"""
        result = await self.scan()
        
        if band == "2.4G":
            channels = result.channels_2g
        else:
            channels = result.channels_5g
        
        return [
            {
                "channel": ch.channel,
                "utilization": ch.utilization_percent,
                "networks_count": ch.networks_count,
                "networks": [
                    {"ssid": n.ssid or "(隐藏)", "signal": n.signal_dbm}
                    for n in ch.networks[:3]
                ]
            }
            for ch in channels
        ]


# ========== 便捷函数 ==========

_default_scanner: Optional[WifiScanner] = None


def get_scanner(interface: str = "wlan0") -> WifiScanner:
    """获取扫描器实例"""
    global _default_scanner
    if not _default_scanner:
        _default_scanner = WifiScanner(interface)
    return _default_scanner


async def quick_scan(interface: str = "wlan0") -> Dict:
    """快速扫描"""
    scanner = WifiScanner(interface)
    return await scanner.quick_scan()


async def get_neighbors(interface: str = "wlan0") -> List[Dict]:
    """获取邻近网络"""
    scanner = WifiScanner(interface)
    return await scanner.get_neighbors()
