const COUNTDOWN_RE = /\b\d{1,2}:\d{2}(?::\d{2})?\b/;
const POLL_MS = 400;

let enabled = true;
let wasCountdown = false;
let missingTicks = 0;
let timerId = 0;
let observer = null;

function readState() {
  const box = document.querySelector(".count-box");
  if (!box) {
    return { found: false, isCountdown: false, text: "", status: null };
  }
  const timeEl = box.querySelector(".count-time");
  const statusEl = timeEl && timeEl.querySelector("[status]");
  const text = timeEl ? String(timeEl.innerText || "").replace(/\s+/g, " ").trim() : "";
  const status = statusEl ? statusEl.getAttribute("status") : null;
  const idle = !text || text === "查看结果" || text === "抽奖";
  const isCountdown = status === "1" || (COUNTDOWN_RE.test(text) && !idle);
  return { found: true, isCountdown, text, status };
}

function isTopFrame() {
  try {
    return window.top === window;
  } catch (_err) {
    return true;
  }
}

function post(type, payload) {
  try {
    chrome.runtime.sendMessage({ type, ...payload });
  } catch (_err) {
    // 扩展被重载时页面上的旧 content script 会失效，忽略即可
  }
}

function tick() {
  if (!enabled) {
    return;
  }
  const state = readState();
  const found = Boolean(state.found);
  const isCountdown = Boolean(state.isCountdown);
  const text = String(state.text || "");
  const status = state.status;

  if (!found) {
    missingTicks += 1;
    if (isTopFrame() && (missingTicks === 1 || missingTicks === 8)) {
      post("status", {
        phase: "waiting",
        detail: "未找到抽奖区域，请确认已登录且直播页已打开",
        text: "",
      });
    }
    return;
  }

  if (missingTicks) {
    post("log", { message: "已定位抽奖按钮区域 .count-box" });
  }
  missingTicks = 0;

  if (isCountdown) {
    post("status", { phase: "countdown", detail: text, text, status });
    if (!wasCountdown) {
      wasCountdown = true;
      post("lottery_started", { text, status });
    } else {
      post("lottery_tick", { text, status });
    }
    return;
  }

  post("status", {
    phase: "watching",
    detail: text || "抽奖未开始",
    text,
    status,
  });
  if (wasCountdown) {
    wasCountdown = false;
    post("lottery_ended", { text });
  }
}

function startWatching() {
  if (timerId) {
    return;
  }
  observer = new MutationObserver(tick);
  observer.observe(document.documentElement || document.body, {
    childList: true,
    subtree: true,
    characterData: true,
    attributes: true,
  });
  timerId = window.setInterval(tick, POLL_MS);
  tick();
}

function stopWatching() {
  if (observer) {
    observer.disconnect();
    observer = null;
  }
  if (timerId) {
    window.clearInterval(timerId);
    timerId = 0;
  }
  wasCountdown = false;
  missingTicks = 0;
}

function applyEnabled(next) {
  enabled = Boolean(next);
  if (enabled) {
    startWatching();
    return;
  }
  stopWatching();
  post("status", { phase: "paused", detail: "监控已暂停", text: "" });
}

chrome.storage.local.get({ enabled: true }, (data) => {
  applyEnabled(data.enabled !== false);
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && changes.enabled) {
    applyEnabled(changes.enabled.newValue !== false);
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message && message.type === "getStatus") {
    const state = enabled ? readState() : { found: false, isCountdown: false, text: "", status: null };
    if (!state.found && !isTopFrame() && enabled) {
      return false;
    }
    let phase = "paused";
    let detail = "监控已暂停";
    if (enabled) {
      if (!state.found) {
        phase = "waiting";
        detail = "未找到抽奖区域，请确认已登录且直播页已打开";
      } else if (state.isCountdown) {
        phase = "countdown";
        detail = state.text || "倒计时中";
      } else {
        phase = "watching";
        detail = state.text || "抽奖未开始";
      }
    }
    sendResponse({
      ok: true,
      enabled,
      found: Boolean(state.found),
      phase,
      detail,
      href: location.href,
    });
    return true;
  }
  return false;
});
