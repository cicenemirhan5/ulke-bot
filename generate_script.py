"""Her gün yeni bölümün senaryosunu üretir -> output/today.json"""
import json
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent
cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
state_path = ROOT / "state.json"
state = json.loads(state_path.read_text(encoding="utf-8"))


def main():
    day = state["day"] + 1
    history = "\n".join(f"Gün {e['day']}: {e['summary']}" for e in state["history"][-7:]) or "Henüz olay yok, ülke bugün kuruluyor."
    votes = state.get("last_votes", {"A": 0, "B": 0})
    total_citizens = len(state["citizens"])

    prompt = f"""Instagram Reels için "{cfg['country_name']}" adlı sanal bir mikro ulus serisinin {day}. gün bölümünü yaz.
Ton: {cfg['tone']}.
Vatandaş sayısı: {total_citizens}.
Son günlerin özeti:
{history}
Dünkü halk oylaması sonucu (A seçeneği / B seçeneği yorum sayısı): A={votes['A']}, B={votes['B']}. Kazanan seçeneği bugünkü olaya sonuç olarak yansıt (gün 1 ise yok say).

Kurallar:
- Türkçe, konuşma dili, toplam 80-100 kelime (yaklaşık 30-40 saniye seslendirme).
- Tam 4 sahne. İlk sahne güçlü bir kanca (ilk 2 saniyede merak uyandır).
- Gün 1 ise ülkenin kuruluşunu, adını, sloganını ve "vatandaş olmak için yoruma adını ve mesleğini yaz" çağrısını anlat.
- Son sahne iki seçenekli (A/B) bir karar sorusuyla bitsin ve izleyiciye "yorumlara A ya da B yaz; yeni vatandaşsan adını ve mesleğini de ekle" desin.
- Gerçek kişi, marka veya siyasi parti kullanma. Nefret, şiddet, cinsellik yok.
- visual_text: ekranda görünecek kısa yazı, en fazla 7 kelime.

SADECE şu JSON'u döndür, başka hiçbir şey yazma:
{{
  "title": "bölüm başlığı",
  "scenes": [{{"narration": "seslendirilecek metin", "visual_text": "ekran yazısı"}}],
  "summary": "bu bölümde olanların 1 cümlelik özeti (hafıza için)",
  "option_a": "A seçeneği kısa",
  "option_b": "B seçeneği kısa",
  "caption": "Instagram açıklaması, 2-3 satır, sonunda A/B çağrısı",
  "hashtags": ["#sanalülke", "..."]
}}"""

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=cfg["model"],
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text
    data = json.loads(text[text.index("{"): text.rindex("}") + 1])
    assert len(data["scenes"]) >= 3, "Senaryo çok kısa geldi"

    data["day"] = day
    data["full_caption"] = (data["caption"] + "\n\n" + " ".join(data["hashtags"]))[:2200]
    data["first_comment"] = f"A: {data['option_a']}\nB: {data['option_b']}\n\nOy vermek için A ya da B yaz. Yeni vatandaşsan adını ve mesleğini de ekle."

    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    (out / "today.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    state["day"] = day
    state["history"].append({"day": day, "summary": data["summary"]})
    state["last_votes"] = {"A": 0, "B": 0}
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Gün {day} senaryosu hazır: {data['title']}")


if __name__ == "__main__":
    main()
