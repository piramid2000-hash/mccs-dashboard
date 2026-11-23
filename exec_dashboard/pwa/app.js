/* 원이엔지 경영 앱
 * - data.enc: 매일 자동으로 만들어지는 암호화된 보고서 (AES-256-GCM, 비밀번호 → PBKDF2-SHA256)
 * - 비밀번호는 서버로 보내지 않는다. 휴대폰 안에서만 풀고, '기억하기'를 켜면
 *   꺼낼 수 없는(non-extractable) 키를 이 기기의 IndexedDB 에만 보관한다.
 */
(function () {
  "use strict";
  var KDF_SALT = "wonieng-ceo-app-v1"; // 공개 솔트 (빌드 스크립트와 같아야 함)
  var TABS = ["home", "proj", "out", "money", "check"];
  var $ = function (id) { return document.getElementById(id); };
  var key = null, payload = null, lastGenerated = null, ranReportJs = false;
  var source = "data.enc"; // 대표용 실제 자료. 심사·시연용 비밀번호면 demo.enc

  // ---------- 키 보관 (IndexedDB) ----------
  function idb() {
    return new Promise(function (res, rej) {
      var r = indexedDB.open("wonieng", 1);
      r.onupgradeneeded = function () { r.result.createObjectStore("k"); };
      r.onsuccess = function () { res(r.result); };
      r.onerror = function () { rej(r.error); };
    });
  }
  function idbDo(mode, fn) {
    return idb().then(function (db) {
      return new Promise(function (res, rej) {
        var tx = db.transaction("k", mode), st = tx.objectStore("k"), out = fn(st);
        tx.oncomplete = function () { res(out && out.result); };
        tx.onerror = function () { rej(tx.error); };
      });
    });
  }
  var saveKey = function (k, src) { return idbDo("readwrite", function (s) { s.put(src, "src"); return s.put(k, "key"); }).catch(function () {}); };
  var loadKey = function () { return idbDo("readonly", function (s) { return s.get("key"); }).catch(function () { return null; }); };
  var loadSrc = function () { return idbDo("readonly", function (s) { return s.get("src"); }).catch(function () { return null; }); };
  var dropKey = function () { return idbDo("readwrite", function (s) { s.delete("src"); return s.delete("key"); }).catch(function () {}); };

  // ---------- 암호 ----------
  function b64(s) { var b = atob(s), u = new Uint8Array(b.length); for (var i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u; }
  function deriveKey(password, iterations) {
    var enc = new TextEncoder();
    return crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveKey"]).then(function (base) {
      return crypto.subtle.deriveKey({ name: "PBKDF2", salt: enc.encode(KDF_SALT), iterations: iterations, hash: "SHA-256" },
        base, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
    });
  }
  function decrypt(k, box) {
    return crypto.subtle.decrypt({ name: "AES-GCM", iv: b64(box.iv) }, k, b64(box.ct)).then(function (buf) {
      return JSON.parse(new TextDecoder().decode(buf));
    });
  }

  // ---------- 데이터 ----------
  function fetchBox(fresh, src) {
    return fetch((src || source) + (fresh ? "?t=" + Date.now() : ""), { cache: fresh ? "no-store" : "default" })
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); });
  }

  function fmtTime(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return iso;
    var p = function (n) { return (n < 10 ? "0" : "") + n; };
    return (d.getMonth() + 1) + "." + p(d.getDate()) + " " + p(d.getHours()) + ":" + p(d.getMinutes());
  }

  function render(p) {
    payload = p;
    $("reportCss").textContent = p.css.replace(/(^|[\n}])\s*body\s*\{/g, "$1#reportRoot{");
    $("content").innerHTML = "<div id='reportRoot'>" + p.body + "</div>";
    ranReportJs = false;
    $("appTitle").textContent = p.company ? p.company.replace(/^㈜/, "") + " 경영" : "원이엔지 경영";
    $("stamp").textContent = "업데이트 " + fmtTime(p.generated) + (p.finance_as_of ? " · 금액 " + p.finance_as_of.slice(5).replace("-", ".") + " 기준" : "");
    var n = p.check_count || 0;
    $("checkDot").hidden = !n; $("checkDot").textContent = n > 99 ? "99+" : n;
    show(currentTab());
  }

  function runReportJs() {
    if (ranReportJs || !payload || !payload.js) return;
    ranReportJs = true;
    try { new Function(payload.js)(); } catch (e) { /* 차트 보조 기능이 실패해도 화면은 유지 */ }
  }

  function currentTab() {
    var h = (location.hash || "").slice(1);
    return TABS.indexOf(h) >= 0 ? h : "home";
  }
  function show(tab) {
    var c = $("content");
    c.className = "t-" + tab;
    document.querySelectorAll(".tab").forEach(function (b) {
      if (b.getAttribute("data-go") === tab) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
    });
    if (tab === "proj") requestAnimationFrame(runReportJs); // 일정표가 보일 때 '오늘' 위치로 이동
    window.scrollTo(0, 0);
  }

  function banner(html, action, label) {
    var b = $("banner");
    if (!html) { b.hidden = true; return; }
    b.innerHTML = "<span>" + html + "</span>";
    if (action) { var x = document.createElement("button"); x.textContent = label; x.onclick = action; b.appendChild(x); }
    b.hidden = false;
  }

  function load(fresh) {
    var btn = $("refreshBtn");
    btn.classList.add("spin");
    return fetchBox(fresh).then(function (box) {
      if (box.generated === lastGenerated && payload) return;
      return decrypt(key, box).then(function (p) {
        lastGenerated = box.generated;
        render(p);
        banner(navigator.onLine ? "" : "오프라인 – 마지막으로 받은 자료를 보여 드립니다.");
      });
    }).catch(function (e) {
      if (e && e.name === "OperationError") { lockOut("비밀번호가 바뀌었습니다. 새 비밀번호를 입력해 주세요."); return; }
      if (!payload) $("content").innerHTML = "<div id='empty'>자료를 불러오지 못했습니다.<br>인터넷 연결을 확인한 뒤 새로고침을 눌러 주세요.</div>";
      banner("새 자료를 받지 못했습니다. 인터넷 연결을 확인해 주세요.");
    }).then(function () { btn.classList.remove("spin"); installHint(); });
  }

  // ---------- 잠금 ----------
  function lockOut(msg) {
    key = null; payload = null; lastGenerated = null;
    dropKey();
    $("app").hidden = true; $("lock").hidden = false;
    $("lockErr").textContent = msg || "";
    $("pw").value = "";
    setTimeout(function () { $("pw").focus(); }, 50);
  }

  function unlock(ev) {
    ev.preventDefault();
    var pw = $("pw").value, btn = $("unlockBtn");
    if (!pw) return;
    btn.disabled = true; btn.textContent = "확인 중…"; $("lockErr").textContent = "";
    var tryOpen = function (src) {
      return fetchBox(true, src).catch(function () { return fetchBox(false, src); }).then(function (box) {
        return deriveKey(pw, box.iter).then(function (k) {
          return decrypt(k, box).then(function (p) {
            key = k; source = src; lastGenerated = box.generated;
            if ($("remember").checked) saveKey(k, src);
            $("lock").hidden = true; $("app").hidden = false;
            render(p); installHint();
          });
        });
      });
    };
    tryOpen("data.enc").catch(function (e) {
      if (e && e.name === "OperationError") {  // 실제 자료 비밀번호가 아니면 예시 자료로 한 번 더
        return tryOpen("demo.enc").catch(function (e2) { throw (e2 && e2.name === "OperationError") ? e2 : e; });
      }
      throw e;
    }).catch(function (e) {
      $("lockErr").textContent = e && e.name === "OperationError" ? "비밀번호가 맞지 않습니다." : "자료를 받지 못했습니다. 인터넷 연결을 확인해 주세요.";
    }).then(function () { btn.disabled = false; btn.textContent = "열기"; });
  }

  // ---------- 설치 안내 ----------
  var deferredPrompt = null;
  window.addEventListener("beforeinstallprompt", function (e) { e.preventDefault(); deferredPrompt = e; installHint(); });
  function standalone() { return window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true; }
  function installHint() {
    if (standalone() || $("app").hidden || !$("banner").hidden) return;
    var dismissed = false;
    try { dismissed = localStorage.getItem("installHintClosed") === "1"; } catch (e) {}
    if (dismissed) return;
    var close = function () { try { localStorage.setItem("installHintClosed", "1"); } catch (e) {} banner(""); };
    if (deferredPrompt) {
      banner("홈 화면에 앱으로 설치할 수 있습니다.", function () {
        deferredPrompt.prompt(); deferredPrompt.userChoice.then(close); deferredPrompt = null;
      }, "설치");
    } else if (/iphone|ipad|ipod/i.test(navigator.userAgent)) {
      banner("앱으로 쓰려면 사파리 아래쪽 <b>공유 □↑</b> → <b>홈 화면에 추가</b>", close, "닫기");
    }
  }

  // ---------- 시작 ----------
  document.querySelectorAll(".tab").forEach(function (b) {
    b.addEventListener("click", function () { var t = b.getAttribute("data-go"); if (location.hash !== "#" + t) location.hash = t; else show(t); });
  });
  window.addEventListener("hashchange", function () { show(currentTab()); });
  $("lockForm").addEventListener("submit", unlock);
  $("refreshBtn").addEventListener("click", function () { banner(""); load(true); });
  $("lockBtn").addEventListener("click", function () { lockOut(""); });
  document.addEventListener("visibilitychange", function () { if (!document.hidden && key) load(true); });
  window.addEventListener("online", function () { if (key) load(true); });

  if (!window.crypto || !crypto.subtle) {
    document.body.innerHTML = "<p style='padding:40px 24px;text-align:center'>이 브라우저에서는 열 수 없습니다.<br>사파리나 크롬 최신 버전으로 열어 주세요.</p>";
    return;
  }
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(function () {});

  Promise.all([loadKey(), loadSrc()]).then(function (r) {
    var k = r[0];
    if (!k) { lockOut(""); return; }
    key = k; source = r[1] || "data.enc"; $("lock").hidden = true; $("app").hidden = false;
    load(true);
  });
})();
