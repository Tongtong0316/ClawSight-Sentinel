FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    snmp \
    && rm -rf /var/lib/apt/lists/*

# 复制代码
COPY sentinel_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sentinel_api/ .

# 创建数据目录
RUN mkdir -p /data/sentinel/logs /data/sentinel/config

EXPOSE 8080

CMD ["uvicorn", "sentinel_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
