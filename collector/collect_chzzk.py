"""
치지직(CHZZK) 수집 스크립트
- 팔로워 수 스냅샷 (날짜별 누적)
- VOD 방송 기록 (v1 API)
- 콜라보 감지 (제목 기반)
"""

import json, csv, time
from datetime import datetime, timezone
from pathlib import Path
import requests

try:
    from collector.config import MEMBERS
except ImportError:
    from config import MEMBERS

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

CHZZK_API = "https://api.chzzk.naver.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

MEMBER_NAME_MAP = {m["name"]: m["id"] for m in MEMBERS}


def fetch_channel_info(chzzk_id: str) -> dict:
    url = f"{CHZZK_API}/service/v1/channels/{chzzk_id}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json().get("content", {})
        return {
            "follower_count": data.get("followerCount", 0),
            "open_live":      data.get("openLive", False),
            "channel_name":   data.get("channelName", ""),
        }
    except Exception as e:
        print(f"  ⚠️  채널 정보 오류: {e}")
        return {}


def fetch_vod_list(chzzk_id: str) -> list:
    """치지직 VOD 목록 - 페이지 기반 전체 수집"""
    vods, size = [], 30

    # 첫 요청으로 totalPages 확인
    url = (
        f"{CHZZK_API}/service/v1/channels/{chzzk_id}/videos"
        f"?sortType=LATEST&pagingType=PAGE&page=0&size={size}"
    )
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        content = res.json().get("content", {})
        total_pages = content.get("totalPages", 1)
        data = content.get("data", [])
    except Exception as e:
        print(f"  ⚠️  VOD 목록 오류: {e}")
        return []

    for item in data:
        vods.append(_parse_vod(item))

    for page in range(1, total_pages):
        url = (
            f"{CHZZK_API}/service/v1/channels/{chzzk_id}/videos"
            f"?sortType=LATEST&pagingType=PAGE&page={page}&size={size}"
        )
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            res.raise_for_status()
            data = res.json().get("content", {}).get("data", [])
        except Exception as e:
            print(f"  ⚠️  VOD 목록 오류 (page {page}): {e}")
            break

        if not data:
            break

        for item in data:
            vods.append(_parse_vod(item))

        time.sleep(0.3)

    return vods


def _parse_vod(item: dict) -> dict:
    dt = item.get("publishDate", "")
    return {
        "video_no":     item.get("videoNo", ""),
        "title":        item.get("videoTitle", ""),
        "date":         dt[:10] if dt else "",
        "duration_min": round(item.get("duration", 0) / 60, 1),
        "category":     item.get("videoCategoryValue", ""),
        "view_count":   item.get("readCount", 0),
    }


def detect_collabs(title: str, streamer_id: str) -> list:
    found = []
    for name, mid in MEMBER_NAME_MAP.items():
        short = name.split(" ")[-1]
        if short in title and mid != streamer_id:
            found.append(mid)
    return found


def main():
    all_streams, all_collabs, follower_log = [], [], []

    for member in MEMBERS:
        name = member["name"]
        chzzk_id = member.get("chzzk_id", "").strip().strip("/")

        if not chzzk_id:
            print(f"\n⏭️  {name}: chzzk_id 없음")
            continue

        print(f"\n📥 {name} 치지직 수집 중...")

        info = fetch_channel_info(chzzk_id)
        if info:
            follower_log.append({
                "date":           TODAY,
                "member_id":      member["id"],
                "member_name":    name,
                "follower_count": info["follower_count"],
                "is_live":        info["open_live"],
            })
            print(f"  팔로워: {info['follower_count']:,}명")

        vods = fetch_vod_list(chzzk_id)
        collab_count = 0
        for v in vods:
            v["member_id"]   = member["id"]
            v["member_name"] = name
            v["generation"]  = member["generation"]
            v["unit"]        = member["unit"]

            collab_ids = detect_collabs(v["title"], member["id"])
            v["collab_members"] = ",".join(collab_ids)
            v["is_collab"]      = bool(collab_ids)

            for pid in collab_ids:
                all_collabs.append({
                    "date":         v["date"],
                    "member_a":     member["id"],
                    "member_b":     pid,
                    "stream_title": v["title"],
                    "video_no":     v["video_no"],
                })
            if collab_ids:
                collab_count += 1

        all_streams.extend(vods)
        print(f"  VOD: {len(vods)}개 / 콜라보: {collab_count}건")
        time.sleep(0.5)

    follower_path = DATA_DIR / "followers.csv"
    write_header = not follower_path.exists()
    with open(follower_path, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["date","member_id","member_name","follower_count","is_live"])
        if write_header: w.writeheader()
        w.writerows(follower_log)
    print(f"\n✅ 팔로워 로그: {follower_path}")

    with open(DATA_DIR / "streams.json", "w", encoding="utf-8") as f:
        json.dump(all_streams, f, ensure_ascii=False, indent=2)
    if all_streams:
        with open(DATA_DIR / "streams.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=all_streams[0].keys())
            w.writeheader(); w.writerows(all_streams)
    print(f"✅ 방송 기록: {len(all_streams)}개")

    with open(DATA_DIR / "collabs.json", "w", encoding="utf-8") as f:
        json.dump(all_collabs, f, ensure_ascii=False, indent=2)
    if all_collabs:
        with open(DATA_DIR / "collabs.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=all_collabs[0].keys())
            w.writeheader(); w.writerows(all_collabs)
    print(f"✅ 콜라보 기록: {len(all_collabs)}건")

    print("\n🎉 치지직 수집 완료!")

if __name__ == "__main__":
    main()