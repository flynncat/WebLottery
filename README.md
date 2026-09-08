# WebLottery · 直播抽奖监控

桌面小工具：用 Playwright 打开企业直播页（qlive），持续观察底部「抽奖」区域。当倒计时出现时，屏幕右下角弹出提醒并播放系统提示音。点击「前往直播」会把浏览器拉到前台，**抽奖按钮仍需你自己点**。

程序不会自动点击抽奖，只负责监控、提醒和切回直播页。

## 功能

- 桌面窗口：填写直播地址、开始 / 停止监控、查看状态与日志
- 优先使用本机 Chrome；找不到则回退到 Playwright Chromium
- 登录态保存在本地 `.chrome-profile`，下次不用重复登录
- 检测到倒计时后：右下角置顶弹窗 + 系统提示音
- 「前往直播」把带 `[抽奖监控]` 标题的浏览器窗口置于前台

## 环境要求

- Windows
- Python 3.10+
- 本机已安装 Chrome（推荐；没有则自动改用 Playwright 自带 Chromium）

## 安装

```bat
git clone git@github.com:flynncat/WebLottery.git
cd WebLottery
pip install -r requirements.txt
python -m playwright install chromium
```

## 启动

双击 `启动.bat`，或在项目目录执行：

```bat
python app.py
```

## 使用

1. 粘贴直播地址，例如 `https://qlive.woa.com/user/live?liveId=...`
2. **首次务必勾选「显示浏览器窗口」**，在弹出的 Chrome 里完成企业微信 / SSO 登录
3. 点「开始监控」。程序会持续查看页面上的 `.count-box` / `.count-time`
4. 倒计时出现后，右下角弹窗 + 提示音。点「前往直播」把页面置于前台，再手动点抽奖
5. 需要结束时点「停止监控」

直播地址和「是否显示浏览器」会写入本地 `config.json`，下次打开会自动带上。该文件和登录目录都不会提交到 Git。

## 检测依据

| 状态 | 页面特征 |
| --- | --- |
| 未开始 / 已结束 | `.count-info.is-result`，`.count-time` 文案为「查看结果」 |
| 抽奖倒计时 | `.count-time` 内出现 `<span status="1">`，或可见时间为 `00:10` 这类格式 |

## 项目结构

```
WebLottery/
├── app.py              # Tkinter 主界面
├── monitor.py          # Playwright 打开直播页并检测倒计时
├── notifier.py         # 右下角提醒弹窗
├── 启动.bat            # Windows 启动脚本
├── requirements.txt
├── config.json         # 本机配置（不入库）
└── .chrome-profile/    # Chrome 登录态（不入库）
```

## 依赖

见 `requirements.txt`：

```
playwright>=1.40.0
```

## 注意

- 仅用于本人已登录、有权访问的直播页提醒，不会代替你点击抽奖
- `.chrome-profile/` 含登录 Cookie，请勿分享或提交到仓库
- 直播页 DOM 若改版，倒计时检测可能失效，需要同步更新选择器
