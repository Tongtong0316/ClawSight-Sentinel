#!/usr/bin/env python3
import socketserver
import json
import requests

LOKI_URL = "http://loki:3100/loki/api/v1/push"

class SyslogUDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request[0].strip().decode('utf-8', errors='ignore')
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
        except Exception as e:
            print(f"Error forwarding to Loki: {e}")

if __name__ == "__main__":
    server = socketserver.UDPServer(("0.0.0.0", 514), SyslogUDPHandler)
    print("Syslog receiver listening on UDP port 514...")
    server.serve_forever()
