# /wechat-moments — 微信朋友圈自动截图 Skill

## 触发词

- "截图朋友圈"
- "抓朋友圈"
- "wechat-moments"
- "朋友圈截图"

## 功能

全自动截图微信 PC 端朋友圈，零外部 API 依赖：

1. **Interception 驱动级点击** — 绕过微信反自动化防护，自动点击"发现"按钮打开朋友圈
2. **Down 箭头键翻页** — 每次滚动1行，逐条捕获，不跳过任何内容
3. **截图对比检测** — 自动检测翻页是否生效，连续5次无变化自动停止
4. **按日期归档** — 自动保存到 `原始截图/YYYY-MM-DD/` 目录

## 用法

```bash
# 全自动模式（推荐）
python D:/Claude/配置/.claude/skills/wechat-moments/screenshot.py --auto

# 手动模式（可设置最大张数）
python D:/Claude/配置/.claude/skills/wechat-moments/screenshot.py

# 限制最大截图数
python D:/Claude/配置/.claude/skills/wechat-moments/screenshot.py --auto --max 50
```

运行前准备：
1. **确保微信 PC 端已安装 Interception 驱动**（只需安装一次，需重启生效）
2. 确保微信 PC 端已打开
3. 脚本会自动点击"发现"按钮 → 打开朋友圈弹窗 → 自动翻页截图

## 依赖

```bash
pip install Pillow interception
```

**注意：不要安装 pyautogui**（见踩坑记录第5条）。

**Interception 驱动安装**（只需一次）：
1. 下载驱动：`https://github.com/oblitum/Interception/releases`
2. 运行安装程序：`install-interception.exe /install`
3. **重启电脑**
4. 验证：`python -c "from interception import lib; print(lib.interception_create_context())"` — 应返回非 NULL

## 文件结构

```
D:/Claude/配置/.claude/skills/wechat-moments/
  SKILL.md          # 本文件
  screenshot.py     # 主脚本（v6.2）
  runtime/          # 运行时数据（自动创建）
    config.json     # 坐标配置
    debug/          # 调试用截图
```

## 技术方案

### 输入层级

| 层级 | API | 微信防护 | 效果 |
|------|-----|---------|------|
| 应用层 | pyautogui, pynput | ❌ 拦截 | 无效 |
| Win32 API | SendInput, mouse_event | ❌ 拦截 | 无效 |
| 系统调用 | InjectMouseInput (Win10 1809+) | ⚠️ 滚轮可用，点击被拦 | 滚轮有效 |
| **内核驱动** | **Interception Driver** | ✅ **绕过** | **点击+键盘均有效** |

### 翻页方式对比

| 方式 | 效果 | 问题 |
|------|------|------|
| 滚轮 | 每次滚动3行 | 微信能检测模拟滚轮，**无效** |
| Page Down | 每次翻一整页 | 翻页量太大，**容易跳过短内容** |
| **Down 箭头** | **每次滚动1行** | **推荐，逐条捕获不跳过** |

### 核心发现

1. **pyautogui 会改变弹窗类型**：
   - 导入 `pyautogui` → 微信打开 **825x1200 不可滚动弹窗**
   - 移除 `pyautogui`，改用 `PIL.ImageGrab` → 微信打开 **550x800 可滚动弹窗**
   - 原因：`pyautogui` 导入时注册 Windows 全局输入钩子，改变了进程输入特征，微信感知到后切换到防御模式弹窗

2. **弹窗尺寸与滚动能力**：
   - **550x800**：可滚动，Down 箭头有效
   - **825x1200**：不可滚动，所有模拟输入无效

3. **DPI 缩放导致截图不完整**：
   - 弹窗逻辑尺寸 550x800，但在 150% DPI 缩放下物理尺寸为 **825x1200**
   - `GetWindowRect` 返回逻辑坐标，直接用此坐标截图只截取弹窗左上角约 44%，内容严重缺失
   - **必须通过 `GetDpiForWindow` 获取 DPI 缩放因子，计算物理尺寸后再截图**

4. **最佳翻页策略**：
   - 主翻页：**Down 箭头键**（每次1行）→ 逐条滚动，不跳过内容
   - 无变化补救：**Page Down**（大跳）→ 触发加载更多历史
   - 每次翻页后随机等待 1.5-3.5 秒 → 避免固定间隔被检测

## 配置项

```json
{
  "discover_btn": [41, 407],
  "version": 2
}
```

- `discover_btn`：微信左侧"发现"按钮坐标（x, y）

如需重新定位：
```bash
python screenshot.py --relocate
```

## 踩坑记录

1. **Interception 驱动必须重启后生效** — 安装后未重启会导致 `interception_create_context()` 返回 NULL
2. **微信弹窗两种类型** — 550x800（可滚动）和 825x1200（不可滚动）
3. **DPI 缩放导致截图不完整**：
   - **根本原因**：`SetProcessDpiAwareness(2)` 后 `GetWindowRect` 直接返回**物理坐标**（150% DPI 下返回 825x1200）。若代码中再乘以 `dpi_scale(1.5x)`，会导致截图区域变成 1237x1800，超出屏幕高度被截断。
   - **正确做法**：设置 DPI Awareness 后，直接用 `GetWindowRect` 返回的宽高截图，**无需额外乘以缩放因子**。
   - **多显示器**：主屏 150% DPI + 副屏 100% DPI 时，`GetDpiForWindow(hwnd)` 返回窗口**所在显示器**的 DPI，不能假设统一缩放。
4. **弹窗自动关闭** — 550x800 弹窗一段时间后会自动关闭，脚本通过"先激活已有弹窗"策略确保复用
5. **⚠️ pyautogui 是陷阱** — `import pyautogui` 会注册全局输入钩子，导致微信打开不可滚动弹窗（825x1200）。**必须使用 `PIL.ImageGrab` 替代截图功能**。
6. **随机时间间隔** — 固定间隔容易被微信行为模型检测，所有等待时间使用 `random.uniform()` 随机化

## 更新日志

- **v6.2 (2025-05-30)**：移除 pyautogui，改用 Down 箭头键逐行翻页，稳定打开 550x800 弹窗
- **v6.1 (2025-05-30)**：改用 Page Down 翻页，兼容两种弹窗类型
- **v6.0 (2025-05-29)**：集成 Interception 驱动级点击 + InjectMouseInput 滚轮
- **v5.0 (2025-05-29)**：发现 InjectMouseInput 是唯一可用的 Win32 API
