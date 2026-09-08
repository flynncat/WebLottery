const PHASE_LABEL = {
  waiting: "等待页面 / 登录",
  watching: "监控中 · 抽奖未开始",
  countdown: "监控中 · 抽奖倒计时",
  paused: "已暂停",
  idle: "当前不是直播页",
};

const toggle = document.getElementById("toggle");
const phaseEl = document.getElementById("phase");
const detailEl = document.getElementById("detail");
const hintEl = document.getElementById("hint");

function render(phase, detail, hint) {
  phaseEl.textContent = PHASE_LABEL[phase] || phase || "未知";
  detailEl.textContent = detail || "--";
  if (hint) {
    hintEl.textContent = hint;
  }
}

function isLiveUrl(url) {
  try {
    const host = new URL(url).hostname;
    return host === "qlive.woa.com" || host.endsWith(".qlive.woa.com");
  } catch (_err) {
    return false;
  }
}

async function refresh() {
  const stored = await chrome.storage.local.get({
    enabled: true,
    lastPhase: "",
    lastDetail: "",
  });
  toggle.checked = stored.enabled !== false;

  if (stored.enabled === false) {
    render("paused", "监控已暂停", "打开开关后，已打开的直播页会继续监控。");
    return;
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !isLiveUrl(tab.url || "")) {
    render(
      "idle",
      stored.lastDetail || "请先打开直播页",
      "请用普通 Chrome 打开 qlive 直播页并完成登录，扩展会自动开始监控。",
    );
    return;
  }

  try {
    const status = await chrome.tabs.sendMessage(tab.id, { type: "getStatus" });
    if (status && status.ok && (status.found || status.phase === "paused")) {
      render(status.phase, status.detail, "倒计时出现后会弹出系统通知，点击通知回到直播页。");
      return;
    }
  } catch (_err) {
    // 页面尚未注入 content script，回退到最近一次状态
  }

  render(
    stored.lastPhase || "waiting",
    stored.lastDetail || "正在等待页面脚本",
    "若刚打开直播页，请刷新一次后再看状态。",
  );
}

toggle.addEventListener("change", async () => {
  await chrome.storage.local.set({ enabled: toggle.checked });
  await refresh();
});

refresh();
