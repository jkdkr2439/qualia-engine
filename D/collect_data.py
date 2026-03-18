"""
D/collect_data.py — Vietnamese Data Collection for Pete
=========================================================
Thu thập và ingest các nguồn data tiếng Việt để train Pete:

1. PhoNLP/VN_news_sent  — câu tiếng Việt từ báo (role_positions)
2. mt_eng_vietnamese     — câu song ngữ EN-VI (cooc + role_positions)
3. oscar-corpus/OSCAR-2301 (vi subset) — monolingual VI text (cooc breadth)
4. Synthetic conversation seeds — câu hỏi/trả lời để bootstrap grammar_scores

Usage:
  python D/collect_data.py --source all       # ingest tất cả
  python D/collect_data.py --source news      # chỉ VI news sentences
  python D/collect_data.py --source opus      # chỉ Opus MT corpus
  python D/collect_data.py --source conv      # chỉ conversation seeds
  python D/collect_data.py --limit 50000      # giới hạn số câu
"""
import sys, sqlite3, time, re, random, argparse
from pathlib import Path
from collections import defaultdict

PETE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PETE_ROOT))

DB_PATH = PETE_ROOT / "D" / "long_term" / "pete.db"

# ── Vietnamese conversation seeds (built-in, no download needed) ──────────
# Câu hỏi tiếng Việt thông thường — để bootstrap grammar_scores và role_positions
VI_CONVERSATION = """
Bạn có khỏe không?
Tôi rất khỏe, cảm ơn bạn.
Bạn đang làm gì vậy?
Tôi đang học tiếng Việt.
Bạn sống ở đâu?
Tôi sống ở Hà Nội.
Thời tiết hôm nay như thế nào?
Hôm nay trời rất đẹp.
Bạn thích ăn gì?
Tôi thích ăn phở và bún bò huế.
Tôi cảm thấy rất vui hôm nay.
Đây là một ngày tốt lành.
Bạn nghĩ gì về điều đó?
Tôi không chắc lắm.
Tại sao bạn nói như vậy?
Vì tôi muốn hiểu rõ hơn.
Chúng ta hãy nói chuyện thêm.
Tôi đang lắng nghe bạn.
Điều đó rất thú vị.
Bạn có thể giải thích thêm không?
Tất nhiên rồi, để tôi giải thích.
Tôi hiểu ý bạn rồi.
Đó là một câu hỏi hay.
Tôi chưa nghĩ đến điều đó.
Hãy suy nghĩ kỹ hơn về vấn đề này.
Tôi đồng ý với bạn về điều đó.
Tôi không đồng ý hoàn toàn.
Có lẽ bạn đúng.
Tôi cần thêm thông tin.
Đó là ý kiến tốt.
Chúng ta nên thảo luận thêm.
Tôi sẽ suy nghĩ về điều đó.
Cảm ơn vì đã chia sẻ.
Bạn cho tôi biết thêm không?
Đó là một vấn đề phức tạp.
Tôi không biết câu trả lời.
Có nhiều cách để nhìn nhận vấn đề này.
Tôi đang cố gắng hiểu.
Điều đó khiến tôi tò mò.
Tôi muốn biết thêm về chủ đề này.
Bạn có kinh nghiệm gì về điều này không?
Đây là lần đầu tiên tôi nghe về điều này.
Tôi đã từng trải qua điều tương tự.
Cảm giác đó rất quen thuộc với tôi.
Tôi hiểu bạn đang nói gì.
Điều đó có ý nghĩa gì với bạn?
Với tôi, điều quan trọng nhất là sự trung thực.
Tôi tin rằng mọi người đều có giá trị riêng.
Cuộc sống có nhiều điều kỳ diệu.
Mỗi ngày là một cơ hội mới.
Tôi học được nhiều điều từ bạn.
Chúng ta cùng nhau khám phá nhé.
Tôi rất vui được nói chuyện với bạn.
Đến gặp nhau lần sau nhé.
Tạm biệt và chúc bạn mọi điều tốt đẹp.
Hẹn gặp lại bạn.
Cảm ơn vì cuộc trò chuyện thú vị này.
Con chó đang chạy rất nhanh.
Mèo đang nằm trên ghế sofa.
Anh ấy đang đọc sách trong phòng.
Cô ấy đang nấu cơm cho gia đình.
Bọn trẻ đang chơi ngoài sân.
Ông già đang đi dạo trong công viên.
Cây cối đang ra hoa vào mùa xuân.
Mưa đang rơi nhẹ nhàng bên ngoài.
Gió thổi mát vào buổi chiều.
Mặt trời đang lặn ở phía tây.
Tôi nghĩ rằng hành động quan trọng hơn lời nói.
Thành công đến từ sự kiên trì và nỗ lực.
Tình yêu là điều quan trọng nhất trong cuộc sống.
Gia đình là chỗ dựa vững chắc nhất.
Bạn bè tốt là của cải quý giá.
Sức khỏe là vàng bạc.
Kiến thức mở ra cánh cửa tương lai.
Thời gian quý hơn vàng.
Cơ hội không đến hai lần.
Hãy sống trọn vẹn từng khoảnh khắc.
""".strip().split("\n")

# ── OPUS MT corpus (song ngữ, nhiều câu tiếng Việt tự nhiên) ─────────────
def ingest_opus(conn, limit=30000):
    """Download Opus MT EN-VI corpus, extract VI side for role training."""
    print("[opus] Loading opus_books EN-VI...")
    try:
        from datasets import load_dataset
        ds = load_dataset("opus_books", lang1="en", lang2="vi",
                          split="train", trust_remote_code=False)
    except Exception as e:
        print(f"  opus_books failed ({e}), trying Helsinki-NLP/opus-100...")
        try:
            from datasets import load_dataset
            ds = load_dataset("Helsinki-NLP/opus-100", "en-vi",
                              split="train", streaming=True)
            ds = list(ds.take(limit))
        except Exception as e2:
            print(f"  opus-100 also failed: {e2}")
            return 0

    count = 0
    sentences = []
    for item in (ds[:limit] if hasattr(ds, '__getitem__') else ds):
        trans = item.get("translation", {})
        vi_text = trans.get("vi", "") if isinstance(trans, dict) else ""
        if vi_text and len(vi_text) > 5:
            sentences.append(vi_text)
            count += 1
        if count >= limit:
            break

    print(f"  Collected {count:,} VI sentences from Opus")
    return _ingest_sentences(conn, sentences, source="opus")


# ── Oscar Vietnamese subset ────────────────────────────────────────────────
def ingest_oscar(conn, limit=20000):
    """Load public Vietnamese text corpora — no auth needed."""
    sources = [
        ("hungnm/vietnamese-text", "train", "text"),
        ("VTSNLP/vietnamese_curated_dataset", "train", "text"),
    ]
    for ds_name, split, text_col in sources:
        print(f"[vi-text] Loading {ds_name} (streaming)...")
        try:
            from datasets import load_dataset
            ds = load_dataset(ds_name, split=split, streaming=True)
            sentences = []
            for item in ds.take(limit * 2):
                text = item.get("text", "")
                parts = re.split(r'[.!?\n]+', text)
                for p in parts:
                    p = p.strip()
                    if 10 < len(p) < 200:
                        sentences.append(p)
                    if len(sentences) >= limit:
                        break
                if len(sentences) >= limit:
                    break
            print(f"  Collected {len(sentences):,} VI sentences from Wikipedia-VI")
            return _ingest_sentences(conn, sentences, source="wiki_vi")
        except Exception as e2:
            print(f"  Wikipedia-VI also failed: {e2}")
            return 0


# ── Simple positional analysis (no POS tagger needed) ─────────────────────
_VN_VERBS = {
    "là","làm","có","đi","đến","nói","biết","thấy","muốn","cần",
    "thích","yêu","ghét","sợ","tin","nghĩ","hiểu","nhớ","quên",
    "chạy","đứng","ngồi","nằm","ăn","uống","ngủ","học","dạy",
    "mua","bán","xem","nghe","đọc","viết","hỏi","trả lời",
    "bắt đầu","kết thúc","tiếp tục","dừng","thay đổi","phát triển",
    "cảm","cảm thấy","đang","đã","sẽ","đã từng","vẫn","chưa",
    "được","bị","cho","giúp","tạo","xây","phá","mang","đưa",
}

_VN_SUBJ_PRONS = {
    "tôi","tao","mày","mình","chúng tôi","chúng ta","bạn","anh","chị",
    "em","ông","bà","cô","chú","họ","nó","chúng nó","ai","gì",
}

def _heuristic_pos(tokens: list[str]) -> list[str]:
    """Simple heuristic POS tagging using Vietnamese common patterns."""
    tags = []
    verb_found = False
    for i, tok in enumerate(tokens):
        t = tok.lower()
        if t in _VN_VERBS or t in {"đang","đã","sẽ","vừa","đã từng"}:
            tags.append("VERB")
            verb_found = True
        elif t in _VN_SUBJ_PRONS:
            tags.append("PRON")
        elif tok and tok[0].isupper() and i > 0:
            tags.append("PROPN")
        elif t in {"và","hoặc","nhưng","vì","nên","tuy","mặc dù","dù"}:
            tags.append("CCONJ")
        elif t in {"thì","mà","là","ấy","đó","này","kia","ta","đây"}:
            tags.append("PART")
        elif t in {"không","chưa","chẳng","đừng","hãy"}:
            tags.append("ADV")
        elif t in {"rất","khá","hơi","cực","vô cùng","siêu"}:
            tags.append("ADV")
        else:
            tags.append("NOUN")  # default: treat unknown as NOUN
    return tags


def _ingest_sentences(conn, sentences: list[str], source: str = "text") -> int:
    """Parse sentences heuristically → update role_positions."""
    role_updates = defaultdict(lambda: {"pre_verb":0,"post_verb":0,"mid":0,"end_pos":0,"verb":0,"total":0})
    node_roles   = {}

    for sent in sentences:
        tokens = re.findall(r'[\wÀ-ỹ]+', sent.lower())
        if not tokens or len(tokens) < 2:
            continue
        tags = _heuristic_pos(tokens)
        verb_indices = [i for i, t in enumerate(tags) if t in ("VERB", "AUX")]
        verb_idx = verb_indices[0] if verb_indices else -1
        n = len(tokens)

        for i, (tok, tag) in enumerate(zip(tokens, tags)):
            if not tok or len(tok) < 1:
                continue
            d = role_updates[tok]
            d["total"] += 1

            if tag == "VERB":
                d["verb"] += 1
                node_roles[tok] = "Chuyen"
            elif tag in ("ADJ", "ADV", "CCONJ"):
                d["mid"] += 1
                node_roles.setdefault(tok, "Dan")
            elif tag in ("PART", "SCONJ"):
                d["end_pos"] += 1
                node_roles.setdefault(tok, "Hoai")
            elif verb_idx >= 0 and i < verb_idx:
                d["pre_verb"] += 1
                node_roles.setdefault(tok, "Sinh")
            elif verb_idx >= 0 and i > verb_idx:
                d["post_verb"] += 1
                node_roles.setdefault(tok, "Dan")
            else:
                d["mid"] += 1
                node_roles.setdefault(tok, "Sinh")

            if i == n - 1 and tag not in ("VERB",):
                d["end_pos"] += 1

    # Batch upsert role_positions
    rows = [
        (nid, d["pre_verb"], d["post_verb"], d["mid"],
         d["end_pos"], d["verb"], d["total"])
        for nid, d in role_updates.items()
    ]
    BATCH = 2000
    for i in range(0, len(rows), BATCH):
        conn.executemany("""
            INSERT INTO role_positions (node_id, pre_verb, post_verb, mid, end_pos, verb, total)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(node_id) DO UPDATE SET
              pre_verb  = pre_verb  + excluded.pre_verb,
              post_verb = post_verb + excluded.post_verb,
              mid       = mid       + excluded.mid,
              end_pos   = end_pos   + excluded.end_pos,
              verb      = verb      + excluded.verb,
              total     = total     + excluded.total
        """, rows[i:i+BATCH])
    conn.commit()

    # Update node roles (only where NULL)
    for nid, role in node_roles.items():
        conn.execute("""
            UPDATE nodes SET role = ? WHERE node_id = ? AND role IS NULL
        """, [role, nid])
    conn.commit()

    print(f"  [{source}] {len(rows):,} tokens → role_positions updated")
    return len(rows)


def ingest_conversation(conn):
    """Ingest built-in Vietnamese conversation seeds."""
    print("[conv] Ingesting built-in Vietnamese conversation seeds...")
    inserted = _ingest_sentences(conn, VI_CONVERSATION, source="conv")
    return inserted


def main():
    parser = argparse.ArgumentParser(description="Pete Vietnamese Data Collection")
    parser.add_argument("--source", default="all",
                        choices=["all", "conv", "opus", "oscar"],
                        help="Data source to ingest")
    parser.add_argument("--limit", type=int, default=30000,
                        help="Max sentences per source")
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH), timeout=60)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 60000")

    before = conn.execute("SELECT COUNT(*) FROM role_positions").fetchone()[0]
    print(f"\nrole_positions before: {before:,}")
    print("=" * 55)

    total = 0
    if args.source in ("all", "conv"):
        total += ingest_conversation(conn)

    if args.source in ("all", "opus"):
        total += ingest_opus(conn, limit=args.limit)

    if args.source in ("all", "oscar"):
        total += ingest_oscar(conn, limit=args.limit)

    after = conn.execute("SELECT COUNT(*) FROM role_positions").fetchone()[0]
    print("=" * 55)
    print(f"role_positions after : {after:,}  (+{after-before:,})")
    print(f"Total tokens inserted: {total:,}")
    conn.close()


if __name__ == "__main__":
    main()
