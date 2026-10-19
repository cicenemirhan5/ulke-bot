"""Son videonun yorumlarını okur: yeni kişilere vatandaşlık verir, A/B oylarını sayar."""
import json
import os
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent
GRAPH = "https://graph.instagram.com/v21.0"
TOKEN = os.environ["IG_ACCESS_TOKEN"]
MAX_REPLIES = 40  # bir çalıştırmada en fazla bu kadar yanıt (spam sınırlarına takılmamak için)

sp = ROOT / "state.json"
state = json.loads(sp.read_text(encoding="utf-8"))


def get_comments(media_id):
    url = f"{GRAPH}/{media_id}/comments"
    params = {"fields": "id,text,username", "limit": 100, "access_token": TOKEN}
    while url:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        j = r.json()
        yield from j.get("data", [])
        url = j.get("paging", {}).get("next")
        params = None


def parse_role(text):
    t = re.sub(r"^\s*[ABab]\b[\s,.:;-]*", "", text).strip()
    return (t[:40] or "Vatandaş")


def main():
    media_id = state.get("last_media_id")
    if not media_id:
        print("Henüz paylaşım yok, atlanıyor.")
        return

    votes = {"A": 0, "B": 0}
    replied = 0
    for c in get_comments(media_id):
        text = (c.get("text") or "").strip()
        user = c.get("username")
        if not user:
            continue
        m = re.match(r"^\s*([ABab])\b", text)
        if m:
            votes[m.group(1).upper()] += 1

        if user not in state["citizens"] and replied < MAX_REPLIES:
            num = state["next_number"]
            role = parse_role(text)
            msg = f"Hoş geldin @{user}! Vatandaş no: {num:03d}. Mesleğin: {role}."
            r = requests.post(f"{GRAPH}/{c['id']}/replies", data={"message": msg, "access_token": TOKEN}, timeout=60)
            if r.ok:
                state["citizens"][user] = {"no": num, "role": role}
                state["next_number"] = num + 1
                replied += 1
                time.sleep(3)
            else:
                print("Yanıt atılamadı:", r.text)

    state["last_votes"] = votes
    sp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Oylar: {votes}, yeni vatandaş: {replied}, toplam: {len(state['citizens'])}")


if __name__ == "__main__":
    main()
