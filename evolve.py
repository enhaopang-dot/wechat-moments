#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信朋友圈截图工具 — 进化模块
分析运行日志，调用 Kimi API 自动优化参数
"""

import json
import os
import re
import requests
from pathlib import Path

SKILL_DIR = Path(__file__).parent.resolve()
RUNTIME_DIR = SKILL_DIR / "runtime"
CONFIG_PATH = RUNTIME_DIR / "config.json"
LOG_PATH = RUNTIME_DIR / "log.json"
EVOLUTION_PATH = RUNTIME_DIR / "evolution.json"

KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_MODEL = "kimi-latest"


def load_json(path, default=None):
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return default if default is not None else {}


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def kimi_chat(prompt: str, max_tokens=500, timeout=30) -> str:
    if not KIMI_API_KEY:
        return ""
    payload = {
        "model": KIMI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": max_tokens
    }
    try:
        resp = requests.post(
            KIMI_API_URL,
            headers={"Authorization": f"Bearer {KIMI_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=timeout
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"   Kimi API 失败: {e}")
        return ""


def analyze_and_evolve():
    print("\n" + "=" * 55)
    print("  🧬 进化模块启动")
    print("=" * 55)

    config = load_json(CONFIG_PATH, {})
    log = load_json(LOG_PATH, {"sessions": []})
    sessions = log.get("sessions", [])

    if len(sessions) < 1:
        print("   暂无运行日志，跳过进化")
        return

    # 取最近5次运行
    recent = sessions[-5:]
    print(f"   分析最近 {len(recent)} 次运行...")

    # 计算指标
    total_count = sum(s.get("count", 0) for s in recent)
    avg_count = total_count / len(recent) if recent else 0
    avg_duration = sum(s.get("duration_sec", 0) for s in recent) / len(recent) if recent else 0
    total_samples = sum(len(s.get("time_samples", [])) for s in recent)
    success_rate = total_samples / total_count * 100 if total_count > 0 else 0

    print(f"   平均截图: {avg_count:.0f} 张/次")
    print(f"   平均耗时: {avg_duration:.0f} 秒/次")
    print(f"   OCR成功率: {success_rate:.0f}%")

    # 构造 prompt
    log_text = json.dumps(recent, ensure_ascii=False, indent=2)
    current_params = json.dumps(config, ensure_ascii=False, indent=2)

    prompt = f"""你是一位自动化测试优化专家。以下是微信朋友圈截图工具最近{len(recent)}次的运行日志：

{log_text}

当前参数配置：
{current_params}

关键指标：
- 平均每次截图 {avg_count:.0f} 张
- 平均耗时 {avg_duration:.0f} 秒
- OCR时间识别成功率 {success_rate:.0f}%

请分析运行效果，判断参数是否合理，给出优化建议。重点关注：
1. scroll_lines（每次滚轮行数）：如果截图数量少且内容有遗漏，应增大绝对值；如果有大量重复内容，应减小
2. wait_after_scroll（滚动后等待）：如果OCR识别失败率高，可能需要增加等待让内容加载
3. wait_after_click（点击后等待）：如果定位验证失败，可能需要增加
4. ocr_sample_interval（OCR采样间隔）：如果API调用过于频繁或稀疏，调整此值

请只返回纯JSON格式（不要markdown代码块，不要解释）：
{{"adjustments": [{{"param": "参数名", "value": 新值, "reason": "简短理由"}}], "summary": "一句话总结"}}
如果认为无需调整，返回 {{"adjustments": [], "summary": "当前参数合理，无需调整"}}"""

    print("\n   🤖 调用Kimi分析...")
    result = kimi_chat(prompt, max_tokens=600)
    if not result:
        print("   ❌ 进化分析失败")
        return

    # 解析 JSON
    try:
        # 尝试直接解析
        parsed = json.loads(result)
    except json.JSONDecodeError:
        # 尝试从文本中提取 JSON
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                print(f"   ⚠️ 无法解析Kimi返回: {result[:300]}")
                return
        else:
            print(f"   ⚠️ 无法解析Kimi返回: {result[:300]}")
            return

    adjustments = parsed.get("adjustments", [])
    summary = parsed.get("summary", "")

    if not adjustments:
        print(f"\n   ✓ {summary}")
        return

    print(f"\n   💡 Kimi建议: {summary}")
    print(f"   发现 {len(adjustments)} 项优化:\n")

    # 应用调整
    applied = []
    for adj in adjustments:
        param = adj.get("param", "")
        value = adj.get("value")
        reason = adj.get("reason", "")

        if param in config and value is not None:
            old_val = config[param]
            config[param] = value
            applied.append(adj)
            print(f"   ✓ {param}: {old_val} → {value}")
            print(f"     理由: {reason}")
        else:
            print(f"   ⚠️ 跳过未知参数: {param}")

    # 保存
    if applied:
        config["version"] = config.get("version", 1) + 1
        save_json(CONFIG_PATH, config)
        print(f"\n   💾 参数已更新 (v{config['version']})")

    # 记录进化历史
    evolution = load_json(EVOLUTION_PATH, {"evolutions": []})
    evolution["evolutions"].append({
        "date": __import__('datetime').datetime.now().isoformat(),
        "analyzed_sessions": len(recent),
        "metrics": {
            "avg_count": round(avg_count, 1),
            "avg_duration": round(avg_duration, 1),
            "ocr_success_rate": round(success_rate, 1)
        },
        "suggestions": adjustments,
        "applied": len(applied),
        "summary": summary
    })
    save_json(EVOLUTION_PATH, evolution)
    print(f"   📝 进化历史已记录: {EVOLUTION_PATH}")


def main():
    if not KIMI_API_KEY:
        print("❌ KIMI_API_KEY 未设置，无法运行进化模块")
        return
    analyze_and_evolve()


if __name__ == "__main__":
    main()
