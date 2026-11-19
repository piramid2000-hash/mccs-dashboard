"""구글 드라이브 연결 점검: 키 파일과 폴더 ID로 실제로 엑셀이 보이는지 확인한다.

사용:
  python exec_dashboard/scripts/test_drive.py <서비스계정키.json> <폴더ID 또는 폴더 URL>
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.parser import parse_workbook                          # noqa: E402
from core.sources import GoogleDriveSource, load_service_account  # noqa: E402


def main():
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    key, folder = sys.argv[1], sys.argv[2]
    m = re.search(r"folders/([\w-]+)", folder)
    folder_id = m.group(1) if m else folder
    info = load_service_account(key)
    print(f"① 서비스계정: {info.get('client_email')}")
    print(f"② 폴더 ID   : {folder_id}")
    try:
        files = GoogleDriveSource(folder_id, info).list_files()
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        print(f"✗ 드라이브 접근 실패: {msg[:300]}")
        if "has not been used" in msg or "disabled" in msg:
            print("  → Google Cloud 콘솔에서 'Google Drive API'를 '사용'으로 켜세요 (켠 뒤 1~2분 대기).")
        elif "404" in msg or "notFound" in msg:
            print("  → 폴더 ID가 틀렸거나, 폴더를 위 서비스계정 이메일에 '뷰어'로 공유하지 않았습니다.")
        sys.exit(2)
    if not files:
        print("✗ 폴더는 열렸지만 엑셀이 없습니다. 폴더를 서비스계정 이메일에 공유했는지, 엑셀을 올렸는지 확인하세요.")
        sys.exit(3)
    print(f"✓ 엑셀 {len(files)}개 발견")
    for f in files[:10]:
        print(f"   - {f.name}  ({f.modified:%Y-%m-%d %H:%M})")
    wb = parse_workbook(files[0].load(), files[0].name)
    print(f"✓ 최신 파일 읽기 성공: 공사 {len(wb.projects)}건, 금액 시트 {'있음' if wb.has_finance else '없음'}")
    print("\n이제 secrets.toml 에 GDRIVE_FOLDER_ID 와 GDRIVE_SERVICE_ACCOUNT 를 넣으면 됩니다.")


if __name__ == "__main__":
    main()
