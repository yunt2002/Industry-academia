"""
End-to-end test: publish one message to MQTT broker and verify it arrives in DB and updates /latest.
Usage: run while `monitor_main.py` is running (with MQTT enabled in monitor_config.json).
"""
import time
import json
import uuid
import urllib.request
import sqlite3
import os
import sys

import paho.mqtt.client as mqtt

BROKER = 'broker.hivemq.com'
PORT = 1883
TOPIC = 'sensor/stress_data'

unique_id = f'test-{uuid.uuid4().hex[:8]}'
now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
heart_rate = round(60 + (uuid.uuid4().int % 40) + (uuid.uuid4().int % 10)/10.0, 1)
payload = {
    'device_id': unique_id,
    'timestamp': now,
    'heart_rate': heart_rate,
    'spo2': 98.0,
    'stress_level': 12.3
}

print('Publishing payload:', payload)
client = mqtt.Client()
try:
    client.connect(BROKER, PORT)
except Exception as e:
    print('MQTT connect failed:', e)
    sys.exit(1)
client.loop_start()
client.publish(TOPIC, json.dumps(payload), qos=1)
client.loop_stop()
client.disconnect()

# Wait for the subscriber to process and DB to be updated
print('Waiting for server to ingest message...')
for i in range(12):
    try:
        r = urllib.request.urlopen('http://127.0.0.1:8765/api/history?limit=10', timeout=3)
        data = r.read().decode()
        if unique_id in data or now in data:
            print('Found in /api/history:', data)
            break
    except Exception as e:
        pass
    time.sleep(1)
else:
    print('Not found in /api/history after wait')

# Check /latest
try:
    r = urllib.request.urlopen('http://127.0.0.1:8765/latest', timeout=3)
    latest = json.loads(r.read().decode())
    print('/latest:', latest)
    if abs(latest.get('heart_rate', 0) - heart_rate) < 0.5:
        print('Latest matches published heart_rate')
    else:
        print('Latest does not match published heart_rate')
except Exception as e:
    print('Error fetching /latest:', e)

# Check DB directly
db_path = os.path.join(os.path.dirname(__file__), 'stress_data.db')
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id,timestamp,heart_rate,spo2,stress_level FROM sensor_log ORDER BY id DESC LIMIT 20").fetchall()
    found = False
    for r in rows:
        rec = dict(r)
        if rec.get('timestamp') == now or rec.get('heart_rate') == heart_rate:
            print('Found in DB:', rec)
            found = True
            break
    if not found:
        print('Not found in DB recent rows (showing recent rows):')
        for r in rows[:5]:
            print(dict(r))
    conn.close()
else:
    print('DB not found:', db_path)
