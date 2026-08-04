import json
import os
import sqlite3
import time
import unittest
import urllib.request

from monitor_server import MonitoringServerState, start_monitoring_server, stop_monitoring_server


class MonitoringServerTest(unittest.TestCase):
    def test_server_state_and_http_endpoints(self):
        state = MonitoringServerState()
        server, thread = start_monitoring_server(state, host='127.0.0.1', port=8765)
        try:
            time.sleep(0.3)
            state.update({"heart_rate": 80, "spo2": 97, "stress": 30})

            db_path = os.path.join(os.path.dirname(__file__), '..', 'stress_data.db')
            conn = sqlite3.connect(db_path)
            conn.execute('CREATE TABLE IF NOT EXISTS sensor_log (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, heart_rate REAL, spo2 REAL, stress_level REAL)')
            conn.execute('INSERT INTO sensor_log (heart_rate, spo2, stress_level) VALUES (?, ?, ?)', (80, 97, 30))
            conn.commit()
            conn.close()

            with urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=2) as response:
                self.assertEqual(response.status, 200)
                body = json.loads(response.read().decode('utf-8'))
                self.assertEqual(body['status'], 'ok')

            with urllib.request.urlopen('http://127.0.0.1:8765/latest', timeout=2) as response:
                self.assertEqual(response.status, 200)
                body = json.loads(response.read().decode('utf-8'))
                self.assertEqual(body['heart_rate'], 80)
                self.assertEqual(body['spo2'], 97)
                self.assertEqual(body['stress'], 30)

            with urllib.request.urlopen('http://127.0.0.1:8765/', timeout=2) as response:
                self.assertEqual(response.status, 200)
                html = response.read().decode('utf-8')
                self.assertIn('Stress Monitoring Server', html)
                self.assertIn('/dashboard', html)

            with urllib.request.urlopen('http://127.0.0.1:8765/dashboard', timeout=2) as response:
                self.assertEqual(response.status, 200)
                html = response.read().decode('utf-8')
                self.assertIn('Stress Monitoring Dashboard', html)

            with urllib.request.urlopen('http://127.0.0.1:8765/api/history?limit=5', timeout=2) as response:
                self.assertEqual(response.status, 200)
                body = json.loads(response.read().decode('utf-8'))
                self.assertGreaterEqual(len(body), 1)
        finally:
            stop_monitoring_server(server)
            thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
