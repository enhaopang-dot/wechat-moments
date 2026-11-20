#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 test_full_flow.py 是否能打开 550x800 弹窗"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from interception import ffi, lib
from interception.utils import raise_process_priority
import ctypes
from ctypes import wintypes
import time

_user32 = ctypes.windll.user32

def activate_wechat():
    def cb(hwnd, lp):
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
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(cb)
    _user32.EnumWindows(proc, 0)

def interception_click(context, device, x, y):
    screen_w, screen_h = 2560, 1600
    stroke = ffi.new("InterceptionMouseStroke *")
    stroke.state = 0
    stroke.flags = 0x001 | 0x8000
    stroke.rolling = 0
    stroke.x = int(x * 65535 / screen_w)
    stroke.y = int(y * 65535 / screen_h)
    stroke.information = 0
    lib.interception_send(context, device, stroke, 1)
    time.sleep(0.2)
    stroke.state = 1
    stroke.flags = 0
    stroke.x = stroke.y = 0
    lib.interception_send(context, device, stroke, 1)
    time.sleep(0.1)
    stroke.state = 2
    lib.interception_send(context, device, stroke, 1)
    time.sleep(0.2)

def find_popup():
    results = []
    def cb(hwnd, lp):
        if _user32.IsWindowVisible(hwnd):
            length = _user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                _user32.GetWindowTextW(hwnd, buff, length + 1)
                if "朋友圈" in buff.value:
                    rect = wintypes.RECT()
                    _user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    results.append((rect.left, rect.top, rect.right-rect.left, rect.bottom-rect.top))
        return True
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(cb)
    _user32.EnumWindows(proc, 0)
    return min(results, key=lambda x: len(str(x))) if results else None

def main():
    activate_wechat()
    time.sleep(1)
    raise_process_priority()
    ctx = lib.interception_create_context()
    if not ctx:
        print("[失败] 无法创建上下文")
        return
    device = None
    for d in range(11, 21):
        if lib.interception_is_mouse(d):
            device = d
            break
    if not device:
        print("[失败] 未找到鼠标设备")
        lib.interception_destroy_context(ctx)
        return

    print("点击发现按钮...")
    interception_click(ctx, device, 41, 407)
    time.sleep(1)

    popup = find_popup()
    if popup:
        print(f"弹窗: {popup}")
    else:
        print("未找到弹窗")

    lib.interception_destroy_context(ctx)

if __name__ == "__main__":
    main()
