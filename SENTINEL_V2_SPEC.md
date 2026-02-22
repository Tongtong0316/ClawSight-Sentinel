# Sentinel Web UI 优化规格书

## 1. Web 界面设计

### 1.1 页面结构
```
/                       - 仪表盘 (系统状态概览)
/settings               - 设置页面
/logs                   - 日志查看页面
/analysis               - 分析历史页面
/fix                    - 危机修复页面
```

### 1.2 仪表盘内容
- 系统状态 (CPU/内存/网络)
- 最近分析结果摘要
- 快速操作按钮
- 告警提示

### 1.3 设置选项
```yaml
analysis:
  frequency_minutes: 5      # 分析频率
  max_logs_per_analysis: 2000  # 每次分析最大日志数
  auto_fix_enabled: false   # 自动修复
  
logs:
  retention_days: 30        # 保留天数
  max_size_gb: 28          # 最大存储 GB
  
models:
  default: "gemma:2b"      # 默认模型
  temperature: 0.7         # 温度参数
  
notifications:
  enabled: false
  webhook_url: ""
```

### 1.4 危机修复功能
- 一键重启服务
- 网络诊断
- 清理缓存
- 回滚配置

## 2. 日志保存逻辑

### 2.1 目录结构
```
/mnt/tf_card/sentinel/
├── raw_logs/              # 原始日志
│   └── YYYY-MM-DD.log
├── analysis/              # 分析结论
│   └── YYYY-MM-DD.json
└── config/                # 配置文件
    └── settings.yaml
```

### 2.2 保存逻辑
1. 原始日志: OpenWRT → Syslog → Loki → TF卡
2. 分析结论: AI 分析结果 → JSON 格式化 → TF卡
3. 存储管理: 检查存储，超出则删除最旧文件

## 3. 分析结论标准化输出

### 3.1 JSON 格式
```json
{
  "timestamp": "2026-02-22T14:30:00Z",
  "model": "gemma:2b",
  "input_logs_count": 1500,
  "diagnosis": {
    "summary": "网络正常运行",
    "issues": [
      {
        "severity": "warning",
        "description": "DHCP 租约即将过期",
        "recommendation": "检查设备连接状态"
      }
    ],
    "metrics": {
      "cpu_usage": "5%",
      "memory_usage": "45%",
      "connections": 128
    }
  },
  "confidence": 0.85
}
```

### 3.2 严重等级
- **critical**: 紧急需要处理
- **warning**: 需要关注
- **info**: 正常信息
