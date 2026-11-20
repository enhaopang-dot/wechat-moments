#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信朋友圈自动截图 v6.1 — 全自动版
基于 test_full_flow.py 验证成功的核心逻辑
"""

import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# DPI Awareness: must be set before any window creation
# Fixes 150% DPI scaling where logical coords != physical pixels
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import time
import random
import os
import json
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageChops, ImageGrab

# ===== Interception =====
try:
    from interception import ffi, lib
    from interception.utils import raise_process_priority
    _HAS_INTERCEPTION = True
except ImportError:
    _HAS_INTERCEPTION = False

SKILL_DIR = Path(__file__).parent.resolve()
RUNTIME_DIR = SKILL_DIR / "runtime"
CONFIG_PATH = RUNTIME_DIR / "config.json"
SAVE_DIR = Path("D:/Claude/项目/01 参谋长/07-人脉图谱/微信朋友圈文件夹/原始截图")

RUNTIME_DIR.mkdir(exist_ok=True)


# ==================== Windows API ====================

_user32 = ctypes.windll.user32
_gdi32 = ctypes.windll.gdi32

class INJECT_MOUSE_INPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.ULONG),
    ]

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120

INTERCEPTION_MOUSE_LEFT_BUTTON_DOWN = 0x001
INTERCEPTION_MOUSE_LEFT_BUTTON_UP = 0x002
INTERCEPTION_MOUSE_MOVE_ABSOLUTE = 0x001


# ==================== 屏幕分辨率 ====================

def _get_physical_screen_size():
    class DEVMODE(ctypes.Structure):
        _fields_ = [
            ("dmDeviceName", ctypes.c_wchar * 32),
            ("dmSpecVersion", ctypes.c_ushort),
            ("dmDriverVersion", ctypes.c_ushort),
            ("dmSize", ctypes.c_ushort),
            ("dmDriverExtra", ctypes.c_ushort),
            ("dmFields", ctypes.c_ulong),
            ("dmOrientation", ctypes.c_short),
            ("dmPaperSize", ctypes.c_short),
            ("dmPaperLength", ctypes.c_short),
            ("dmPaperWidth", ctypes.c_short),
            ("dmScale", ctypes.c_short),
            ("dmCopies", ctypes.c_short),
            ("dmDefaultSource", ctypes.c_short),
            ("dmPrintQuality", ctypes.c_short),
            ("dmColor", ctypes.c_short),
            ("dmDuplex", ctypes.c_short),
            ("dmYResolution", ctypes.c_short),
            ("dmTTOption", ctypes.c_short),
            ("dmCollate", ctypes.c_short),
            ("dmFormName", ctypes.c_wchar * 32),
            ("dmLogPixels", ctypes.c_ushort),
            ("dmBitsPerPel", ctypes.c_ulong),
            ("dmPelsWidth", ctypes.c_ulong),
            ("dmPelsHeight", ctypes.c_ulong),
            ("dmDisplayFlags", ctypes.c_ulong),
            ("dmDisplayFrequency", ctypes.c_ulong),
            ("dmICMMethod", ctypes.c_ulong),
            ("dmICMIntent", ctypes.c_ulong),
            ("dmMediaType", ctypes.c_ulong),
            ("dmDitherType", ctypes.c_ulong),
            ("dmReserved1", ctypes.c_ulong),
            ("dmReserved2", ctypes.c_ulong),
            ("dmPanningWidth", ctypes.c_ulong),
            ("dmPanningHeight", ctypes.c_ulong),
        ]
    dm = DEVMODE()
    dm.dmSize = ctypes.sizeof(DEVMODE)
    if _user32.EnumDisplaySettingsW(None, -1, ctypes.byref(dm)):
        return dm.dmPelsWidth, dm.dmPelsHeight
    hdc = _user32.GetDC(None)
    w = _gdi32.GetDeviceCaps(hdc, 8)
    h = _gdi32.GetDeviceCaps(hdc, 10)
    _user32.ReleaseDC(None, hdc)
    return w, h


_screen_w, _screen_h = _get_physical_screen_size()
print(f"[系统] 物理屏幕分辨率: {_screen_w}x{_screen_h}")


def _to_abs(screen_x, screen_y):
    return int(screen_x * 65535 / _screen_w), int(screen_y * 65535 / _screen_h)


# ==================== InjectMouseInput ====================

def inject_move(screen_x, screen_y):
    abs_x, abs_y = _to_abs(screen_x, screen_y)
    inp = INJECT_MOUSE_INPUT()
    inp.dx, inp.dy = abs_x, abs_y
    inp.mouseData = 0
    inp.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
    inp.time = 0
    inp.dwExtraInfo = 0
    arr = (INJECT_MOUSE_INPUT * 1)(inp)
    _user32.InjectMouseInput(ctypes.byref(arr), 1)


def inject_scroll_down(times=3, delta_multiplier=3):
    """使用 InjectMouseInput 发送滚轮事件"""
    delta = WHEEL_DELTA * delta_multiplier
    inp = INJECT_MOUSE_INPUT()
    inp.dx, inp.dy = 0, 0
    inp.mouseData = delta
    inp.dwFlags = MOUSEEVENTF_WHEEL
    inp.time = 0
    inp.dwExtraInfo = 0
    arr = (INJECT_MOUSE_INPUT * 1)(inp)
    for _ in range(times):
        _user32.InjectMouseInput(ctypes.byref(arr), 1)
        time.sleep(random.uniform(0.03, 0.08))


def send_pagedown(ctx, device, count=1):
    """使用 Interception 驱动发送 Page Down 键（带随机延迟反检测）"""
    stroke = ffi.new("InterceptionKeyStroke *")
    SCANCODE_PAGEDOWN = 0x51
    INTERCEPTION_KEY_DOWN = 0x00
    INTERCEPTION_KEY_UP = 0x01
    INTERCEPTION_KEY_E0 = 0x02
    for _ in range(count):
        stroke.code = SCANCODE_PAGEDOWN
        stroke.state = INTERCEPTION_KEY_DOWN | INTERCEPTION_KEY_E0
        stroke.information = 0
        lib.interception_send(ctx, device, stroke, 1)
        time.sleep(random.uniform(0.03, 0.08))
        stroke.state = INTERCEPTION_KEY_UP | INTERCEPTION_KEY_E0
        lib.interception_send(ctx, device, stroke, 1)
        time.sleep(random.uniform(0.05, 0.15))


def send_key(ctx, device, scancode, e0=True, count=1):
    """发送任意键盘键（带随机延迟）"""
    stroke = ffi.new("InterceptionKeyStroke *")
    INTERCEPTION_KEY_DOWN = 0x00
    INTERCEPTION_KEY_UP = 0x01
    INTERCEPTION_KEY_E0 = 0x02
    for _ in range(count):
        stroke.code = scancode
        if e0:
            stroke.state = INTERCEPTION_KEY_DOWN | INTERCEPTION_KEY_E0
        else:
            stroke.state = INTERCEPTION_KEY_DOWN
        stroke.information = 0
        lib.interception_send(ctx, device, stroke, 1)
        time.sleep(random.uniform(0.03, 0.08))
        if e0:
            stroke.state = INTERCEPTION_KEY_UP | INTERCEPTION_KEY_E0
        else:
            stroke.state = INTERCEPTION_KEY_UP
        lib.interception_send(ctx, device, stroke, 1)
        time.sleep(random.uniform(0.05, 0.15))


# ==================== Interception 点击 ====================

def interception_click(x, y, ctx=None, device=None):
    """Interception 驱动级点击。传入 ctx+device 复用外部上下文。"""
    if not _HAS_INTERCEPTION:
        return False
    own_ctx = False
    try:
        if ctx is None:
            ctx = lib.interception_create_context()
            if not ctx:
                return False
            own_ctx = True
            device = None
            for d in range(11, 21):
                if lib.interception_is_mouse(d):
                    device = d
                    break
            if not device:
                lib.interception_destroy_context(ctx)
                return False

        stroke = ffi.new("InterceptionMouseStroke *")
        stroke.state = 0
        stroke.flags = INTERCEPTION_MOUSE_MOVE_ABSOLUTE
        stroke.rolling = 0
        stroke.x = int(x * 65535 / _screen_w)
        stroke.y = int(y * 65535 / _screen_h)
        stroke.information = 0
        lib.interception_send(ctx, device, stroke, 1)
        time.sleep(0.2)

        stroke.state = INTERCEPTION_MOUSE_LEFT_BUTTON_DOWN
        stroke.flags = 0
        stroke.x = stroke.y = 0
        lib.interception_send(ctx, device, stroke, 1)
        time.sleep(0.1)

        stroke.state = INTERCEPTION_MOUSE_LEFT_BUTTON_UP
        stroke.flags = 0
        stroke.x = stroke.y = 0
        lib.interception_send(ctx, device, stroke, 1)
        time.sleep(0.2)

        if own_ctx:
            lib.interception_destroy_context(ctx)
        return True
    except Exception as e:
        print(f"   [Interception错误] {e}")
        if own_ctx and ctx:
            try:
                lib.interception_destroy_context(ctx)
            except Exception:
                pass
        return False


# ==================== 配置 ====================

DEFAULT_CONFIG = {
    "discover_btn": [41, 407],
    "version": 2
}

SIMILARITY_THRESHOLD = 0.01


def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                if "btn" in cfg and "discover_btn" not in cfg:
                    cfg["discover_btn"] = cfg["btn"]
                return cfg
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ==================== 截图对比 ====================

def screenshot_region(region, hwnd=None):
    x, y, w, h = region
    if hwnd:
        # Bring popup to top before screenshot
        _user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)  # HWND_TOPMOST
        time.sleep(0.05)
    img = ImageGrab.grab(bbox=(x, y, x+w, y+h))
    if hwnd:
        # Remove topmost after screenshot
        _user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0001 | 0x0002)  # HWND_NOTOPMOST
    return img


def image_difference_ratio(img1, img2):
    if img1.size != img2.size:
        return 1.0
    diff = ImageChops.difference(img1, img2)
    bbox = diff.getbbox()
    if bbox is None:
        return 0.0
    diff_gray = diff.convert("L")
    pixels = list(diff_gray.getdata())
    diff_count = sum(1 for p in pixels if p > 10)
    return diff_count / len(pixels)


def is_mostly_blank(img, threshold=0.95):
    small = img.resize((100, 100), Image.LANCZOS)
    pixels = list(small.getdata())
    if not pixels:
        return True
    from collections import Counter
    quantized = [(r//10*10, g//10*10, b//10*10) for r, g, b in pixels if len([r,g,b]) == 3]
    if not quantized:
        return True
    most_common = Counter(quantized).most_common(1)[0][1]
    ratio = most_common / len(quantized)
    return ratio > threshold


# ==================== 窗口操作 ====================

def activate_wechat_window():
    """激活微信窗口（和 test_full_flow.py 一致）"""
    def enum_callback(hwnd, lParam):
        if _user32.IsWindowVisible(hwnd):
            length = _user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                _user32.GetWindowTextW(hwnd, buff, length + 1)
                if "微信" in buff.value:
                    _user32.ShowWindow(hwnd, 9)
                    time.sleep(0.2)
                    _user32.SetForegroundWindow(hwnd)
                    time.sleep(0.3)
        return True
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    proc = EnumWindowsProc(enum_callback)
    _user32.EnumWindows(proc, 0)
    return True


def get_window_dpi_scale(hwnd):
    """获取窗口的 DPI 缩放因子（用于 150% 等 DPI 缩放）"""
    try:
        dpi = _user32.GetDpiForWindow(hwnd)
        return dpi / 96.0
    except Exception:
        return 1.0

def find_friend_circle_window():
    results = []
    def cb(hwnd, lp):
        if _user32.IsWindowVisible(hwnd):
            length = _user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                _user32.GetWindowTextW(hwnd, buff, length + 1)
                if "朋友圈" in buff.value:
                    rect = ctypes.wintypes.RECT()
                    _user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    scale = get_window_dpi_scale(hwnd)
                    results.append((hwnd, buff.value, rect.left, rect.top, rect.right, rect.bottom, scale))
        return True
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(cb)
    _user32.EnumWindows(proc, 0)
    if not results:
        return None
    return min(results, key=lambda x: len(x[1]))


# ==================== 主循环 ====================

def capture_loop(config, max_count=None):
    discover_btn = config.get("discover_btn", [41, 407])

    # 步骤1: 激活微信主窗口并点击"发现"
    # ===== 完全复制 test_full_flow.py 的打开流程 =====
    print(f"\n[点击] 发现按钮 ({discover_btn[0]}, {discover_btn[1]})")
    activate_wechat_window()
    time.sleep(1)

    if _HAS_INTERCEPTION:
        raise_process_priority()
        print("   [Interception] 驱动级点击...")
        click_ctx = lib.interception_create_context()
        if click_ctx:
            click_device = None
            for d in range(11, 21):
                if lib.interception_is_mouse(d):
                    click_device = d
                    break
            if click_device:
                interception_click(discover_btn[0], discover_btn[1], ctx=click_ctx, device=click_device)
                print("   [成功] 点击已发送")
            else:
                print("   [失败] 未找到鼠标设备")
                lib.interception_destroy_context(click_ctx)
                click_ctx = None
        else:
            print("   [失败] 无法创建上下文")
    else:
        print("   [警告] Interception未安装，请手动点击发现按钮")
        input("   点击后按 Enter 继续...")

    # 步骤2: 等待弹窗（和 test_full_flow.py 一样只等1秒）
    print("\n[检测] 等待朋友圈弹窗...")
    time.sleep(1)
    fc = find_friend_circle_window()
    region = None
    fc_hwnd = None
    dpi_scale = 1.0
    if fc:
        fc_hwnd, title, wx, wy, wr, wb, dpi_scale = fc
        # 使用物理尺寸（考虑 DPI 缩放如 150%）
        phys_w = int((wr - wx) * dpi_scale)
        phys_h = int((wb - wy) * dpi_scale)
        region = [wx, wy, phys_w, phys_h]
        print(f"   [成功] 弹窗: '{title}' 位置: ({wx}, {wy}) 逻辑大小: {wr-wx}x{wb-wy} DPI缩放: {dpi_scale:.1f}x 物理大小: {phys_w}x{phys_h}")
    else:
        # 如果1秒没找到，再额外等几秒
        for i in range(5):
            time.sleep(1)
            fc = find_friend_circle_window()
            if fc:
                fc_hwnd, title, wx, wy, wr, wb, dpi_scale = fc
                phys_w = int((wr - wx) * dpi_scale)
                phys_h = int((wb - wy) * dpi_scale)
                region = [wx, wy, phys_w, phys_h]
                print(f"   [成功] 弹窗: '{title}' 位置: ({wx}, {wy}) 逻辑大小: {wr-wx}x{wb-wy} DPI缩放: {dpi_scale:.1f}x 物理大小: {phys_w}x{phys_h}")
                break
            print(f"   等待... {i+1}/5")

    if not fc:
        print("   [失败] 未检测到弹窗")
        return None, [], 0

    x, y, w, h = region
    cx = x + w // 2
    cy = y + h // 2

    # 首次截图
    print("\n[验证] 首次截图...")
    first_img = screenshot_region(region, hwnd=fc_hwnd)

    debug_dir = RUNTIME_DIR / "debug"
    debug_dir.mkdir(exist_ok=True)
    debug_path = debug_dir / f"first_{datetime.now().strftime('%H%M%S')}.png"
    first_img.save(debug_path)

    if is_mostly_blank(first_img):
        print("   [错误] 截图内容空白，可能未正确打开")
        return None, [], 0

    print("   [成功] 截图内容正常\n")

    # 初始化 Interception 键盘（用于发送 Page Down）
    kb_ctx = lib.interception_create_context()
    if not kb_ctx:
        print("[警告] Interception 上下文创建失败，将使用 InjectMouseInput 滚轮")
        kb_device = None
    else:
        kb_device = None
        for d in range(1, 11):
            if lib.interception_is_keyboard(d):
                kb_device = d
                break
        if not kb_device:
            print("[警告] 未找到键盘设备，将使用 InjectMouseInput 滚轮")
            lib.interception_destroy_context(kb_ctx)
            kb_ctx = None

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = SAVE_DIR / f"批次_{session_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    print(f"[保存] {temp_dir.name}\n")

    screenshots = []
    prev_img = first_img
    fail_streak = 0
    count = 0
    start_at = time.time()

    if kb_device:
        print(f"[开始] 驱动级 Page Down 翻页 | Ctrl+C 停止\n")
    else:
        print(f"[开始] 驱动级滚轮翻页 | Ctrl+C 停止\n")

    try:
        while True:
            if max_count and count >= max_count:
                print(f"\n[停止] 达到最大张数 {max_count}")
                break

            count += 1
            ts = datetime.now().strftime("%H%M%S")
            filename = f"朋友圈_{count:03d}_{ts}.png"
            filepath = temp_dir / filename

            img = screenshot_region(region, hwnd=fc_hwnd)
            img.save(filepath)
            screenshots.append(filepath)

            diff_ratio = image_difference_ratio(prev_img, img)
            scrolled = diff_ratio > SIMILARITY_THRESHOLD

            status = ""
            if count > 1:
                if scrolled:
                    status = f"  (变化: {diff_ratio*100:.1f}%)"
                    fail_streak = 0
                else:
                    # Page Down 无变化，尝试滚轮触发加载更多
                    if kb_device:
                        # 无变化时：用 Page Down 补救（大跳翻页）
                        send_pagedown(kb_ctx, kb_device, count=1)
                        time.sleep(random.uniform(2.0, 3.5))
                        img2 = screenshot_region(region, hwnd=fc_hwnd)
                        diff_ratio2 = image_difference_ratio(prev_img, img2)
                        if diff_ratio2 > SIMILARITY_THRESHOLD:
                            img2.save(filepath)
                            img = img2
                            scrolled = True
                            fail_streak = 0
                            status = f"  (变化: {diff_ratio2*100:.1f}%, PageDown补救)"
                        else:
                            fail_streak += 1
                            status = f"  (无变化, 连续{fail_streak}次)"
                    else:
                        fail_streak += 1
                        status = f"  (无变化, 连续{fail_streak}次)"

            print(f"   [{count:03d}] {filename}{status}")

            if fail_streak >= 5:
                print(f"\n[停止] 连续5次无变化，可能已到底")
                break

            prev_img = img

            if kb_device:
                # 主翻页：Down 箭头（每次滚动一行，不跳过内容）
                send_key(kb_ctx, kb_device, scancode=0x50, e0=True, count=1)
                time.sleep(random.uniform(1.5, 2.5))
            else:
                # 备用：InjectMouseInput 滚轮
                scroll_target_x = x + w // 2
                scroll_target_y = y + h // 2
                inject_move(scroll_target_x, scroll_target_y)
                time.sleep(random.uniform(0.2, 0.5))
                inject_scroll_down(times=3, delta_multiplier=3)
                time.sleep(random.uniform(2.0, 3.5))

    except KeyboardInterrupt:
        print(f"\n\n[停止] 手动中断，共 {count} 张")

    if kb_ctx:
        lib.interception_destroy_context(kb_ctx)
    if click_ctx:
        lib.interception_destroy_context(click_ctx)

    duration = time.time() - start_at
    return temp_dir, screenshots, duration


# ==================== 归档 ====================

def finalize(temp_dir, screenshots, duration):
    if not screenshots:
        print("\n未截取到图片")
        return

    print(f"\n{'=' * 55}")
    print("  归档")
    print(f"{'=' * 55}")

    now = datetime.now()
    folder_name = f"{now.strftime('%Y-%m-%d')}"

    final_dir = SAVE_DIR / folder_name
    if final_dir.exists():
        final_dir = SAVE_DIR / f"{folder_name}_{now.strftime('%H%M%S')}"

    try:
        temp_dir.rename(final_dir)
        print(f"[归档] {final_dir.name}")
    except Exception as e:
        print(f"[警告] 重命名失败: {e}")
        final_dir = temp_dir

    print(f"\n{'=' * 55}")
    print(f"  截图: {len(screenshots)} 张")
    print(f"  耗时: {duration:.0f} 秒")
    print(f"  位置: {final_dir}")
    print(f"{'=' * 55}\n")


# ==================== 主入口 ====================

def main():
    parser = argparse.ArgumentParser(description="微信朋友圈自动截图 v6.1 (全自动)")
    parser.add_argument("--auto", action="store_true", help="全自动模式")
    parser.add_argument("--max", type=int, default=None, help="最大截图张数")
    parser.add_argument("--relocate", action="store_true", help="强制重新定位")
    args = parser.parse_args()

    print("\n" + "=" * 55)
    print("  微信朋友圈自动截图 v6.1 (全自动)")
    print("=" * 55)

    if _HAS_INTERCEPTION:
        print("   [Interception驱动] 已加载")
    else:
        print("   [警告] Interception未安装")

    config = load_config()
    print(f"\n使用坐标: discover_btn={config['discover_btn']}")

    max_count = args.max
    if not args.auto:
        max_in = input("\n最大截图数（回车=无限制）: ").strip()
        max_count = int(max_in) if max_in.isdigit() else max_count
        input("\n确保微信已打开，按 Enter 开始...")
    else:
        print(f"\n[auto] 最大: {max_count or '无限制'}")
        print("[auto] 5秒后开始...")
        time.sleep(5)

    result = capture_loop(config, max_count=max_count)
    if result[0] is not None:
        finalize(*result)


if __name__ == "__main__":
    main()
