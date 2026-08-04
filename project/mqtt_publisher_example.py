"""
Simple MQTT publisher example for Raspberry Pi.
Usage:
  python mqtt_publisher_example.py --broker broker.hivemq.com --topic sensor/stress_data --interval 5

This script can run in simulation mode (random values) or be adapted to read real sensors.
"""

import time
import json
import argparse
import random
import uuid
import os
import sys

import paho.mqtt.client as mqtt


def build_payload(device_id=None):
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload = {
        "device_id": device_id or f"raspi-{uuid.uuid4().hex[:6]}",
        "timestamp": now,
        "heart_rate": round(random.uniform(60, 90), 1),
        "spo2": round(random.uniform(95, 99), 1),
        "stress_level": round(random.uniform(0, 100), 1)
    }
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", default=os.environ.get("MQTT_BROKER", "broker.hivemq.com"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MQTT_PORT", 1883)))
    parser.add_argument("--topic", default=os.environ.get("MQTT_TOPIC", "sensor/stress_data"))
    parser.add_argument("--interval", type=float, default=float(os.environ.get("PUBLISH_INTERVAL", 5.0)))
    parser.add_argument("--client-id", default=None)
    parser.add_argument("--qos", type=int, default=1)
    parser.add_argument("--simulate", action="store_true", help="Use simulated random data (default).")
    args = parser.parse_args()

    client_id = args.client_id or f"pub-{uuid.uuid4().hex[:8]}"
    client = mqtt.Client(client_id=client_id)

    try:
        client.connect(args.broker, args.port)
    except Exception as exc:
        print("MQTT connect failed:", exc)
        sys.exit(1)

    client.loop_start()
    print(f"Publishing to {args.broker}:{args.port} topic={args.topic} every {args.interval}s")

    try:
        while True:
            if args.simulate:
                payload = build_payload()
            else:
                # Replace this block with real sensor reads on Raspberry Pi
                payload = build_payload()

            payload_json = json.dumps(payload)
            rc = client.publish(args.topic, payload_json, qos=args.qos)
            print(time.strftime("%Y-%m-%d %H:%M:%S"), "PUBLISHED ->", payload_json)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Stopping publisher")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == '__main__':
    main()
