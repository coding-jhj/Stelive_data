# 🌟 StelLive Data Dashboard
스텔라이브 멤버 데이터를 자동 수집하고 웹 대시보드로 시각화하는 프로젝트입니다.

🌐 **[대시보드 보기 →](https://coding-jhj.github.io/Stelive_data/)**

---

## 📁 구조

```
stellive-data/
├── collect_all.py              ← 전체 수집 실행
├── build_dashboard.py          ← 수집 데이터로 대시보드 임베드 재생성 (동결 방지)
├── config.py                   ← 멤버 설정 (채널 ID 포함)
├── requirements.txt
├── .env.example
├── collector/
│   ├── collect_youtube.py      ← YouTube API 수집
│   ├── collect_chzzk.py        ← 치지직 스크래핑
│   └── collect_kiriunuki.py    ← 인기 키리누키 클립 수집
├── data/                       ← 수집 데이터 (자동 생성)
│   ├── streams.json / .csv     ← 방송 기록
│   ├── music.json / .csv       ← 음악 발매
│   ├── collabs.json / .csv     ← 콜라보 기록
│   ├── followers.csv           ← 치지직 팔로워 추이
│   ├── subscribers.csv         ← 유튜브 구독자 추이
│   ├── videos.json / .csv      ← 유튜브 영상 전체
│   └── kiriunuki.json          ← 인기 키리누키 클립 (자동 생성)
├── dashboard/
│   └── index.html              ← 웹 대시보드
└── .github/workflows/
    └── collect-and-deploy.yml  ← 매일 수집 → 임베드 재생성 → Pages 배포
```

---

## 🚀 설치 및 실행

```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. API 키 설정
copy .env.example .env
# .env 파일 열어서 YOUTUBE_API_KEY 입력

# 3. 수집 실행
python collect_all.py

# 4. 대시보드 확인
# dashboard/index.html 브라우저로 열기
```

---

## ⚙️ GitHub Actions 설정

1. `Settings → Secrets → New repository secret`
   - Name: `YOUTUBE_API_KEY`
   - Value: 발급받은 키
2. `Settings → Pages → Source: GitHub Actions`

→ 매일 오전 9시(KST) 자동 수집 → 대시보드 임베드 재생성 → Pages 배포

---

## 📊 대시보드 기능

- **홈**: 핵심 KPI · 오늘 방송 현황 · 주간 하이라이트
- **멤버**: 멤버별 상세 프로필 · 치지직/유튜브/트위터 링크
- **활동 분석**: 멤버별 성과 · 기수별 비교 · 카테고리 · 시간 흐름 · 팔로워 현황 · 인사이트
- **방송 기록**: 전체/멤버/카테고리/연도 필터 · 검색 · 정렬
- **키리누키**: 인기 팬 클립 Top 15 (조회수 순)
- **회사 소개**: 스텔라이브 소개

---

## ⚠️ 주의사항

- `.env` 파일은 절대 깃허브에 올리지 마세요 (`.gitignore` 처리됨)
- YouTube API 무료 할당량: 하루 10,000 유닛
- 치지직은 비공식 API 사용 (정책 변경 시 동작 달라질 수 있음)
