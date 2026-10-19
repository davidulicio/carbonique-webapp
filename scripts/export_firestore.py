"""Read-only Firestore export. Install firebase-admin separately; never commit credentials."""
import argparse
import json
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore

parser = argparse.ArgumentParser()
parser.add_argument("--credential", required=True, help="Local Firebase service-account JSON, outside this repository")
parser.add_argument("--output", required=True)
args = parser.parse_args()
firebase_admin.initialize_app(credentials.Certificate(args.credential))
db = firestore.client()
result = {"format": "carbonique-field-log-v1", "members": [{"id": d.id, **d.to_dict()} for d in db.collection("members").stream()], "sites": []}
for doc in db.collection("sites").stream():
    site = {"id": doc.id, **doc.to_dict()}
    for collection in ["tasks", "visits", "comments"]:
        site[collection] = [{"id": d.id, **d.to_dict()} for d in doc.reference.collection(collection).stream()]
    result["sites"].append(site)
Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, default=lambda value: value.isoformat()), encoding="utf-8")
print(f"Exported {len(result['sites'])} sites to the requested local file.")
