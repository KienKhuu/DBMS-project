from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import threading
import redis

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

    urgent = []
    for patient_id in urgent_ids:
        patient_data = r.hgetall(f"Patient {patient_id}")
        urgent.append(patient_data)

    normal = []
    for patient_id in normal_ids:
        patient_data = r.hgetall(f"Patient {patient_id}")
        normal.append(patient_data)

    return jsonify({"urgent": urgent, "normal": normal})


@app.route("/beds")
def get_beds():
    beds = {}
    for i in range(1, 11):
        key = f"Bed {i}"
        beds[key] = r.hgetall(key)
    return jsonify(beds)


def emit_updates():
    pubsub = r.pubsub()
    pubsub.psubscribe("__keyspace@0__:*")
    for message in pubsub.listen():
        socketio.emit("update", {"data": "refresh"})


if __name__ == "__main__":
    r.flushdb()
    threading.Thread(target=emit_updates).start()
    socketio.run(app, debug=True)
