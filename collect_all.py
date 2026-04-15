"""전체 수집 실행 - YouTube + 치지직"""
import subprocess, sys, os

def run(script):
    print(f"\n{'='*50}\n▶ {script} 실행 중...\n{'='*50}")
    root = os.path.dirname(os.path.abspath(__file__))
    base = os.path.join(root, "collector")
    env = {**os.environ, "PYTHONPATH": root}
    r = subprocess.run([sys.executable, os.path.join(base, script)], env=env)
    if r.returncode != 0:
        print(f"⚠️  {script} 오류 발생 (계속 진행)")

if __name__ == "__main__":
    print("🌟 스텔라이브 데이터 수집 시작")
    run("collect_youtube.py")
    run("collect_chzzk.py")
    print("\n✅ 모든 수집 완료! data/ 폴더에서 결과 확인하세요.")