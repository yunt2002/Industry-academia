import json
import os
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional


class MonitoringServerState:
    def __init__(self):
        self._lock = threading.Lock()
        self.latest = {
            "heart_rate": 0,
            "spo2": 0,
            "stress": 0,
            "stress_level": None,
            "alert": None,
            "trend_score": None,
            "timestamp": None,
        }

    def update(self, payload: dict):
        with self._lock:
            self.latest.update(payload)
            self.latest.setdefault("timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self.latest)


class MonitoringRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = self.path.split('?', 1)[0]
        query = {}
        if '?' in self.path:
            for part in self.path.split('?', 1)[1].split('&'):
                if '=' in part:
                    key, value = part.split('=', 1)
                    query[key] = value

        normalized_path = parsed_path.rstrip('/') or '/'

        if normalized_path == "/health":
            self._send_json({"status": "ok", "service": "stress-monitor"})
        elif normalized_path == "/latest":
            self._send_json(self.server.state.snapshot())
        elif normalized_path == "/api/history":
            self._send_json(self._load_history(query))
        elif normalized_path == "/dashboard":
            # allow language override via query param, e.g. /dashboard?lang=ko
            self._send_html(self._render_dashboard(query.get('lang', None)))
        elif normalized_path == "/":
            self._send_html(self._render_index())
        else:
            self._send_json({"status": "ok", "message": "stress monitoring server"}, status=404)

    def log_message(self, format, *args):
        return

    def _send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, body: str, status: int = 200):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _load_history(self, query: dict):
        limit = int(query.get('limit', 10))
        db_path = os.path.join(os.path.dirname(__file__), 'stress_data.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            'SELECT timestamp, heart_rate, spo2, stress_level FROM sensor_log ORDER BY id DESC LIMIT ?',
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def _render_dashboard(self, lang: str = None):
        # server-side translations for simple i18n
        is_ko = False
        if lang:
            try:
                is_ko = str(lang).lower().startswith('ko')
            except Exception:
                is_ko = False

        if is_ko:
            title = '스트레스 모니터링 대시보드'
            latest_title = '최신 스냅샷'
            recent_history = '최근 기록'
            label_hr = '심박수'
            label_spo2 = '혈중산소'
            label_stress = '스트레스'
        else:
            title = 'Stress Monitoring Dashboard'
            latest_title = 'Latest snapshot'
            recent_history = 'Recent history'
            label_hr = 'Heart Rate'
            label_spo2 = 'SpO2'
            label_stress = 'Stress'

        html_lang = 'ko' if is_ko else 'en'
        html = """
        <!doctype html>
        <html lang="__HTML_LANG__">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>__TITLE__</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; background: #07111f; color: #f4f7fb; }
                .container { max-width: 980px; margin: 0 auto; padding: 24px; }
                .card { background: #111c2f; border: 1px solid #2d3e5e; border-radius: 14px; padding: 20px; margin-bottom: 16px; }
                .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
                .metric { background: #18253c; padding: 14px; border-radius: 12px; }
                .metric .label { color: #8da3c7; font-size: 12px; text-transform: uppercase; }
                .metric .value { font-size: 24px; font-weight: bold; margin-top: 6px; }
                table { width: 100%; border-collapse: collapse; }
                th, td { text-align: left; padding: 10px; border-bottom: 1px solid #2d3e5e; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>__TITLE__</h1>
                    <p>Live monitoring server for sensor data and recent history.</p>
                </div>
                <div class="card">
                    <h2>__LATEST_TITLE__</h2>
                    <div class="grid" id="latest">
                        <div class="metric"><div class="label">__LABEL_HR__</div><div class="value" id="hr">--</div></div>
                        <div class="metric"><div class="label">__LABEL_SPO2__</div><div class="value" id="spo2">--</div></div>
                        <div class="metric"><div class="label">__LABEL_STRESS__</div><div class="value" id="stress">--</div></div>
                    </div>
                </div>
                <div class="card">
                    <h2>__RECENT_HISTORY__</h2>
                    <table>
                        <thead><tr><th>Timestamp</th><th>Heart Rate</th><th>SpO2</th><th>Stress</th></tr></thead>
                        <tbody id="history"></tbody>
                    </table>
                </div>
            </div>
            <script>
                async function loadData() {
                    const latestRes = await fetch('/latest');
                    const latest = await latestRes.json();
                    document.getElementById('hr').textContent = latest.heart_rate ?? '--';
                    document.getElementById('spo2').textContent = latest.spo2 ?? '--';
                    document.getElementById('stress').textContent = latest.stress ?? '--';

                    const historyRes = await fetch('/api/history?limit=8');
                    const history = await historyRes.json();
                    const rows = history.map(function(item){
                        return '<tr><td>' + (item.timestamp ?? '-') + '</td><td>' + (item.heart_rate ?? '-') + '</td><td>' + (item.spo2 ?? '-') + '</td><td>' + (item.stress_level ?? '-') + '</td></tr>';
                    }).join('');
                    document.getElementById('history').innerHTML = rows;
                }
                loadData();
                setInterval(loadData, 3000);
            </script>
        </body>
        </html>
        """

        html = html.replace('__HTML_LANG__', html_lang)
        html = html.replace('__TITLE__', title)
        html = html.replace('__LATEST_TITLE__', latest_title)
        html = html.replace('__LABEL_HR__', label_hr)
        html = html.replace('__LABEL_SPO2__', label_spo2)
        html = html.replace('__LABEL_STRESS__', label_stress)
        html = html.replace('__RECENT_HISTORY__', recent_history)
        return html

    def _render_index(self):
        return """
        <!doctype html>
        <html lang=\"en\">
        <head>
            <meta charset=\"utf-8\">
            <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
            <title>Stress Monitoring Server</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; background: #07111f; color: #f4f7fb; }
                .container { max-width: 720px; margin: 0 auto; padding: 24px; }
                .card { background: #111c2f; border: 1px solid #2d3e5e; border-radius: 14px; padding: 20px; margin-bottom: 16px; }
                a { color: #58a6ff; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class=\"container\">
                <div class=\"card\">
                    <h1>Stress Monitoring Server</h1>
                    <p>Use the links below to open the dashboard or query endpoints.</p>
                    <ul>
                        <li><a href=\"/dashboard\">Dashboard (EN)</a></li>
                        <li><a href=\"/dashboard?lang=ko\">대시보드 (한국어)</a></li>
                        <li><a href=\"/health\">Health</a></li>
                        <li><a href=\"/latest\">Latest JSON</a></li>
                        <li><a href=\"/api/history?limit=8\">History JSON</a></li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """


class MonitoringHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_class, state: MonitoringServerState):
        super().__init__(server_address, handler_class)
        self.state = state


def start_monitoring_server(state: Optional[MonitoringServerState] = None, host: str = "0.0.0.0", port: int = 8765):
    server_state = state or MonitoringServerState()
    # Initialize latest snapshot from DB if available
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'stress_data.db')
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute('SELECT timestamp, heart_rate, spo2, stress_level FROM sensor_log ORDER BY id DESC LIMIT 1').fetchone()
            conn.close()
            if row:
                try:
                    server_state.update({
                        'heart_rate': float(row['heart_rate']) if row['heart_rate'] is not None else 0,
                        'spo2': float(row['spo2']) if row['spo2'] is not None else 0,
                        'stress': float(row['stress_level']) if row['stress_level'] is not None else 0,
                        'timestamp': row['timestamp']
                    })
                except Exception:
                    pass
    except Exception:
        pass

    server = MonitoringHTTPServer((host, port), MonitoringRequestHandler, server_state)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def stop_monitoring_server(server: Optional[MonitoringHTTPServer]):
    if server is not None:
        try:
            server.shutdown()
        except Exception:
            pass
        try:
            server.server_close()
        except Exception:
            pass


def main():
    state = MonitoringServerState()
    server, thread = start_monitoring_server(state, host='0.0.0.0', port=8765)
    print('Monitoring server started on http://0.0.0.0:8765')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop_monitoring_server(server)
        thread.join(timeout=2)


if __name__ == '__main__':
    main()
