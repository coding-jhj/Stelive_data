# -*- coding: utf-8 -*-
"""대시보드 임베드 데이터 빌더.

data/ 의 원시 수집물(streams/followers/subscribers)을 읽어 dashboard/index.html 안의
임베드 상수( SD · ST · MO · CAT · FOL_DATES · FOL_DATA )를 최신 값으로 재생성한다.
수집 워크플로가 매일 data/ 만 갱신하던 구조라 대시보드 숫자가 동결됐던 문제를 해소한다.

- 줄바꿈(CRLF) 보존: 파일을 '\r\n' 로 split/join.
- MB·GROWTH_DATA(수동 큐레이션 추정치)는 건드리지 않는다.
- 모든 시점 지표(s30·fg 등)는 trailing window 정의. 일일 수집이 쌓이면 정확해진다.
"""
import csv, io, json, os, sys, re
from datetime import date, timedelta
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
HTML = os.path.join(ROOT, "dashboard", "index.html")

MEMBER_ORDER = [
    "ayatsuno_yuni", "sakihane_huya", "shirayuki_hina", "neneko_mashiro",
    "akane_lize", "arahashi_tabi", "tenko_shibuki", "aokumo_rin",
    "hanako_nana", "yuzuha_riko",
]

def rd(name):
    with io.open(os.path.join(DATA, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def pdate(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None

def bucket(cat):
    c = (cat or "").strip()
    if c == "talk":      return "talk"
    if c == "음악/노래":  return "music"
    if c == "":          return "etc"
    return "game"

def build(asof):
    streams = rd("streams.csv")
    followers = rd("followers.csv")
    subs = rd("subscribers.csv")
    w30 = asof - timedelta(days=30)
    w60 = asof - timedelta(days=60)

    rows = [s for s in streams if pdate(s["date"]) and pdate(s["date"]) <= asof]
    rows.sort(key=lambda s: (s["date"], int(s["video_no"])), reverse=True)

    # ── SD: [video_no, title, date, duration, bucket, views, member_id, is_collab] ──
    SD = [[
        int(s["video_no"]), s["title"], s["date"][:10],
        round(float(s["duration_min"] or 0)), bucket(s["category"]),
        int(s["view_count"] or 0), s["member_id"],
        1 if s["is_collab"] == "True" else 0,
    ] for s in rows]

    # ── 팔로워/구독자 시계열 (멤버별, 날짜오름차순) ──
    folser, subser = {}, {}
    for m in MEMBER_ORDER:
        fh = sorted({pdate(r["date"]): int(r["follower_count"])
                     for r in followers
                     if r["member_id"] == m and pdate(r["date"]) and pdate(r["date"]) <= asof}.items())
        folser[m] = fh
        sh = sorted({pdate(r["date"]): int(r["subscriber_count"])
                     for r in subs
                     if r["member_id"] == m and pdate(r["date"]) and pdate(r["date"]) <= asof}.items())
        subser[m] = sh

    def fol_growth(fh):
        """asof 기준 직전 30일 팔로워 증가. 30일 전 데이터 없으면 0(이력 부족 — 일일수집 누적되면 정상화)."""
        if not fh:
            return 0, 0
        cur = fh[-1][1]
        # 30일 전 근방(-10일~0) 최신값
        base = [v for d, v in fh if w30 - timedelta(days=10) <= d <= w30]
        return (cur, cur - base[-1]) if base else (cur, 0)

    # ── ST: 멤버별 통계 ──
    ST = {}
    for m in MEMBER_ORDER:
        h = [s for s in rows if s["member_id"] == m]
        t = len(h)
        s30 = sum(1 for s in h if pdate(s["date"]) > w30)
        sp = sum(1 for s in h if w60 < pdate(s["date"]) <= w30)
        c30 = sum(1 for s in h if pdate(s["date"]) > w30 and s["is_collab"] == "True")
        cr = round(c30 / s30 * 100, 1) if s30 else 0
        fol, fg = fol_growth(folser[m])
        eff = round(fg / s30) if s30 and fg > 0 else 0
        sub = subser[m][-1][1] if subser[m] else 0
        ST[m] = {"t": t, "s30": s30, "sp": sp, "fol": fol, "fg": fg,
                 "eff": eff, "sub": sub, "c30": c30, "cr": cr}

    # ── MO: 최근 13개월 방송수/콜라보수 ──
    def ym(d): return (d.year, d.month)
    months = []
    y, mo = asof.year, asof.month
    for _ in range(13):
        months.append((y, mo))
        mo -= 1
        if mo == 0:
            mo = 12; y -= 1
    months.reverse()
    lb = [f"{y % 100:02d}-{mo:02d}" for y, mo in months]
    tot = [sum(1 for s in rows if ym(pdate(s["date"])) == (y, mo)) for y, mo in months]
    col = [sum(1 for s in rows if ym(pdate(s["date"])) == (y, mo) and s["is_collab"] == "True")
           for y, mo in months]
    MO = {"lb": lb, "tot": tot, "col": col}

    # ── CAT: 최근 30일 카테고리별 ──
    recent = [s for s in rows if pdate(s["date"]) > w30]
    CAT = {}
    for b in ("talk", "game", "music"):
        br = [s for s in recent if bucket(s["category"]) == b]
        cnt = len(br)
        avg = round(sum(int(s["view_count"] or 0) for s in br) / cnt) if cnt else 0
        cp = round(sum(1 for s in br if s["is_collab"] == "True") / cnt * 100, 1) if cnt else 0
        CAT[b] = {"cnt": cnt, "avg": avg, "cp": cp}

    # ── FOL_DATES / FOL_DATA: 일일수집기(2026-04-15~) 연속 구간 ──
    start = date(2026, 4, 15)
    all_dates = sorted({d for m in MEMBER_ORDER for d, _ in folser[m] if d >= start and d <= asof})
    FOL_DATES = [d.isoformat() for d in all_dates]
    FOL_DATA = {}
    for m in MEMBER_ORDER:
        dmap = dict(folser[m])
        last = None
        seq = []
        for d in all_dates:
            if d in dmap:
                last = dmap[d]
            seq.append(last if last is not None else 0)
        FOL_DATA[m] = seq

    return {"SD": SD, "ST": ST, "MO": MO, "CAT": CAT,
            "FOL_DATES": FOL_DATES, "FOL_DATA": FOL_DATA}

def js(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

def inject(blocks):
    raw = io.open(HTML, encoding="utf-8", newline="").read()
    cr, lf = raw.count("\r"), raw.count("\n")
    nl = "\r\n" if "\r\n" in raw else "\n"  # CI(git autocrlf)=LF, 로컬=CRLF 양쪽 대응
    lines = raw.split(nl)

    def replace(prefix, newline):
        start = next(i for i, l in enumerate(lines) if l.lstrip().startswith(prefix))
        if lines[start].rstrip().endswith(";"):
            end = start
        else:
            end = next(j for j in range(start, len(lines)) if lines[j].rstrip() == "};")
        lines[start:end + 1] = [newline]

    replace("const SD=[",        "const SD=" + js(blocks["SD"]) + ";")
    replace("const ST={",        "const ST=" + js(blocks["ST"]) + ";")
    replace("const MO={",        "const MO=" + js(blocks["MO"]) + ";")
    replace("const CAT={",       "const CAT=" + js(blocks["CAT"]) + ";")
    replace("const FOL_DATES=[", "const FOL_DATES=" + js(blocks["FOL_DATES"]) + ";")
    replace("const FOL_DATA={",  "const FOL_DATA=" + js(blocks["FOL_DATA"]) + ";")

    out = nl.join(lines)
    io.open(HTML, "w", encoding="utf-8", newline="").write(out)
    ncr, nlf = out.count("\r"), out.count("\n")
    print(f"CRLF: CR {cr}->{ncr} / LF {lf}->{nlf} {'OK' if ncr == nlf else 'MISMATCH'}")

def main():
    streams = rd("streams.csv")
    asof = max(d for d in (pdate(s["date"]) for s in streams) if d)
    if "--asof" in sys.argv:
        asof = date.fromisoformat(sys.argv[sys.argv.index("--asof") + 1])
    b = build(asof)
    print(f"asof={asof}  SD={len(b['SD'])}행  FOL_DATES={len(b['FOL_DATES'])}일  "
          f"멤버={len(b['ST'])}  최근30일방송={sum(b['MO']['tot'][-1:])}")
    if "--dry" in sys.argv:
        print("ST sample:", b["ST"]["ayatsuno_yuni"])
        print("CAT:", b["CAT"])
        print("MO.tot:", b["MO"]["tot"])
        return
    inject(b)
    print("dashboard/index.html 임베드 갱신 완료")

if __name__ == "__main__":
    main()
