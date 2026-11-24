"""도면 링크·QR·수령 확인 서명.

모든 값은 비밀값 DOC_SECRET 하나에서 계산된다 (저장소·로그에 남지 않음).
- 도면 공개 id  : HMAC("id:"+도면번호) 앞 16자  → 주소에 도면번호가 드러나지 않음
- 도면 열쇠     : HMAC("key:"+도면번호) 32바이트 → 그 도면 파일 하나만 풀 수 있음 (개정돼도 같은 열쇠라 옛 QR도 계속 열림)
- 수령 확인 서명: HMAC("ack|도면번호|Rev|수신자") 앞 24자 → 구글 앱스 스크립트가 같은 비밀값으로 검증

링크 모양 (주소의 # 뒤는 서버로 전송되지 않음):
  현장 QR  : <앱 주소>d.html#v1/<공개id>/<인쇄된 Rev>/<열쇠>
  카톡 링크: <앱 주소>d.html#v1/<공개id>/<보낸 Rev>/<열쇠>/<수신자>/<서명>
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
from urllib.parse import quote


def _h(secret: str, msg: str) -> bytes:
    return hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()


def public_id(secret: str, doc_no: str) -> str:
    return _h(secret, "id:" + doc_no).hex()[:16]


def doc_key(secret: str, doc_no: str) -> bytes:
    return _h(secret, "key:" + doc_no)


def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def ack_sig(secret: str, doc_no: str, rev: str, recipient: str) -> str:
    """구글 앱스 스크립트(apps_script/수령확인.gs)와 같은 계산이어야 한다."""
    return hmac.new(secret.encode("utf-8"), f"ack|{doc_no}|{rev}|{recipient}".encode("utf-8"),
                    hashlib.sha256).hexdigest()[:24]


def link(base_url: str, secret: str, doc_no: str, rev: str, recipient: str | None = None) -> str:
    parts = ["v1", public_id(secret, doc_no), quote(str(rev), safe=""), b64url(doc_key(secret, doc_no))]
    if recipient:
        parts += [quote(recipient, safe=""), ack_sig(secret, doc_no, rev, recipient)]
    return base_url.rstrip("/") + "/d.html#" + "/".join(parts)


def qr_svg(data: str) -> str:
    """QR 코드 SVG (현장 라벨용). 오류 정정 M: 라벨이 조금 긁혀도 읽힘."""
    import qrcode
    import qrcode.image.svg
    img = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=4,
                      error_correction=qrcode.constants.ERROR_CORRECT_M)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode("utf-8")
    return svg[svg.index("<svg"):]
