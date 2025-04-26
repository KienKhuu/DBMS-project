from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import threading
import redis
import time
from time import perf_counter

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

app = Flask(__name__)
socketio = SocketIO(app)


@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/triage")
def get_triage():
    # Convert zrange results to lists explicitly
    urgent_ids = r.zrange("triage:urgent", 0, -1) or []
    normal_ids = r.zrange("triage:normal", 0, -1) or []
    emergency_ids = r.zrange("triage:emergency", 0, -1) or []

    urgent = []
    for patient_id in urgent_ids:
        patient_data = r.hgetall(f"Patient {patient_id}")
        urgent.append(patient_data)

    normal = []
    for patient_id in normal_ids:
        patient_data = r.hgetall(f"Patient {patient_id}")
        normal.append(patient_data)

    emergency = []
    for patient_id in emergency_ids:
        patient_data = r.hgetall(f"Patient {patient_id}")
        emergency.append(patient_data)

    return jsonify({"urgent": urgent, "normal": normal, "emergency": emergency})


@app.route("/beds")
def get_beds():
    beds = {}
    for i in range(1, 6):
        key = f"Bed {i}"
        beds[key] = r.hgetall(key)
    return jsonify(beds)


@app.route("/move_to_emergency/<patient_id>", methods=["POST"])
def move_to_emergency(patient_id):
    start_time = perf_counter()

    r.zrem("triage:urgent", patient_id)
    r.zrem("triage:normal", patient_id)
    r.zadd("triage:emergency", {patient_id: time.time()})

    end_time = perf_counter()
    processing_time = end_time - start_time

    r.lpush("processing_logs", f"move_to_emergency:{processing_time}")
    return jsonify({"status": "success", "processing_time": processing_time})


@app.route("/processing_logs")
def get_processing_logs():
    logs = r.lrange("processing_logs", 0, 9)  # Lấy 10 log gần nhất
    return jsonify({"logs": logs})


def emit_updates():
    pubsub = r.pubsub()
    pubsub.psubscribe("__keyspace@0__:*")
    for message in pubsub.listen():
        socketio.emit("update", {"data": "refresh"})


if __name__ == "__main__":
    r.flushdb()
    threading.Thread(target=emit_updates).start()
    socketio.run(app, debug=True)
