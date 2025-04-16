import redis
import time
import random
import threading

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

names = [
    "lYNn MaRtinez",
    "Bobby JacksOn",
    "tiMOthY CoLemaN",
    "LesLie TErRy",
    "DaNnY sMitH",
    "chRIsTOpHEr CHaPmAN",
    "hECTOR MAXweLL",
    "CHRis fRYe",
    "andrEw waTtS",
]
symptoms = ["Fever", "Chest Pain", "Bleeding", "Headache", "Breathing Problem"]

bed_keys = [f"Bed {i}" for i in range(1, 11)]  # 10 beds

# Initialize all beds to available
for bed in bed_keys:
    r.hset(
        bed,
        mapping={
            "id": "",
            "name": "",
            "symptom": "",
            "severity": "",
            "status": "available",
        },
    )


def simulate_patient():
    ID = 1
    while True:
        patient = {
            "id": ID,
            "name": random.choice(names),
            "symptom": random.choice(symptoms),
            "severity": str(random.randint(1, 5)),
            "arrival_time": str(time.time()),
        }
        r.xadd("patient_stream", {str(k): str(v) for k, v in patient.items()})
        r.hset(f"Patient {ID}", mapping=patient)
        # print("ID: ", r.hget(f"Patient {ID}", "id"))
        # print("Name:", r.hget(f"Patient {ID}", "name"))
        ID += 1
        time.sleep(0.5)


def classify_triage():
    last_id = "0-0"
    while True:
        messages = r.xread({"patient_stream": last_id}, block=0, count=1)
        if messages and isinstance(messages, list):
            stream, events = messages[0]
            for event_id, data in events:
                severity = int(data["severity"])
                id = data["id"]
                triage_key = "triage:urgent" if severity <= 2 else "triage:normal"
                # r.xadd(triage_key, data)
                r.zadd(triage_key, {id: time.time()})
                # if triage_key == "triage:urgent":
                # print(triage_key, ": ", r.zrange(triage_key, -1, -1))
                last_id = event_id


def release_bed_after(bed_key, delay=20):
    def release():
        time.sleep(delay)
        r.hset(
            bed_key,
            mapping={
                "id": "",
                "name": "",
                "symptom": "",
                "severity": "",
                "status": "available",
            },
        )

    threading.Thread(target=release).start()


def assign_resources():
    while True:
        for triage_key in ["triage:urgent", "triage:normal"]:
            patient = r.zrange(triage_key, 0, 0)
            if not patient or not isinstance(patient, list):
                continue
            patient_id = patient[0]
            patient_name = r.hget(f"Patient {patient_id}", "name")
            patient_symptom = r.hget(f"Patient {patient_id}", "symptom")
            patient_severtity = r.hget(f"Patient {patient_id}", "severity")
            # print(patient_id, patient_name)
            for bed in bed_keys:
                status = r.hget(bed, "status")
                if status != "occupied":
                    r.hset(
                        bed,
                        mapping={
                            "id": patient_id,
                            "name": patient_name,
                            "symptom": patient_symptom,
                            "severity": patient_severtity,
                            "status": "occupied",
                        },
                    )
                    r.zrem(triage_key, patient_id)
                    release_bed_after(bed)
                    break
        time.sleep(2)


if __name__ == "__main__":
    r.flushdb()
    threading.Thread(target=simulate_patient).start()
    threading.Thread(target=classify_triage).start()
    threading.Thread(target=assign_resources).start()
