from flask import Flask, request, jsonify, send_file
import io
import redis
import os
import json
from influxdb import InfluxDBClient
from datetime import datetime
import pandas as pd 
from fpdf import FPDF

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

@app.route('/report', methods=['GET'])
def generate_report():
    start = request.args.get("start")
    end = request.args.get("end")
    device_name = request.args.get("device_name")
    report_format = request.args.get("format", "pdf") # default to 'pdf' if not provided

    # Validate required parameters
    if not (start and end and device_name):
        return jsonify({"error": "start, end, and device_name parameters are required "}), 400
    
    # Query InfluxDB
    query = (
        f"SELECT * FROM sensor_measurement "
        f"WHERE device_name = '{device_name}' "
        f"AND time >= '{start}' AND time <= '{end}'" 
    )
    result = influx_client.query(query)
    data_points = list(result.get_points())

    if not data_points:
        return jsonify({"error": "No data found for given parameters"}), 404
    
    # Excel report
    if report_format.lower() == 'excel':
        # create a Pandas DataFrame from the data
        df = pd.DataFrame(data_points)
        output = io.BytesIO()
        # write the DataFrame to an Excel file in memory
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Report')
            writer.save()
        output.seek(0)
        return send_file(
            output,
            attachment_filename="report.xlsx",
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # PDF report
    elif report_format.lower() == 'pdf':
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        # Title and header information
        pdf.cell(200, 10, txt="Sensor Report", ln=True, align='C')
        pdf.cell(200, 10, txt=f"Device: {device_name}", ln=True, align='C')
        pdf.ln(10)

        # If there is data, extract headers from the first record
        headers = list(data_points[0].keys())
        col_width = pdf.w / (len(headers) + 1)  # basic calculation for cell width
        
        # Table header row
        for header in headers:
            pdf.cell(col_width, 10, header, border=1)
        pdf.ln()

        # Data rows
        for point in data_points:
            for header in headers:
                pdf.cell(col_width, 10, str(point.get(header, '')), border=1)
            pdf.ln()

        # Output the PDF into a BytesIO buffer
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        return send_file(
            pdf_output,
            attachment_filename="report.pdf",
            as_attachment=True,
            mimetype="application/pdf"
        )
    
    else:
        return jsonify({"error": "Invalid format. Supported formats: pdf, excel"}), 400


if __name__ == '__main__':
    app.run(debug = True, host = '0.0.0.0', port = 5000)