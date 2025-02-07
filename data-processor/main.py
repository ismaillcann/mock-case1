import os
import json
import redis
from influxdb import InfluxDBClient

def process_data():
    # Redis Connection
    redis_host = os.environ.get("REDIS HOST", "localhost")
    redis_client = redis.Redis(host=redis_host, port=6379, db=0)
    pubsub = redis_client.pubsub()
    pubsub.subscribe("data_channel")

    # InfluxDB connection
    influx_host= os.environ.get("INFLUXDB_HOST", "localhost")
    influx_port = int(os.environ.get("INFLUXDB_PORT", 8086))
    influx_db = os.environ.get("INFLUXDB_DB", "sensor_data")
    influx_client = InfluxDBClient(host=influx_host, port=influx_port)
    influx_client.switch_database(influx_db)

    print("Data Processor is listening...")
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                json_body = [
                    {
                        "measurement": "sensor_measurement",
                        "tags": {
                            "device_name": data["device"]
                        },
                        "fields": {
                            "observation": float(data["observation"])
                        },
                        "time": data["timestamp"]
                    }
                ]
                influx_client.write_points(json_body)
                print("Written in InfluxDB:", json_body)
            except Exception as e:
                print("Data process error:", e)

if __name__ == "__main__":
    process_data()