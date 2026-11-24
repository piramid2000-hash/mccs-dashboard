/**
 * 도면 수령 확인 기록기 (구글 앱스 스크립트 · 무료, 구글이 운영)
 *
 * 받은 사람이 카톡 링크에서 [수령 확인했습니다]를 누르면 이 웹 앱이 열리고,
 * 링크의 서명을 확인한 뒤 이 스프레드시트의 '수령확인' 시트에 한 줄을 남긴다.
 * 매일 자동 업데이트가 이 시트를 읽어 대표 앱 '도면' 탭과 아침 메일에 반영한다.
 *
 * 설치 (한 번, 10분): docs/도면배포_설정가이드.md 참고
 *  1) 드라이브 '원이엔지_업무현황' 폴더에 구글 스프레드시트 '수령확인' 만들기
 *  2) 확장 프로그램 → Apps Script → 이 코드를 붙여넣고 저장
 *  3) 프로젝트 설정(톱니) → 스크립트 속성 → DOC_SECRET = GitHub Secrets 의 DOC_SECRET 과 같은 값
 *  4) 배포 → 새 배포 → 유형 '웹 앱' → 실행: 나 / 액세스: 모든 사용자 → 배포 → 웹 앱 URL 복사
 *  5) GitHub Secrets 에 ACK_URL = 그 URL
 */
const SHEET = '수령확인';

function doGet(e) {
  const p = (e && e.parameter) || {};
  const secret = PropertiesService.getScriptProperties().getProperty('DOC_SECRET');
  if (!secret) return page_('설정이 끝나지 않았습니다', '담당자에게 알려 주세요. (DOC_SECRET 없음)', false);
  if (!p.doc || !p.rev || !p.r || !p.s) return page_('링크가 올바르지 않습니다', '보낸 분께 링크를 다시 요청해 주세요.', false);

  // 파이썬 core/doclinks.py ack_sig 와 같은 계산: HMAC-SHA256("ack|도면번호|Rev|수신자") 앞 24자
  const msg = ['ack', p.doc, p.rev, p.r].join('|');
  const bytes = Utilities.computeHmacSha256Signature(msg, secret, Utilities.Charset.UTF_8);
  const sig = bytes.map(function (b) { return ('0' + (b & 0xff).toString(16)).slice(-2); }).join('').slice(0, 24);
  if (sig !== String(p.s)) return page_('확인할 수 없는 링크입니다', '링크가 잘렸거나 바뀌었습니다. 보낸 분께 다시 요청해 주세요.', false);

  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName(SHEET) || ss.insertSheet(SHEET);
    if (sh.getLastRow() === 0) sh.appendRow(['시각', '도면번호', 'Rev', '수신자', '확인']);
    sh.appendRow([new Date(), p.doc, p.rev, p.r, '확인']);
  } finally {
    lock.releaseLock();
  }
  return page_('수령 확인되었습니다', '도면 ' + p.doc + ' · Rev ' + p.rev + '. 감사합니다. 이 창을 닫으셔도 됩니다.', true);
}

function page_(title, msg, ok) {
  const color = ok ? '#0a7f2e' : '#c42b2b';
  const html = '<meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<div style="font-family:-apple-system,Apple SD Gothic Neo,Malgun Gothic,sans-serif;max-width:520px;margin:48px auto;padding:0 20px">' +
    '<div style="border:2px solid ' + color + ';border-radius:14px;padding:20px">' +
    '<div style="font-size:22px;font-weight:700;color:' + color + '">' + (ok ? '✓ ' : '⚠️ ') + esc_(title) + '</div>' +
    '<div style="margin-top:8px;font-size:16px;color:#333">' + esc_(msg) + '</div></div></div>';
  return HtmlService.createHtmlOutput(html).setTitle(title);
}

function esc_(s) {
  return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; });
}
