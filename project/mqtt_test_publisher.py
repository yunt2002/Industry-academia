import json
import random
import time
import paho.mqtt.client as mqtt

BROKER_ADDRESS = "broker.hivemq.com"
TOPIC = "sensor/stress_data"


def publish_test_data(count=5, interval=1.0):
    client = mqtt.Client()
    client.connect(BROKER_ADDRESS, 1883, 60)

    for i in range(count):
        payload = {
            "heart_rate": round(random.uniform(70, 95), 1),
            "spo2": round(random.uniform(96, 100), 1),
            "stress": round(random.uniform(20, 80), 1),
        }
        client.publish(TOPIC, json.dumps(payload), qos=1)
        print(f"[{i+1}/{count}] Published: {payload}")
        time.sleep(interval)

    client.disconnect()


if __name__ == "__main__":
    publish_test_data()
