with open('D:/Claude/配置/.claude/skills/wechat-moments/screenshot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace main scroll loop: Page Down -> Interception wheel
old_main = '''            if kb_device:
                # 使用 Page Down 翻页（每次1个，留时间加载）
                send_pagedown(kb_ctx, kb_device, count=1)
                time.sleep(random.uniform(2.0, 3.5))
            else:
                # 备用：滚轮翻页
                scroll_target_x = x + w // 2
                scroll_target_y = y + h // 2
                inject_move(scroll_target_x, scroll_target_y)
                time.sleep(random.uniform(0.2, 0.5))
                inject_scroll_down(times=3, delta_multiplier=3)
                time.sleep(random.uniform(2.0, 3.5))'''

new_main = '''            if click_ctx and click_device:
                # 主翻页：Interception 滚轮（小步滚动，不跳过内容）
                mstroke = ffi.new("InterceptionMouseStroke *")
                # 移动鼠标到弹窗内容区
                mstroke.state = 0
                mstroke.flags = 0x001 | 0x8000
                mstroke.rolling = 0
                mstroke.x = int((x + w // 2) * 65535 / _screen_w)
                mstroke.y = int((y + h // 2 + 100) * 65535 / _screen_h)
                mstroke.information = 0
                lib.interception_send(click_ctx, click_device, mstroke, 1)
                time.sleep(random.uniform(0.3, 0.6))
                # 发送滚轮事件
                mstroke.flags = 0
                mstroke.rolling = -120 * 3
                lib.interception_send(click_ctx, click_device, mstroke, 1)
                time.sleep(random.uniform(0.1, 0.3))
                mstroke.rolling = -120 * 3
                lib.interception_send(click_ctx, click_device, mstroke, 1)
                time.sleep(random.uniform(0.1, 0.3))
                mstroke.rolling = -120 * 3
                lib.interception_send(click_ctx, click_device, mstroke, 1)
                time.sleep(random.uniform(1.5, 2.5))
            elif kb_device:
                # 备用：Page Down
                send_pagedown(kb_ctx, kb_device, count=1)
                time.sleep(random.uniform(2.0, 3.5))
            else:
                # 最后备用：InjectMouseInput 滚轮
                scroll_target_x = x + w // 2
                scroll_target_y = y + h // 2
                inject_move(scroll_target_x, scroll_target_y)
                time.sleep(random.uniform(0.2, 0.5))
                inject_scroll_down(times=3, delta_multiplier=3)
                time.sleep(random.uniform(2.0, 3.5))'''

content = content.replace(old_main, new_main)

# Replace wheel fallback: Interception wheel -> Page Down
old_fallback = '''                    if kb_device:
                        # 先用 Interception 鼠标移动光标到弹窗内部
                        if click_ctx and click_device:
                            mstroke = ffi.new("InterceptionMouseStroke *")
                            mstroke.state = 0
                            mstroke.flags = 0x001 | 0x8000
                            mstroke.rolling = 0
                            mstroke.x = int((x + w // 2) * 65535 / _screen_w)
                            mstroke.y = int((y + h // 2 + 100) * 65535 / _screen_h)
                            mstroke.information = 0
                            lib.interception_send(click_ctx, click_device, mstroke, 1)
                            time.sleep(random.uniform(0.3, 0.6))
                            # Interception 滚轮事件
                            mstroke.rolling = -120 * 3
                            lib.interception_send(click_ctx, click_device, mstroke, 1)
                            time.sleep(random.uniform(0.1, 0.3))
                            mstroke.rolling = -120 * 3
                            lib.interception_send(click_ctx, click_device, mstroke, 1)
                            time.sleep(random.uniform(0.1, 0.3))
                            mstroke.rolling = -120 * 3
                            lib.interception_send(click_ctx, click_device, mstroke, 1)
                            time.sleep(random.uniform(0.1, 0.3))
                            mstroke.rolling = 0
                        else:
                            inject_move(x + w // 2, y + h // 2)
                            time.sleep(random.uniform(0.2, 0.5))
                            inject_scroll_down(times=5, delta_multiplier=3)
                        time.sleep(random.uniform(2.0, 3.0))
                        img2 = screenshot_region(region)
                        diff_ratio2 = image_difference_ratio(prev_img, img2)
                        if diff_ratio2 > SIMILARITY_THRESHOLD:
                            img2.save(filepath)
                            img = img2
                            scrolled = True
                            fail_streak = 0
                            status = f\"  (变化: {diff_ratio2*100:.1f}%, 滚轮触发)\"
                        else:
                            fail_streak += 1
                            status = f\"  (无变化, 连续{fail_streak}次)\"'''

new_fallback = '''                    if kb_device:
                        # 无变化时：用 Page Down 补救（大跳翻页）
                        send_pagedown(kb_ctx, kb_device, count=1)
                        time.sleep(random.uniform(2.0, 3.5))
                        img2 = screenshot_region(region)
                        diff_ratio2 = image_difference_ratio(prev_img, img2)
                        if diff_ratio2 > SIMILARITY_THRESHOLD:
                            img2.save(filepath)
                            img = img2
                            scrolled = True
                            fail_streak = 0
                            status = f\"  (变化: {diff_ratio2*100:.1f}%, PageDown补救)\"
                        else:
                            fail_streak += 1
                            status = f\"  (无变化, 连续{fail_streak}次)\"'''

content = content.replace(old_fallback, new_fallback)

with open('D:/Claude/配置/.claude/skills/wechat-moments/screenshot.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK')
