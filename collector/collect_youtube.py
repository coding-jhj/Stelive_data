"""
YouTube Data API v3 수집 스크립트
"""

import os, json, csv, time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests

try:
    from collector.config import MEMBERS
except ImportError:
    from config import MEMBERS

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
if not API_KEY:
    raise ValueError("❌ .env에 YOUTUBE_API_KEY가 없습니다!")

youtube = build("youtube", "v3", developerKey=API_KEY, static_discovery=False)
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def resolve_channel_id(handle: str) -> str:
    """handle → channel_id
    @ 포함/미포함 두 가지 모두 시도 (YouTube API의 handle 조회 버그 우회)
    """
    handle = handle.strip()
    # @ 포함 버전과 미포함 버전 둘 다 시도
    candidates = []
    if handle.startswith("@"):
        candidates = [handle, handle.lstrip("@")]
    else:
        candidates = [f"@{handle}", handle]

    for h in candidates:
        try:
            url = "https://www.googleapis.com/youtube/v3/channels"
            params = {"part": "id,snippet", "forHandle": h, "key": API_KEY}
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            items = data.get("items", [])
            if items:
                channel_name = items[0].get("snippet", {}).get("title", "")
                print(f"  → 채널 확인: {channel_name} (handle: {h})")
                return items[0]["id"]
        except Exception as e:
            print(f"  ⚠️  handle 조회 실패 ({h}): {e}")

    print(f"  ⚠️  '{handle}' 조회 실패 — config.py에 youtube_channel_id를 직접 입력해주세요")
    return ""


def fetch_channel_stats(channel_id: str) -> dict:
    try:
        url = "https://www.googleapis.com/youtube/v3/channels"
        params = {"part": "statistics", "id": channel_id, "key": API_KEY}
        res = requests.get(url, params=params, timeout=10)
        items = res.json().get("items", [])
        if not items:
            return {}
        s = items[0]["statistics"]
        return {
            "subscriber_count": int(s.get("subscriberCount", 0)),
            "video_count":      int(s.get("videoCount", 0)),
            "view_count":       int(s.get("viewCount", 0)),
        }
    except Exception as e:
        print(f"  ⚠️  채널 통계 오류: {e}")
        return {}


def fetch_all_videos(channel_id: str) -> list:
    # 업로드 플레이리스트 ID 조회
    try:
        url = "https://www.googleapis.com/youtube/v3/channels"
        params = {"part": "contentDetails", "id": channel_id, "key": API_KEY}
        res = requests.get(url, params=params, timeout=10)
        items = res.json().get("items", [])
        if not items:
            print(f"  ⚠️  채널 없음 또는 비공개 (channel_id={channel_id})")
            return []
        playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    except Exception as e:
        print(f"  ⚠️  재생목록 조회 실패: {e}")
        return []

    videos, next_page = [], None
    while True:
        try:
            params = {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": 50,
                "key": API_KEY,
            }
            if next_page:
                params["pageToken"] = next_page
            res = requests.get(
                "https://www.googleapis.com/youtube/v3/playlistItems",
                params=params, timeout=15
            )
            data = res.json()
        except Exception as e:
            print(f"  ⚠️  영상 목록 오류: {e}")
            break

        for item in data.get("items", []):
            snippet = item["snippet"]
            # 삭제된 영상(Private/Deleted) 필터링
            if snippet.get("title") in ("Deleted video", "Private video"):
                continue
            videos.append({
                "video_id":     item["contentDetails"]["videoId"],
                "title":        snippet.get("title", ""),
                "published_at": snippet.get("publishedAt", "")[:10],
            })

        next_page = data.get("nextPageToken")
        if not next_page:
            break
        time.sleep(0.1)

    # 조회수·좋아요·카테고리 보강
    enriched = []
    for i in range(0, len(videos), 50):
        batch = videos[i:i+50]
        try:
            params = {
                "part": "statistics,snippet",
                "id": ",".join(v["video_id"] for v in batch),
                "key": API_KEY,
            }
            res = requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params=params, timeout=15
            )
            stats_map = {item["id"]: item for item in res.json().get("items", [])}
        except Exception:
            stats_map = {}

        for v in batch:
            info  = stats_map.get(v["video_id"], {})
            stats = info.get("statistics", {})
            snip  = info.get("snippet", {})
            v["view_count"]  = int(stats.get("viewCount", 0))
            v["like_count"]  = int(stats.get("likeCount", 0))
            v["category_id"] = snip.get("categoryId", "")
            # is_music: 제목 키워드 기반으로 판단 (category_id 신뢰 안 함)
            title_lower = v["title"].lower()
            has_music_kw = any(k in title_lower for k in [
                # 커버곡
                "cover", "커버",
                # 오리지널/MV
                "mv", "m/v", "original", "오리지널",
                # 콘서트/라이브 공연
                "concert", "콘서트", "3d live", "1st live", "2nd live", "3rd live",
                # 노래 키워드
                "노래", "sing", "song", "歌",
                # 기타 음악 형식
                "ost", "feat", "remix", "arrange", "ver.", "version",
                "piano", "acoustic",
            ])
            v["is_music"] = has_music_kw
            enriched.append(v)
        time.sleep(0.1)

    return enriched


def main():
    all_videos, all_music, subscriber_log = [], [], []

    for member in MEMBERS:
        name = member["name"]
        print(f"\n📥 {name} YouTube 수집 중...")

        channel_id = member.get("youtube_channel_id", "").strip()
        if not channel_id:
            handle = member.get("youtube_handle", "").strip()
            if not handle:
                print(f"  ⏭️  youtube_handle과 youtube_channel_id 모두 없음, 건너뜀")
                continue
            print(f"  → handle로 채널 ID 조회: {handle}")
            channel_id = resolve_channel_id(handle)
            if not channel_id:
                print(f"  ⏭️  채널 ID 조회 실패, 건너뜀")
                continue
            member["youtube_channel_id"] = channel_id

        stats = fetch_channel_stats(channel_id)
        if stats:
            subscriber_log.append({
                "date":             TODAY,
                "member_id":        member["id"],
                "member_name":      name,
                "subscriber_count": stats.get("subscriber_count", 0),
                "video_count":      stats.get("video_count", 0),
                "total_views":      stats.get("view_count", 0),
            })
            print(f"  구독자: {stats.get('subscriber_count', 0):,}명")

        videos = fetch_all_videos(channel_id)
        for v in videos:
            v["member_id"]   = member["id"]
            v["member_name"] = name
            v["generation"]  = member["generation"]
            v["unit"]        = member["unit"]
        all_videos.extend(videos)

        music = [v for v in videos if v["is_music"]]
        all_music.extend(music)
        print(f"  영상: {len(videos)}개 / 음악: {len(music)}개")
        time.sleep(0.5)

    sub_path = DATA_DIR / "subscribers.csv"
    write_header = not sub_path.exists()
    with open(sub_path, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=[
            "date","member_id","member_name",
            "subscriber_count","video_count","total_views"
        ])
        if write_header: w.writeheader()
        w.writerows(subscriber_log)
    print(f"\n✅ 구독자 로그: {sub_path}")

    with open(DATA_DIR / "videos.json", "w", encoding="utf-8") as f:
        json.dump(all_videos, f, ensure_ascii=False, indent=2)
    if all_videos:
        with open(DATA_DIR / "videos.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=all_videos[0].keys())
            w.writeheader(); w.writerows(all_videos)
    print(f"✅ 영상 목록: {len(all_videos)}개")

    with open(DATA_DIR / "music.json", "w", encoding="utf-8") as f:
        json.dump(all_music, f, ensure_ascii=False, indent=2)
    if all_music:
        with open(DATA_DIR / "music.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=all_music[0].keys())
            w.writeheader(); w.writerows(all_music)
    print(f"✅ 음악 발매: {len(all_music)}개")

    print("\n🎉 YouTube 수집 완료!")

if __name__ == "__main__":
    main()