"""앱 자료 암호화: 같은 비밀번호로만 풀리고, 암호문에 회사 자료가 그대로 보이지 않아야 한다.
(휴대폰 브라우저 WebCrypto 와의 호환은 Playwright 로 실제 앱을 열어 확인함)"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("build_app", ROOT / "scripts" / "build_app.py")
build_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_app)


def test_roundtrip_and_wrong_password():
    payload = {"body": "<p>200톤 10척 3호정 미수 87,300,000</p>", "generated": "2026-11-23T07:05"}
    box = build_app.encrypt(payload, "correct horse battery")
    assert "200톤" not in json.dumps(box) and "87,300,000" not in box["ct"]
    assert build_app.decrypt(box, "correct horse battery") == payload
    with pytest.raises(InvalidTag):
        build_app.decrypt(box, "wrong password")


def test_salt_matches_app_js():
    js = (ROOT / "pwa" / "app.js").read_text(encoding="utf-8")
    assert f'KDF_SALT = "{build_app.KDF_SALT.decode()}"' in js
