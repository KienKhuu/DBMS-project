import redis
import time
import random
import threading

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

names = ["John", "Alice", "Bob", "Mary", "David", "Sara", "Tom", "Lily"]
symptoms = ["Fever", "Chest Pain", "Bleeding", "Headache", "Breathing Problem"]

bed_keys = [f"bed:{i}" for i in range(1, 21)]  # 20 beds

# Initialize all beds to available
for bed in bed_keys:
    r.hset(bed, mapping={"patient": "", "status": "available"})


def simulate_patient():
    while True:
        patient = {
            "name": random.choice(names),
            "symptom": random.choice(symptoms),
            "severity": str(random.randint(1, 5)),
            "arrival_time": str(time.time()),
        }
        r.xadd("patient_stream", {str(k): str(v) for k, v in patient.items()})
        time.sleep(1)


def classify_triage():
    last_id = "0-0"
    while True:
        messages = r.xread({"patient_stream": last_id}, block=0, count=1)
        if messages and isinstance(messages, list):
            stream, events = messages[0]
            for event_id, data in events:
                severity = int(data["severity"])
                name = data["name"]
                triage_key = "triage:urgent" if severity <= 2 else "triage:normal"
                r.zadd(triage_key, {name: time.time()})
                last_id = event_id


def release_bed_after(bed_key, patient_name, delay=20):
    def release():
        time.sleep(delay)
        r.hset(bed_key, mapping={"patient": "", "status": "available"})

    threading.Thread(target=release).start()


def assign_resources():
    while True:
        for triage_key in ["triage:urgent", "triage:normal"]:
            patient = r.zrange(triage_key, 0, 0)
            if not patient or not isinstance(patient, list):
                continue
            patient_name = patient[0]
            for bed in bed_keys:
                status = r.hget(bed, "status")
                if status != "occupied":
                    r.hset(bed, mapping={"patient": patient_name, "status": "occupied"})
                    r.zrem(triage_key, patient_name)
                    release_bed_after(bed, patient_name)
                    break
        time.sleep(1)


if __name__ == "__main__":
    threading.Thread(target=simulate_patient).start()
    threading.Thread(target=classify_triage).start()
    threading.Thread(target=assign_resources).start()
