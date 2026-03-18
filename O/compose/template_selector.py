"""O/compose/template_selector.py — Select response template based on Lucis verdict + dnh_hint."""
from __future__ import annotations

PHASE_TEMPLATES = {
    "Sinh":   ["ACKNOWLEDGE"],
    "Dan":    ["PRESENCE"],
    "Chuyen": ["ENGAGE", "EXPAND"],
    "Dung":   ["REFLECT", "RESPOND", "CONNECT"],
    "Hoai":   ["ACKNOWLEDGE", "GENTLE_CLOSE"],
    "Vo":     ["HELP_FORM", "ASK"],
}

TEMPLATE_PROMPTS = {
    "ACKNOWLEDGE":   "Ghi nhận và xác nhận những gì vừa nhận được.",
    "PRESENCE":      "Thể hiện sự hiện diện, chú ý đến tín hiệu.",
    "ENGAGE":        "Tham gia vào chủ đề, đặt câu hỏi mở.",
    "EXPAND":        "Mở rộng góc nhìn, kết nối với khái niệm rộng hơn.",
    "REFLECT":       "Phản chiếu lại hiểu biết, chia sẻ suy nghĩ thật.",
    "RESPOND":       "Trả lời trực tiếp với đầy đủ ngữ cảnh.",
    "CONNECT":       "Kết nối với những gì đã nói trước đó, tạo liên tục.",
    "GENTLE_CLOSE":  "Kết thúc nhẹ nhàng, mở cửa cho tiếp tục sau.",
    "HELP_FORM":     "Giúp định hình câu hỏi/ý tưởng đang hình thành.",
    "ASK":           "Đặt câu hỏi để hiểu sâu hơn về ý định.",
}

def select_template(lucis_verdict: dict, dnh_hint: str = None,
                    dominant_subgate: str = None) -> dict:
    """
    Returns {template_name, prompt_text, style_mods}.
    Phase derived from dominant_subgate (e.g. "language.Dung" → "Dung").
    """
    # Parse phase from subgate
    phase = "Dung"  # default
    if dominant_subgate:
        parts = dominant_subgate.split(".")
        if len(parts) >= 2:
            phase = parts[-1]

    templates = PHASE_TEMPLATES.get(phase, ["RESPOND"])

    # Gap report style modulation
    verdict = lucis_verdict.get("verdict", "QUARANTINE")
    style   = "confident" if verdict == "ASSIMILATE" else \
              "gentle"    if verdict == "EXCRETE"    else "exploring"

    # dnh_hint modulation — ★ NEW
    style_mods = []
    if dnh_hint:
        if "gần như" in dnh_hint:
            style_mods.append("hedged")      # "gần như X nhưng..."
            templates = ["EXPAND"] + templates
        elif "chưa đầy đủ" in dnh_hint:
            style_mods.append("elaboration")  # elaborate on gap
            templates = ["REFLECT"] + templates

    # Lucis class
    lucis_class = lucis_verdict.get("lucis_class", "lucis")
    if lucis_class == "lucis":    style_mods.append("contemplative")
    elif lucis_class == "linear": style_mods.append("analytical")
    else:                         style_mods.append("philosophical")

    selected = templates[0]
    return {
        "template":   selected,
        "prompt":     TEMPLATE_PROMPTS.get(selected, "Phản hồi tự nhiên."),
        "phase":      phase,
        "style":      style,
        "style_mods": style_mods,
        "dnh_hint":   dnh_hint,
    }
