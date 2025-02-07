from flask import Flask, request, jsonify
import redis
import os
import json
from influxdb import InfluxDBClient
from datetime import datetime

app = Flask(__name__)

# Redis Connection
redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_client = redis.Redis(host= redis_host, port= 6379, db= 0)
REDIS_CHANNEL = "data_channel"

# Influx Connection
influx_host = os.environ.get("INFLUXDB_HOST", "localhost")
influx_port = int(os.environ.get("INFLUXDB_PORT", 8086))
influx_db = os.environ.get("INFLUXDB_DB", "sensor_data")
influx_client = InfluxDBClient(host=influx_host, port=influx_port)
influx_client.switch_database(influx_db)

@app.route('/data/<provider>/<device>/<observation>', methods=['PUT'])
def receive_data(provider, device, observation):
    data = {
        "provider": provider,
        "device": device,
        "observation": observation,
        "timestamp": datetime.utcnow().isoformat()
    }
    # sending data to pubsub channel
    redis_client.publish(REDIS_CHANNEL, json.dumps(data))
    return "Data received", 200

@app.route('/query', methods=['GET'])
def query_data():
    start = request.args.get("start")
    end = request.args.get("end")
    device_name = request.args.get("device_name")

    # Influx request, timestamp should be ISO format
    query = (
        f"SELECT * FROM sensor_measurement "
        f"WHERE device_name = '{device_name}' "
        f"AND time >= '{start}' AND time <= '{end}'"
    )
    result = influx_client.query(query)

    data_points = list(result.get_points())
    return jsonify(data_points)

if __name__ == '__main__':
    app.run(debug = True, host = '0.0.0.0', port = 5000)