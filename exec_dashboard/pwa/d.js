/* 도면 확인 페이지 (현장 QR · 카톡 링크)
 * 주소 # 뒤: v1/<공개id>/<Rev>/<열쇠>[/<수신자>/<서명>]  — # 뒤는 서버로 가지 않는다.
 * 열쇠로 그 도면 파일 하나만 풀고, 주소에 적힌 Rev 와 최신 Rev 를 비교해 옛 판이면 경고한다.
 */
(function () {
  "use strict";
  var m = document.getElementById("m");
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function day(iso) { return iso ? iso.slice(2).replace(/-/g, ".") : "-"; }
  function b64(s) { s = s.replace(/-/g, "+").replace(/_/g, "/"); while (s.length % 4) s += "="; var b = atob(s), u = new Uint8Array(b.length); for (var i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u; }
  function fail(title, msg) {
    m.innerHTML = "<div class='brand'><img src='icons/favicon.png' alt=''><span>도면 확인</span></div>" +
      "<div class='state old'><b>" + esc(title) + "</b><span>" + esc(msg) + "</span></div>";
  }
  var parts = (location.hash || "").replace(/^#/, "").split("/");
  if (parts[0] !== "v1" || parts.length < 4) { fail("링크가 올바르지 않습니다", "보낸 분께 링크를 다시 요청해 주세요."); return; }
  var id = parts[1], printed = decodeURIComponent(parts[2]), keyStr = parts[3];
  var who = parts[4] ? decodeURIComponent(parts[4]) : "", sig = parts[5] || "";
  if (!/^[0-9a-f]{16}$/.test(id)) { fail("링크가 올바르지 않습니다", "보낸 분께 링크를 다시 요청해 주세요."); return; }
  if (!window.crypto || !crypto.subtle) { fail("이 브라우저에서는 열 수 없습니다", "크롬이나 사파리로 열어 주세요."); return; }

  var cfg = { ack: "", company: "" };
  Promise.all([
    fetch("docs/config.json", { cache: "no-store" }).then(function (r) { return r.ok ? r.json() : cfg; }).catch(function () { return cfg; }),
    fetch("docs/" + id + ".enc", { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error("nf"); return r.json(); })
  ]).then(function (res) {
    cfg = res[0]; var box = res[1];
    return crypto.subtle.importKey("raw", b64(keyStr), "AES-GCM", false, ["decrypt"]).then(function (k) {
      return crypto.subtle.decrypt({ name: "AES-GCM", iv: b64(box.iv) }, k, b64(box.ct));
    }).then(function (buf) { return JSON.parse(new TextDecoder().decode(buf)); });
  }).then(render).catch(function (e) {
    if (e && e.message === "nf") fail("도면을 찾을 수 없습니다", "삭제되었거나 아직 올라오지 않은 도면입니다. 보낸 분께 문의해 주세요.");
    else fail("도면을 열 수 없습니다", "링크가 잘렸거나 손상되었습니다. 보낸 분께 다시 요청해 주세요.");
  });

  function render(d) {
    document.title = d.no + " · 도면 확인";
    var lt = d.latest, isLatest = printed === lt.rev, known = d.revisions.some(function (r) { return r.rev === printed; });
    var state;
    if (d.withdrawn) state = "<div class='state old'><b>⛔ 폐기된 도면입니다</b><span>이 도면은 더 이상 사용하지 않습니다. 담당자에게 확인해 주세요.</span></div>";
    else if (isLatest) state = "<div class='state ok'><b>✓ 최신 판입니다</b><span>Rev " + esc(lt.rev) + " · " + day(lt.date) + " 승인</span></div>";
    else state = "<div class='state old'><b>⚠️ 옛 판입니다. 사용하지 마세요</b><span>" +
      (known ? (who ? "보내 드린 판" : "이 종이") + ": Rev " + esc(printed) + " → " : "") +
      "최신: Rev " + esc(lt.rev) + " (" + day(lt.date) + " 승인)" + (lt.note ? "<br>바뀐 내용: " + esc(lt.note) : "") + "</span></div>";
    var hist = d.revisions.slice().reverse().map(function (r) {
      return "<li class='" + (r.rev === lt.rev ? "cur" : "") + "'>Rev " + esc(r.rev) + " · " + day(r.date) + (r.note ? " · " + esc(r.note) : "") + (r.rev === lt.rev ? " (최신)" : "") + "</li>";
    }).join("");
    var btns = [];
    if (d.pdf) btns.push("<a class='btn main' id='pdf' href='#' download='" + esc(d.pdf_name) + "'>최신 도면 PDF 열기 (Rev " + esc(lt.rev) + ")</a>");
    var ackKey = "ack:" + id + ":" + printed + ":" + who;
    var done = false; try { done = localStorage.getItem(ackKey) === "1"; } catch (e) {}
    if (who && sig) {
      var name = (d.recipients && d.recipients[who]) || who;
      if (!isLatest && !d.withdrawn) btns.push("<p class='meta'>" + esc(name) + "님, 보내 드린 뒤 새 판이 나왔습니다. 위 최신 도면을 보시고 담당자가 보낸 새 링크에서 수령 확인을 눌러 주세요.</p>");
      else if (d.withdrawn) { /* 폐기 도면은 수령 확인 없음 */ }
      else if (!cfg.ack) btns.push("<p class='meta'>" + esc(name) + "님, 수령 확인 기능이 아직 설정되지 않았습니다.</p>");
      else if (done) btns.push("<span class='btn done'>✓ 수령 확인을 보냈습니다</span>");
      else btns.push("<a class='btn sub' id='ack' href='#'>" + esc(name) + "님, 수령 확인했습니다</a>");
    }
    m.innerHTML = "<div class='brand'><img src='icons/favicon.png' alt=''><span>" + esc(d.company || cfg.company || "") + " 도면 확인</span></div>" +
      state +
      "<div class='card'><h1>" + esc(d.title) + "</h1><div class='meta'>" + esc(d.no) + " · " + esc(d.project) + "</div></div>" +
      "<div class='btns'>" + btns.join("") + "</div>" +
      "<div class='card'><div class='meta'><b>개정 이력</b></div><ol class='hist'>" + hist + "</ol></div>" +
      "<p class='foot'>자료 기준 " + esc((d.generated || "").replace("T", " ")) + " · 이 페이지는 " + esc(d.company || cfg.company || "") + "의 공식 도면 확인 페이지입니다</p>";

    var pdf = document.getElementById("pdf");
    if (pdf) {
      var bin = atob(d.pdf), u = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
      pdf.href = URL.createObjectURL(new Blob([u], { type: "application/pdf" }));
      pdf.target = "_blank"; pdf.rel = "noopener";
    }
    var ack = document.getElementById("ack");
    if (ack) {
      // 앱스 스크립트로 이동 → 서명 검증 후 '수령확인' 시트에 한 줄 기록
      ack.href = cfg.ack + (cfg.ack.indexOf("?") >= 0 ? "&" : "?") +
        "doc=" + encodeURIComponent(d.no) + "&rev=" + encodeURIComponent(printed) +
        "&r=" + encodeURIComponent(who) + "&s=" + encodeURIComponent(sig);
      ack.addEventListener("click", function () { try { localStorage.setItem(ackKey, "1"); } catch (e) {} });
    }
  }
})();
