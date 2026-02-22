#!/usr/bin/env python3
import socketserver
import json
import requests
import sys

LOKI_URL = "http://loki:3100/loki/api/v1/push"

class SyslogUDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request[0].strip().decode('utf-8', errors='ignore')
        print(f"Received: {data[:50]}", file=sys.stderr)
        # Parse syslog format (simplified)
        payload = {
            "streams": [
                {
                    "labels": "{job=\"openwrt\", host=\"openwrt-router\"}",
                    "entries": [
                        {"ts": "", "line": data}
                    ]
                }
            ]
        }
        try:
            requests.post(LOKI_URL, json=payload, timeout=5)
            print("Sent to Loki", file=sys.stderr)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    print("Starting syslog receiver on UDP 514...", file=sys.stderr)
    server = socketserver.UDPServer(("0.0.0.0", 514), SyslogUDPHandler)
    print("Listening...", file=sys.stderr)
    server.serve_forever()
