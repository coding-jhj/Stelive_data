# -*- coding: utf-8 -*-
"""인기 키리누키(팬 클립) 영상 수집 — YouTube Data API.

스텔라이브 키리누키 관련 검색어로 조회수 상위 영상을 모아 data/kiriunuki.json 에 저장한다.
대시보드 '키리누키' 탭이 이 파일을 fetch 해서 Top 15 를 보여준다.
"""
import os, json, requests
from datetime import datetime, timezone

API_KEY = os.environ["YOUTUBE_API_KEY"]
BASE = "https://www.googleapis.com/youtube/v3"
QUERIES = ["스텔라이브 키리누키", "stellive 키리누키", "스텔라이브 clip"]

def main():
    seen, videos = set(), []
    for query in QUERIES:
        r = requests.get(f"{BASE}/search", params={
            "part": "snippet", "q": query, "type": "video",
            "maxResults": 20, "order": "viewCount",
            "relevanceLanguage": "ko", "key": API_KEY,
        })
        items = r.json().get("items", [])
        ids = [i["id"]["videoId"] for i in items if i["id"]["videoId"] not in seen]
        if not ids:
            continue
        r2 = requests.get(f"{BASE}/videos", params={
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(ids), "key": API_KEY,
        })
        for v in r2.json().get("items", []):
            vid = v["id"]
            if vid in seen:
                continue
            seen.add(vid)
            stats, snip = v.get("statistics", {}), v["snippet"]
            thumbs = snip.get("thumbnails", {})
            thumb = (thumbs.get("maxres") or thumbs.get("high") or thumbs.get("medium") or {}).get("url", "")
            videos.append({
                "id": vid, "title": snip["title"],
                "channel": snip["channelTitle"], "channelId": snip["channelId"],
                "published": snip["publishedAt"][:10], "thumb": thumb,
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "url": f"https://www.youtube.com/watch?v={vid}",
            })

    videos.sort(key=lambda x: x["views"], reverse=True)
    videos = videos[:15]
    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "videos": videos,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/kiriunuki.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"✅ 키리누키 {len(videos)}개 수집")

if __name__ == "__main__":
    main()
