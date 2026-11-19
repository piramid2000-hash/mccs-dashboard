"""업로드된 엑셀 버전마다 요약(snapshot)을 저장해, 직원이 같은 파일명으로 덮어써도 변경 이력을 남긴다."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path


class HistoryStore:
    def __init__(self, folder: str | Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def save(self, snapshot: dict) -> bool:
        """새 버전이면 저장하고 True."""
        path = self.folder / f"{snapshot['file_hash']}.json"
        if path.exists():
            return False
        snapshot = dict(snapshot, saved_at=dt.datetime.now().isoformat(timespec="seconds"))
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
        return True

    def all(self) -> list[dict]:
        out = []
        for p in self.folder.glob("*.json"):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return sorted(out, key=lambda s: s.get("saved_at", ""))

    def previous_of(self, file_hash: str) -> dict | None:
        snaps = self.all()
        idx = next((i for i, s in enumerate(snaps) if s["file_hash"] == file_hash), None)
        if idx is None:
            return snaps[-1] if snaps else None
        return snaps[idx - 1] if idx > 0 else None
