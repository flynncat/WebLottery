const NOTIFY_ID = "lottery-countdown";

const PHASE_LABEL = {
  waiting: "等待页面 / 登录",
  watching: "监控中 · 抽奖未开始",
  countdown: "监控中 · 抽奖倒计时",
  paused: "已暂停",
};

let lastStartedAt = 0;
const tabPhase = {};

function setBadge(phase, detail) {
  if (phase === "countdown") {
    chrome.action.setBadgeBackgroundColor({ color: "#3dd68c" });
    chrome.action.setBadgeText({ text: "!" });
    chrome.action.setTitle({ title: `抽奖倒计时 ${detail || ""}`.trim() });
    return;
  }
  if (phase === "paused") {
    chrome.action.setBadgeBackgroundColor({ color: "#8b93a7" });
    chrome.action.setBadgeText({ text: "关" });
    chrome.action.setTitle({ title: "直播抽奖监控（已暂停）" });
    return;
  }
  chrome.action.setBadgeText({ text: "" });
  chrome.action.setTitle({ title: PHASE_LABEL[phase] || "直播抽奖监控" });
}

function rememberTab(tabId, extra) {
  if (!tabId) {
    return;
  }
  chrome.storage.local.set({ lastTabId: tabId, ...extra });
}

function showCountdownNotice(text, tabId) {
  rememberTab(tabId, { lastCountdown: text || "" });
  chrome.notifications.create(NOTIFY_ID, {
    type: "basic",
    iconUrl: "icons/icon128.png",
    title: "检测到抽奖倒计时",
    message: `${text || "进行中"}\n点击通知回到直播页，请再手动点抽奖`,
    priority: 2,
    requireInteraction: true,
  });
}

function clearNotice() {
  chrome.notifications.clear(NOTIFY_ID);
}

async function focusLiveTab(tabId) {
  let targetId = tabId;
  if (!targetId) {
    const stored = await chrome.storage.local.get({ lastTabId: 0 });
    targetId = stored.lastTabId;
  }
  if (!targetId) {
    return;
  }
  try {
    const tab = await chrome.tabs.get(targetId);
    if (tab.windowId) {
      await chrome.windows.update(tab.windowId, { focused: true });
    }
    await chrome.tabs.update(targetId, { active: true });
  } catch (_err) {
    // 标签页已关则忽略
  }
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get({ enabled: true }, (data) => {
    if (typeof data.enabled !== "boolean") {
      chrome.storage.local.set({ enabled: true });
    }
    setBadge(data.enabled === false ? "paused" : "watching", "");
  });
});

chrome.runtime.onMessage.addListener((message, sender) => {
  if (!message || !message.type) {
    return;
  }
  const tabId = sender.tab && sender.tab.id;

  if (message.type === "status") {
    const prev = tabId ? tabPhase[tabId] : "";
    if (message.phase === "waiting" && (prev === "countdown" || prev === "watching")) {
      return;
    }
    if (tabId) {
      tabPhase[tabId] = message.phase;
    }
    rememberTab(tabId, {
      lastPhase: message.phase,
      lastDetail: message.detail || "",
    });
    setBadge(message.phase, message.detail || "");
    return;
  }

  if (message.type === "lottery_started") {
    const now = Date.now();
    if (now - lastStartedAt < 2000) {
      return;
    }
    lastStartedAt = now;
    if (tabId) {
      tabPhase[tabId] = "countdown";
    }
    rememberTab(tabId, { lastPhase: "countdown", lastDetail: message.text || "" });
    setBadge("countdown", message.text || "");
    showCountdownNotice(message.text, tabId);
    return;
  }

  if (message.type === "lottery_tick") {
    rememberTab(tabId, { lastPhase: "countdown", lastDetail: message.text || "" });
    setBadge("countdown", message.text || "");
    return;
  }

  if (message.type === "lottery_ended") {
    if (tabId) {
      tabPhase[tabId] = "watching";
    }
    rememberTab(tabId, { lastPhase: "watching", lastDetail: message.text || "抽奖未开始" });
    setBadge("watching", message.text || "");
    clearNotice();
  }
});

chrome.notifications.onClicked.addListener((notificationId) => {
  if (notificationId === NOTIFY_ID) {
    focusLiveTab();
    clearNotice();
  }
});
