FROM python:3.11-slim

RUN pip install --no-cache-dir requests

WORKDIR /app

COPY syslog_receiver.py /app/receiver.py

EXPOSE 514/udp
CMD ["python", "/app/receiver.py"]
