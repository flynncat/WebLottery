# WebLottery · 直播抽奖监控

监控企业直播页（qlive）底部「抽奖」区域。倒计时出现时提醒你，**抽奖按钮仍需自己点**。

仓库里有两个互不影响的版本：

| 版本 | 目录 | 谁打开直播页 | 更适合 |
| --- | --- | --- | --- |
| 桌面版 | 仓库根目录 | Playwright 启动 Chrome | 独立窗口、开始 / 停止监控 |
| Chrome 扩展 | `chrome-extension/` | 你自己用普通 Chrome 打开 | 不想被识别成自动化浏览器 |

两者都不会自动点击抽奖，只负责检测和提醒。

## 选哪个

- 想少一点自动化特征：用 **Chrome 扩展**，在已登录的直播页里监控
- 想要桌面窗口和独立 Chrome 配置：用 **桌面版**

---

## Chrome 扩展（推荐日常使用）

源码在 [`chrome-extension/`](chrome-extension/)，详细说明见 [chrome-extension/README.md](chrome-extension/README.md)。

1. Chrome 打开 `chrome://extensions/`
2. 打开 **开发者模式**
3. 点 **加载已解压的扩展程序**，选中 `chrome-extension` 文件夹
4. 用普通 Chrome 打开并登录直播页
5. 保持扩展开启；倒计时出现后点系统通知回到该标签页，再手动点抽奖

扩展只匹配 `qlive.woa.com`，登录态就是你当前 Chrome 的登录态。

---

## 桌面版

用 Playwright 打开直播页。当 `.count-time` 从「查看结果」变成倒计时（`status="1"` 或 `00:10` 这类时间）时，屏幕右下角弹出提醒。点击「前往直播」会把浏览器拉到前台。

### 环境要求

- Windows
- Python 3.10+
- 本机已安装 Chrome（推荐；没有则自动改用 Playwright 自带 Chromium）

### 安装

```bat
git clone git@github.com:flynncat/WebLottery.git
cd WebLottery
pip install -r requirements.txt
python -m playwright install chromium
```

### 启动

双击 `启动.bat`，或在项目目录执行：

```bat
python app.py
```

### 使用

1. 粘贴直播地址，例如 `https://qlive.woa.com/user/live?liveId=...`
2. **首次务必勾选「显示浏览器窗口」**，在弹出的 Chrome 里完成企业微信 / SSO 登录
3. 点「开始监控」。程序会持续查看页面上的 `.count-box` / `.count-time`
4. 倒计时出现后，右下角弹窗 + 提示音。点「前往直播」把页面置于前台，再手动点抽奖
5. 需要结束时点「停止监控」

直播地址和「是否显示浏览器」会写入本地 `config.json`，下次打开会自动带上。该文件和登录目录都不会提交到 Git。

---

## 检测依据

两个版本使用同一套页面特征：

| 状态 | 页面特征 |
| --- | --- |
| 未开始 / 已结束 | `.count-info.is-result`，`.count-time` 文案为「查看结果」 |
| 抽奖倒计时 | `.count-time` 内出现 `<span status="1">`，或可见时间为 `00:10` 这类格式 |

## 项目结构

```
WebLottery/
├── app.py                 # 桌面版主界面
├── monitor.py             # 桌面版 Playwright 监控
├── notifier.py            # 桌面版右下角提醒
├── 启动.bat               # 桌面版启动脚本
├── requirements.txt
├── chrome-extension/      # Chrome 扩展（独立，不影响桌面版）
├── config.json            # 本机配置（不入库）
└── .chrome-profile/       # 桌面版 Chrome 登录态（不入库）
```

## 依赖

桌面版见 `requirements.txt`：

```
playwright>=1.40.0
```

Chrome 扩展无 Python 依赖，用 Chrome 开发者模式加载即可。

## 注意

- 仅用于本人已登录、有权访问的直播页提醒，不会代替你点击抽奖
- `.chrome-profile/` 含登录 Cookie，请勿分享或提交到仓库
- 直播页 DOM 若改版，倒计时检测可能失效；桌面版改 `monitor.py`，扩展改 `chrome-extension/content.js`
