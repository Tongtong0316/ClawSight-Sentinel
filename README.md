# ClawSight-Sentinel v3.0

> 网络监控日志整合 + 脚本化分析 + 自建 WebUI + 外部 API

## 架构

```
OpenWrt → Syslog → Sentinel → 日志整合 + 时间对齐
                                      ↓
                          [脚本化分析] → 直观指标
                                      ↓
                          [自建 WebUI] → 可视化
                                      ↓
                          [API] → 外部 Agent/LLM 调用
```

## 功能特性

### 1. 日志收集
- Syslog 接收 (UDP 514)
- 标准化时间戳
- 多源数据采集 (SNMP + Syslog)

### 2. 脚本化分析
- 设备在线/离线检测
- 丢包率计算
- 延迟测量
- DHCP 租约分析
- WiFi 连接统计
- 带宽使用监控

### 3. WebUI 可视化
- 仪表盘展示关键指标
- 在线/离线设备列表
- 历史趋势图
- 告警提示

### 4. 外部 API
- `/api/v2/metrics/summary` - 网络健康摘要
- `/api/v2/metrics/device/{ip}` - 单设备指标
- `/api/v2/logs/recent` - 最近日志
- `/api/v2/analysis` - 分析结果

## 快速开始

### 配置

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml 设置 OpenWrt IP 等
```

### Docker 部署

```bash
docker-compose up -d
```

### 访问

- WebUI: http://192.168.0.27:8080
- API: http://192.168.0.27:8080/api/v2

## API 文档

### 网络健康摘要

```bash
GET /api/v2/metrics/summary
```

响应:
```json
{
  "online_devices": 68,
  "offline_devices": 3,
  "offline_list": ["192.168.100.52", "192.168.100.78"],
  "packet_loss": 0.02,
  "avg_latency_ms": 5.2,
  "wifi_clients": 45,
  "alert": "3台设备离线超过 30 分钟"
}
```

### 单设备指标

```bash
GET /api/v2/metrics/device/192.168.100.1
```

### 最近日志

```bash
GET /api/v2/logs/recent?limit=100
```

## 数据来源

| 源 | 协议 | 用途 |
|---|------|------|
| OpenWrt SNMP | UDP 161 | 设备状态、流量、接口 |
| OpenWrt Syslog | UDP 514 | 系统日志、事件 |
| DHCP 租约 | 文件/SSH | 设备在线历史 |

## 技术栈

- FastAPI (Python 3.11)
- Vue.js 3 (前端)
- Chart.js (图表)
- pysnmp (SNMP 采集)
