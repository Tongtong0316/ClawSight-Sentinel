# ClawSight-Sentinel 系统架构规格说明书 (v0.1)

## 1. 核心容器堆栈 (Docker Compose)
- **loki**: 日志存储引擎，挂载点指向直通的 TF 卡 (`/mnt/tf_card/loki`)。
- **promtail**: 日志采集代理，监听 514/udp (Syslog)。
- **prometheus**: 性能指标库。
- **grafana**: 可视化面板，预置 WiFi 频谱与流量监控 Dashboard。
- **ollama**: AI 分析引擎，受限使用 1.5 核心。
- **sentinel-api**: 核心业务逻辑，包含：
    - Agent 自解释接口 (`/agent/bootstrap`)。
    - 危机修复控制器 (Playwright 驱动)。
    - 定时巡检调度器。

## 2. Agent 接入协议 (ClawSight Protocol)
- **发现机制**: Agent 访问 `GET /api/v1/instruction` 获取 DSL 描述。
- **分析流**: Agent 发送日志片段至 `POST /api/v1/ai/analyze` 获取专家建议。
- **执行流**: Agent 确认方案后发送密钥至 `POST /api/v1/exec/reboot`。

## 3. 硬件亲和性配置 (PVE/N305)
- 限制 Sentinel 容器仅在 CPU 核心 6, 7 运行，避免干扰核心 0-4 的 10G NAT 转发。
