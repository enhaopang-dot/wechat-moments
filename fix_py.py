with open('D:/Claude/配置/.claude/skills/wechat-moments/screenshot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove pyautogui lines
content = content.replace('pyautogui.FAILSAFE = True\npyautogui.PAUSE = 0.05\n\n\n# ==================== Windows API ====================', '\n\n# ==================== Windows API ====================')

# Replace pyautogui.screenshot with ImageGrab.grab
content = content.replace(
    'def screenshot_region(region):\n    return pyautogui.screenshot(region=region)',
    'def screenshot_region(region):\n    x, y, w, h = region\n    return ImageGrab.grab(bbox=(x, y, x+w, y+h))'
)

# Fix if not ctx: -> if not click_ctx:
content = content.replace(
    '    if not ctx:\n        print("   [失败] 无法创建上下文")',
    '    if not click_ctx:\n        print("   [失败] 无法创建上下文")'
)

with open('D:/Claude/配置/.claude/skills/wechat-moments/screenshot.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK')
