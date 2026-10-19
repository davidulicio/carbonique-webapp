"""Extract JSON constants and embedded media without executing the HTML's JavaScript."""
import argparse
import base64
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("html", type=Path)
parser.add_argument("--output", type=Path, required=True, help="Destination directory for fieldnotes.json and media/")
args = parser.parse_args()
text = args.html.read_text(encoding="utf-8")
data = {}
for name in ["NOTES", "PIPE", "PLOTS", "SITEINFO"]:
    match = re.search(r"const\s+" + name + r"\s*=\s*", text)
    if not match:
        raise SystemExit(f"Missing {name} constant. Use the self-contained Carbonique Field Notes format.")
    data[name], _ = json.JSONDecoder().raw_decode(text[match.end():])
args.output.mkdir(parents=True, exist_ok=True)
(args.output / "media").mkdir(exist_ok=True)
def save_image(value, name):
    name = re.sub(r"[^A-Za-z0-9_-]", "_", name)
    prefix, encoded = value.split(",", 1)
    if prefix not in {"data:image/jpeg;base64", "data:image/png;base64"}:
        raise SystemExit("Only embedded JPEG and PNG media are supported.")
    ext = ".png" if "png" in prefix else ".jpg"
    rel = "media/" + name + ext
    (args.output / rel).write_bytes(base64.b64decode(encoded, validate=True))
    return rel
data["plots"] = {k: save_image(v, k) for k, v in data.pop("PLOTS").items()}
for site in data["SITEINFO"]["sites"]:
    for i, photo in enumerate(site.get("photos", [])):
        photo["path"] = save_image(photo.pop("src"), f"{site['code'].upper()}-{i+1}")
(args.output / "fieldnotes.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Extracted {len(data['NOTES'])} notes, {len(data['PIPE'])} caveats and {len(data['SITEINFO']['sites'])} sites.")
