# Changelog

## v6.2 (2026-05-30)

### 修复
- **移除 pyautogui 依赖** — 关键修复。pyautogui 导入时注册 Windows 全局输入钩子，改变进程输入特征，导致微信打开不可滚动的 825x1200 弹窗。改用 `PIL.ImageGrab` 替代截图。
- **翻页方式改为 Down 箭头键** — 每次滚动1行，逐条捕获，不跳过短内容。Page Down 翻页量太大（一整页），容易跳过纯文字朋友圈。
- **添加随机时间间隔** — 所有按键和等待时间使用 `random.uniform()` 随机化，避免固定间隔被微信行为模型检测。

### 技术细节
- 新增 `send_key()` 通用键盘函数，支持任意扫描码
- 保留 `send_pagedown()` 作为无变化时的补救翻页（大跳触发加载更多）
- Interception 鼠标上下文复用模式（test_full_flow.py 验证成功的方式）

## v6.1 (2026-05-30)

### 变更
- 主翻页从 InjectMouseInput 滚轮改为 Interception Page Down
- 添加滚轮补救逻辑：Page Down 无变化时尝试滚轮触发加载更多

### 问题
- Page Down 在 825x1200 弹窗上翻页量不稳定
- 未解决弹窗类型不一致的根本问题

## v6.0 (2026-05-29)

### 新增
- 集成 Interception 驱动级点击（绕过微信点击防护）
- InjectMouseInput 滚轮翻页
- 截图对比自动检测（变化率 > 2% 认为有效翻页）
- 自动归档到 `原始截图/YYYY-MM-DD/` 目录

## v5.0 (2026-05-29)

### 发现
- pyautogui / pynput / SendInput / mouse_event 全部被微信拦截
- InjectMouseInput (Win10 1809+) 是唯一可用的 Win32 API，但只能用于滚轮，点击仍被拦截
- Interception 驱动是唯一能同时绕过点击和键盘防护的方案
