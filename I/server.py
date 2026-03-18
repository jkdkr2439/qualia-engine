"""
I/server.py — Pete v4 FastAPI server.
Endpoints: / (UI), /chat, /stats, /graph, /trace
"""
from __future__ import annotations
import json, sys, os, asyncio, threading, time
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

# Path setup
BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

app = FastAPI(title="Pete v4")

# ── Static UI ────────────────────────────────────────────────────────────────
STATIC = Path(__file__).parent / "static"
if not STATIC.exists(): STATIC.mkdir()
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

# ── State ────────────────────────────────────────────────────────────────────
_engine = None
_i_engine = None
_last_trace: dict = {}
_chat_log: list = []

def _autosave_to_db():
    """Flush in-memory node_store to SQLite pete.db (non-blocking)."""
    if _engine is None: return
    try:
        from D.db import get_db
        db = get_db()
        nodes = list(_engine._node_store.values())
        with db._tx():
            for node in nodes:
                db.upsert_node(node)
        from O.compose.grammar_learner import save_store
        from P.think.semantic.p1.role_classifier import save_roles
        save_store()
        save_roles()
    except Exception as e:
        pass  # never crash the server over a save

def _load_engine():
    global _engine, _i_engine
    print("[server] Loading PEngine...")
    from P.p_engine import PEngine
    from I.core import IEngine
    from D.bootstrap import bootstrap
    bootstrap()
    _engine  = PEngine()
    _i_engine = IEngine()
    print(f"[server] Ready. {_engine.stats}")

@app.on_event("startup")
async def startup():
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _load_engine)

# ── UI ───────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root():
    html = STATIC / "index.html"
    if html.exists():
        return HTMLResponse(html.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Pete v4 — UI not found. Place index.html in I/static/</h1>")

# ── Chat ─────────────────────────────────────────────────────────────────────
@app.post("/chat")
async def chat(payload: dict):
    global _last_trace
    if _engine is None:
        return JSONResponse({"error": "Engine loading, please wait..."}, status_code=503)

    text = payload.get("text", "").strip()
    if not text:
        return JSONResponse({"error": "empty"}, status_code=400)

    # Process through I → P
    event  = _i_engine.process(text, source="user", modality="chat")
    result = _engine.process(event, mode=payload.get("mode", "NORMAL"))

    # Build response text
    from O.compose.template_selector import select_template
    from O.gate.output_gates import select_active_gates
    tmpl   = select_template(
        lucis_verdict     = result["lucis_verdict"],
        dnh_hint          = result.get("dnh_hint"),
        dominant_subgate  = result.get("dominant_subgate"),
    )

    # Compose reply
    field   = result["dominant_field"]
    phase   = result["p2_result"].get("phase","Vo")
    S_comb  = result["odfs_world"].get("S_combined", 0.5)
    verdict = result["odfs_world"].get("verdict", "QUARANTINE")
    nodes_top  = result["active_nodes"][:6]
    node_words  = [n["node_id"] for n in nodes_top]   # for display/trace

    # awareness from P2
    p2_aware_raw = result["p2_result"].get("awareness")  # str or None
    p2_aware_f   = {"IAM": 0.9, "SENSING": 0.7, "IAMNOT": 0.1, None: 0.0}.get(p2_aware_raw, 0.0)

    # gap signal from primordial activations
    prim_acts  = result.get("primordial_activations", [])
    gap_signal = prim_acts[0].get("gap_signal", 0.0) if prim_acts else 0.0

    # Speaker's field vector — for Gap(Pete, Speaker) computation
    result["R_sit_raw"] = list(event.situation_signal.to_R0())

    # Compose reply using dynamic_lexicalize
    response_text = _compose_response(
        user_text        = text,
        tmpl             = tmpl,
        field            = field,
        phase            = phase,
        S_comb           = S_comb,
        node_words       = node_words,
        dnh_hint         = result.get("dnh_hint"),
        R_0              = result.get("R_0", [1/6]*6),
        p2_awareness     = p2_aware_f,
        gap_signal       = gap_signal,
        lucis_verdict_str= result["odfs_world"].get("verdict", "QUARANTINE"),
        active_nodes_raw = nodes_top,
        result           = result,      # ← P-space state + R_sit_raw
        engine           = _engine,     # ← node_store access
    )

    # Feedback to I (Pete's output)
    feedback_event = _i_engine.process(response_text, source="pete_output")
    _engine.process(feedback_event, mode="NORMAL")

    # Auto-save nodes to SQLite every 10 ticks
    if result.get("tick", 0) % 10 == 0:
        _autosave_to_db()

    # Log
    _chat_log.append({"role":"user","text":text})
    _chat_log.append({"role":"pete","text":response_text})

    # Trace
    sig = event.situation_signal
    _last_trace = {
        "tick":       result["tick"],
        "situation":  {"emotion": round(sig.emotional_intensity,3),
                       "valence": round(sig.valence,3),
                       "urgency": round(sig.urgency,3),
                       "question": round(sig.question_pressure,3)},
        "R_sit":      [round(x,3) for x in sig.to_R0()],
        "attn_mode":  result["attention_mode"],
        "proc_mode":  result["processing_mode"],
        "p2":         {"phase":phase, "awareness":result["p2_result"].get("awareness"),
                       "iam_streak":result["p2_result"].get("iam_streak",0)},
        "S_combined": round(S_comb,3),
        "verdict":    verdict,
        "field":      field,
        "phase":      phase,
        "dnh_hint":   result.get("dnh_hint"),
        "template":   tmpl["template"],
        "nodes":      node_words,
        "lucis_class": result["lucis_verdict"].get("lucis_class","lucis"),
        # Wave layer
        "gap_density":          result.get("gap_density", 0.0),
        "wave_dominant_prime":  result.get("wave_dominant_prime", "—"),
        "primordial_activations": result.get("primordial_activations", []),
    }


    return {"text": response_text, "trace": _last_trace}

def _compose_response(user_text: str, tmpl: dict, field: str, phase: str,
                       S_comb: float, node_words: list, dnh_hint: str,
                       R_0: list = None, p2_awareness: float = 0.0,
                       gap_signal: float = 0.0, lucis_verdict_str: str = "QUARANTINE",
                       active_nodes_raw: list = None, language: str = "vi",
                       result: dict = None, engine=None) -> str:
    """
    Pete's response — P-space fractal generation pipeline, no LLM.

    Priority:
      0. p_space_realizer — P-space lifecycle + gap neighbors (NEW)
      1. surface_realizer.realize() — grammar_cycle fallback (echo-checked)
      2. dynamic_lexicalize()       — template class fallback
      3. bare field+phase string
    """
    fw = R_0 if R_0 else [1/6]*6
    nodes_raw = active_nodes_raw or []

    # Helper: echo check — reject if fractal output too similar to user input
    def _is_echo(generated: str, user_input: str, threshold: float = 0.3) -> bool:
        """Return True if generated sentence is just echoing input words."""
        if not generated or not user_input:
            return False
        gen_words  = set(generated.lower().split())
        inp_words  = set(user_input.lower().split())
        if not gen_words: return False
        # Special case: 1-2 word inputs → any overlap = echo
        if len(inp_words) <= 2 and gen_words & inp_words:
            return True
        overlap = len(gen_words & inp_words) / len(gen_words)
        return overlap >= threshold

    input_words = set(user_text.lower().split())

    # Helper: echo check
    def _is_echo_v2(generated: str) -> bool:
        if not generated: return False
        gen_words = set(generated.lower().split())
        if not gen_words: return False
        if len(input_words) <= 2 and gen_words & input_words: return True
        return len(gen_words & input_words) / len(gen_words) >= 0.3

    # ── P-SPACE PRIMARY: lifecycle phases + gap neighbors ─────────────────────
    if result and engine:
        try:
            from O.compose.p_space_realizer import realize_from_p_space
            p_out = realize_from_p_space(
                result=result, engine=engine,
                input_words=input_words, language=language,
            )
            if p_out and p_out.strip() and len(p_out.strip()) > 8 and not _is_echo_v2(p_out):
                return p_out
        except Exception:
            pass

    # ── SECONDARY: fractal sentence generation (echo-checked) ────────────────
    try:
        from O.compose.surface_realizer import realize
        from O.compose.context_gate import detect_context_gate

        context_gate = detect_context_gate(fw)
        fractal_out = realize(
            template       = tmpl.get("template", "PRESENCE"),
            active_nodes   = nodes_raw,
            dominant_field = field,
            thought_phase  = phase,
            gap_style      = tmpl.get("gap_style", "mid"),
            dnh_hint       = dnh_hint,
            language       = language,
            R              = fw,
            rng            = None,
            node_store     = None,
        )
        # Accept fractal output only if:
        #  1. Non-empty and longer than a trivial word
        #  2. NOT echoing user input (no >50% overlap)
        if (fractal_out and fractal_out.strip() and len(fractal_out.strip()) > 6
                and not _is_echo(fractal_out, user_text)):
            return fractal_out
    except Exception:
        pass  # fall through to secondary

    # ── Secondary: dynamic_lexicalize (8 template classes, English phrases) ──
    try:
        from O.compose.lexicalize import dynamic_lexicalize
        verdict_map = {"ASSIMILATE": "output", "EXCRETE": "reject", "QUARANTINE": "clarify"}
        lex_verdict = verdict_map.get(lucis_verdict_str, "clarify")
        fw_max  = max(fw) or 1.0
        fw_norm = [x / fw_max for x in fw]
        result  = dynamic_lexicalize(
            field_weights  = fw_norm,
            phase          = phase,
            verdict        = lex_verdict,
            active_nodes   = node_words[:4],
            gap_signal     = gap_signal,
            awareness      = p2_awareness,
            H              = len(node_words),
            dominant_field = field,
        )
        if result and result.strip():
            return result
    except Exception:
        pass

    # ── Last resort ───────────────────────────────────────────────────────────
    confidence = "rõ ràng" if S_comb > 0.6 else "đang khám phá" if S_comb > 0.3 else "..."
    return f"[{field}|{phase}|{confidence}]"


# ── Stats + Trace ─────────────────────────────────────────────────────────────
@app.get("/stats")
async def stats():
    if _engine is None:
        return {"status":"loading"}
    base = {**_engine.stats, "chat_turns": len(_chat_log)//2}
    # Also show DB node count for transparency
    try:
        from D.db import get_db
        base["nodes_in_db"] = get_db().count_nodes()
    except Exception:
        pass
    return base

@app.get("/trace")
async def trace():
    return _last_trace

@app.get("/log")
async def log():
    return {"log": _chat_log[-50:]}

@app.get("/graph")
async def graph():
    if _engine is None: return {"nodes":[],"edges":[]}
    nodes = []
    for nid, node in list(_engine._node_store.items())[:500]:
        nodes.append({"id":nid, "H":round(node.H,2), "phase":node.phase,
                      "field": max(node.meaning, key=node.meaning.get)})
    return {"nodes": nodes, "edges": []}

@app.get("/primordial")
async def primordial():
    """Live Pete internal state for visualization."""
    if _engine is None:
        return {"status": "loading", "nodes": [], "edges": [], "field": {}, "p2": {}}
    try:
        trace      = _last_trace if isinstance(_last_trace, dict) else {}
        node_store = getattr(_engine, "_node_store", {})
        FLDS       = ["emotion","logic","reflection","visual","language","intuition"]

        # Active ids: from last trace, or cold top-H view
        active_ids = trace.get("nodes", [])
        if not active_ids:
            all_nd = sorted(node_store.items(),
                            key=lambda x: float(getattr(x[1],'H',0)), reverse=True)
            active_ids = [nid for nid,_ in all_nd[:10]]

        # Build node list
        nodes = []
        for nid in active_ids:
            nd = node_store.get(nid)
            if nd is None: continue
            try:
                m = nd.meaning if isinstance(nd.meaning, dict) else {}
                df = max(m, key=lambda k: m[k]) if m else "logic"
                nodes.append({
                    "id":      nid,
                    "phase":   getattr(nd, "phase", "Dan"),
                    "H":       round(float(getattr(nd, "H", 0)), 2),
                    "field":   df,
                    "meaning": {k: round(float(v), 3) for k,v in m.items()},
                })
            except Exception:
                continue

        # Edges: L2 neighbors in active set
        edges      = []
        seen       = set()
        active_set = {n["id"] for n in nodes}
        for nd_data in nodes:
            nid = nd_data["id"]
            nd  = node_store.get(nid)
            if nd is None: continue
            # members may be list, set, or None — always convert to list of str
            raw_members = getattr(nd, "members", None) or []
            try:
                members = list(raw_members)
            except Exception:
                members = []
            # L2 edges
            for m in members[:6]:
                try:
                    # Each member is either a plain str ID, or (id, weight) tuple
                    nbr = str(m[0]) if isinstance(m, (list, tuple)) else str(m)
                    key = (min(nid, nbr), max(nid, nbr))
                    if key not in seen and nbr in active_set:
                        seen.add(key)
                        edges.append({"from": nid, "to": nbr, "layer": 2})
                except Exception:
                    continue
            # L3 edges
            for m in members[:4]:
                try:
                    l2  = str(m[0]) if isinstance(m, (list, tuple)) else str(m)
                    nd2 = node_store.get(l2)
                    if nd2 is None: continue
                    raw2 = getattr(nd2, "members", None) or []
                    for m2 in list(raw2)[:4]:
                        l3 = str(m2[0]) if isinstance(m2, (list, tuple)) else str(m2)
                        if l3 in active_set:
                            key = (min(l2, l3), max(l2, l3))
                            if key not in seen:
                                seen.add(key)
                                edges.append({"from": l2, "to": l3, "layer": 3})
                except Exception:
                    continue


        R  = trace.get("R_sit", [1/6]*6)
        fp = {f: round(float(R[i]) if i < len(R) else 1/6, 3)
              for i,f in enumerate(FLDS)}

        return {
            "tick":         trace.get("tick", 0),
            "nodes":        nodes,
            "edges":        edges,
            "field":        fp,
            "dominant_field": trace.get("field", "logic"),
            "p2":           trace.get("p2", {}),
            "verdict":      trace.get("verdict", "—"),
            "lucis_class":  trace.get("lucis_class", ""),
            "S_combined":   trace.get("S_combined", 0),
            "primordial_activations": trace.get("primordial_activations", []),
            "dnh_hint":     trace.get("dnh_hint"),
            "attn_mode":    trace.get("attn_mode", "NORMAL"),
            # Wave layer
            "gap_density":  trace.get("gap_density", 0.0),
            "wave_prime":   trace.get("wave_dominant_prime", "—"),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e),
                "nodes": [], "edges": [], "field": {}, "p2": {}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("I.server:app", host="0.0.0.0", port=8000, reload=False)


