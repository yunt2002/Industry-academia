import json
import paho.mqtt.client as mqtt

BROKER_ADDRESS = "broker.hivemq.com"
TOPIC = "sensor/stress_data"


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[SUB] MQTT 연결 성공")
        client.subscribe(TOPIC)
    else:
        print(f"[SUB] 연결 실패: {rc}")


def on_message(client, userdata, msg):
    print(f"[SUB] 수신: {msg.payload.decode('utf-8')}")


if __name__ == "__main__":
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER_ADDRESS, 1883, 60)
    client.loop_forever()
