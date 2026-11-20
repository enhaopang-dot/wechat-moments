#!/usr/bin/env python3
# -*- coding: utf-8 -*"
"""
按日期整理朋友圈截图
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import re
from pathlib import Path
from datetime import datetime, timedelta
import shutil

try:
    import easyocr
except ImportError:
    print("[错误] 未安装 easyocr，请运行: pip install easyocr")
    sys.exit(1)

# 配置
SRC_DIR = Path("D:/Claude/项目/01 参谋长/07-人脉图谱/08-微信朋友圈文件夹/原始截图/2026-05-30_215909")
DST_DIR = Path("D:/Claude/项目/01 参谋长/07-人脉图谱/08-微信朋友圈文件夹/按日期整理")
TODAY = datetime(2026, 5, 30)

def parse_date(text):
    """从OCR文本中提取日期"""
    text = text.replace(" ", "").replace("\n", "")

    # 刚刚 / X分钟前 / X小时前 -> 今天
    if re.search(r'刚刚|(\d+)分钟前|(\d+)小时前', text):
        return TODAY.strftime('%Y-%m-%d')

    # 昨天 -> 昨天
    if '昨天' in text:
        return (TODAY - timedelta(days=1)).strftime('%Y-%m-%d')

    # X天前
    m = re.search(r'(\d+)天前', text)
    if m:
        days = int(m.group(1))
        return (TODAY - timedelta(days=days)).strftime('%Y-%m-%d')

    # X月Y日 -> 2026-X-Y
    m = re.search(r'(\d+)月(\d+)日', text)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        return f"2026-{month:02d}-{day:02d}"

    # YYYY-MM-DD
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
    if m:
        return m.group(0)

    return None

def main():
    print("=" * 55)
    print("  朋友圈截图按日期整理")
    print("=" * 55)

    png_files = sorted(SRC_DIR.glob("朋友圈_*.png"))
    if not png_files:
        print(f"[错误] 未找到截图: {SRC_DIR}")
        return

    print(f"\n找到 {len(png_files)} 张截图")
    print("初始化 EasyOCR（首次运行会下载模型，请等待）...")
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
    print("OCR 引擎就绪\n")

    date_map = {}  # date_str -> [files]
    stats = {}

    for filepath in png_files:
        print(f"  OCR: {filepath.name}", end=" ")
        result = reader.readtext(str(filepath), detail=0)
        text = " ".join(result)

        date_str = parse_date(text)
        if date_str:
            print(f"-> {date_str}")
            date_map.setdefault(date_str, []).append(filepath)
            stats[date_str] = stats.get(date_str, 0) + 1
        else:
            print("-> 未识别日期")
            date_map.setdefault("未识别", []).append(filepath)

    # 创建目标文件夹并复制
    print(f"\n{'=' * 55}")
    print("  整理结果")
    print(f"{'=' * 55}")

    for date_str, files in sorted(date_map.items()):
        folder = DST_DIR / date_str
        folder.mkdir(parents=True, exist_ok=True)
        for src in files:
            dst = folder / src.name
            shutil.copy2(str(src), str(dst))
        print(f"  {date_str}: {len(files)} 张 -> {folder}")

    print(f"\n{'=' * 55}")
    print("  日期统计")
    print(f"{'=' * 55}")
    for date_str, count in sorted(stats.items()):
        print(f"  {date_str}: {count} 张")
    print(f"\n总计: {len(png_files)} 张")
    print(f"位置: {DST_DIR}")

if __name__ == "__main__":
    main()
