# 🌟 StelLive Data Dashboard

스텔라이브 멤버 데이터를 자동 수집하고 웹 대시보드로 시각화하는 프로젝트입니다.

🌐 **[대시보드 보기 →](https://YOUR_USERNAME.github.io/stellive-data)**

---

## 📁 구조

```
stellive-data/
├── collect_all.py              ← 전체 수집 실행
├── config.py                   ← 멤버 설정 (채널 ID 포함)
├── requirements.txt
├── .env.example
├── collector/
│   ├── collect_youtube.py      ← YouTube API 수집
│   └── collect_chzzk.py        ← 치지직 스크래핑
├── data/                       ← 수집 데이터 (자동 생성)
│   ├── streams.json / .csv     ← 방송 기록
│   ├── music.json / .csv       ← 음악 발매
│   ├── collabs.json / .csv     ← 콜라보 기록
│   ├── followers.csv           ← 치지직 팔로워 추이
│   ├── subscribers.csv         ← 유튜브 구독자 추이
│   └── videos.json / .csv      ← 유튜브 영상 전체
├── dashboard/
│   └── index.html              ← 웹 대시보드
└── .github/workflows/
    └── collect-and-deploy.yml  ← 매일 자동 수집 + Pages 배포
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

→ 매일 오전 9시 자동 수집 + 대시보드 배포

---

## 📊 대시보드 기능

- **개요**: 팔로워·구독자·방송·음악·콜라보 통계 + 차트
- **멤버별**: 기수별 필터, 개별 통계 카드
- **방송 기록**: 전체/멤버별 필터, 카테고리·조회수
- **음악**: 발매 목록, 조회수·좋아요
- **콜라보**: 멤버×멤버 히트맵, 상세 기록
- **팔로워 추이**: 날짜별 라인 차트

---

## ⚠️ 주의사항

- `.env` 파일은 절대 깃허브에 올리지 마세요 (`.gitignore` 처리됨)
- YouTube API 무료 할당량: 하루 10,000 유닛
- 치지직은 비공식 API 사용 (정책 변경 시 동작 달라질 수 있음)
