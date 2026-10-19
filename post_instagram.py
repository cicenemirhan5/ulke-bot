"""Videoyu Instagram'a Reels olarak yükler ve ilk yorumu atar."""
import json
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent
GRAPH = "https://graph.instagram.com/v21.0"
IG = os.environ["IG_USER_ID"]
TOKEN = os.environ["IG_ACCESS_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")


def call(method, url, **kw):
    r = requests.request(method, url, timeout=60, **kw)
    if not r.ok:
        raise RuntimeError(f"{r.status_code}: {r.text}")
    return r.json()


def main():
    data = json.loads((ROOT / "output" / "today.json").read_text(encoding="utf-8"))
    video_url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{data['video_path']}"

    container = call("POST", f"{GRAPH}/{IG}/media", data={
        "media_type": "REELS",
        "video_url": video_url,
        "caption": data["full_caption"],
        "share_to_feed": "true",
        "access_token": TOKEN,
    })["id"]

    for _ in range(40):
        status = call("GET", f"{GRAPH}/{container}", params={"fields": "status_code", "access_token": TOKEN})["status_code"]
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError("Instagram videoyu işleyemedi (video URL'si herkese açık mı?)")
        time.sleep(15)
    else:
        raise RuntimeError("Instagram işlemi zaman aşımına uğradı")

    media_id = call("POST", f"{GRAPH}/{IG}/media_publish", data={"creation_id": container, "access_token": TOKEN})["id"]
    print("Yayınlandı:", media_id)

    try:
        call("POST", f"{GRAPH}/{media_id}/comments", data={"message": data["first_comment"], "access_token": TOKEN})
    except RuntimeError as e:
        print("İlk yorum atılamadı:", e)

    sp = ROOT / "state.json"
    state = json.loads(sp.read_text(encoding="utf-8"))
    state["last_media_id"] = media_id
    sp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
