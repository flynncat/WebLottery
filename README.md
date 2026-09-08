# 直播抽奖监控

监控企业直播页（qlive）底部「抽奖」区域。当 `.count-time` 从「查看结果」变成倒计时（`status="1"` 或 `00:10` 这类时间）时，屏幕右下角弹出提醒。点击「前往直播」会把浏览器拉到前台，抽奖按钮仍需你自己点。

## 环境

- Windows
- Python 3.10+
- 本机已安装 Chrome（优先使用；没有则自动改用 Playwright 自带 Chromium）

```bat
cd lottery-monitor
pip install -r requirements.txt
python -m playwright install chromium
启动.bat
```

也可以直接：

```bat
python app.py
```

## 使用

1. 粘贴直播地址，例如 `https://qlive.woa.com/user/live?liveId=...`
2. **首次务必勾选「显示浏览器窗口」**，在弹出的 Chrome 里完成企业微信 / SSO 登录。登录态会保存在 `.chrome-profile`，之后不用重复登。
3. 点「开始监控」。程序会持续查看 `.count-box` / `.count-time`。
4. 倒计时出现后，右下角弹窗 + 系统提示音。点「前往直播」把页面置于前台，再手动点抽奖。

## 检测依据

| 状态 | 页面特征 |
| --- | --- |
| 未开始 / 已结束 | `.count-info.is-result`，`.count-time` 文案为「查看结果」 |
| 抽奖倒计时 | `.count-time` 内出现 `<span status="1">`，可见时间为 `00:10` 这类格式 |

程序不会自动点击抽奖，只负责提醒和切回直播页。
