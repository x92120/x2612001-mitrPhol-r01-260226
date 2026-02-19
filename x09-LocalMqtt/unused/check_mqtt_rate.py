
import paho.mqtt.client as mqtt
import time
import json
from collections import defaultdict

counts = defaultdict(int)
start_time = time.time()
sample_data = {}

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe("scale/scale-01")
    client.subscribe("scale/scale-02")
    client.subscribe("scale/scale-03")

def on_message(client, userdata, msg):
    topic = msg.topic
    counts[topic] += 1
    try:
        sample_data[topic] = json.loads(msg.payload.decode())
    except:
        sample_data[topic] = msg.payload.decode()

client = mqtt.Client()
client.username_pw_set("admin", "admin")  # Using default creds from previous context if any
# Wait, the bridge code uses admin/admin.
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect("localhost", 1883, 60)
    client.loop_start()
    
    print("Monitoring MQTT topics for 5 seconds...")
    time.sleep(5)
    
    elapsed = time.time() - start_time
    print("-" * 50)
    print(f"Monitoring Duration: {elapsed:.2f}s")
    print("-" * 50)
    
    for topic in ["scale/scale-01", "scale/scale-02", "scale/scale-03"]:
        count = counts[topic]
        rate = count / elapsed
        print(f"Topic: {topic}")
        print(f"  Count: {count}")
        print(f"  Rate:  {rate:.2f} msg/sec")
        print(f"  Latest Data: {sample_data.get(topic, 'No Data')}")
        print("-" * 50)
        
except Exception as e:
    print(f"Error: {e}")
finally:
    client.loop_stop()
    client.disconnect()
