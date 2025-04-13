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
    urgent = r.zrange("triage:urgent", 0, -1)
    normal = r.zrange("triage:normal", 0, -1)
    return jsonify({"urgent": urgent, "normal": normal})


@app.route("/beds")
def get_beds():
    beds = {}
    for i in range(1, 21):
        key = f"bed:{i}"
        beds[key] = r.hgetall(key)
    return jsonify(beds)


def emit_updates():
    pubsub = r.pubsub()
    pubsub.psubscribe("__keyspace@0__:*")
    for message in pubsub.listen():
        socketio.emit("update", {"data": "refresh"})


if __name__ == "__main__":
    threading.Thread(target=emit_updates).start()
    socketio.run(app, debug=True)
