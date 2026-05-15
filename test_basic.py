"""基本的な動作確認テスト"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== Monitor Cleaner テスト ===")

# 1. Config テスト
from config import Config
c = Config()
print(f"[OK] Config loaded: timeout={c.timeout_seconds}s, auto_start={c.auto_start}")

# 2. Monitor テスト
from core.monitor import get_monitors, get_cursor_position, monitor_from_point
mons = get_monitors()
print(f"[OK] Monitors found: {len(mons)}")
for m in mons:
    print(f"     {m}")
cx, cy = get_cursor_position()
cur_mon = monitor_from_point(cx, cy, mons)
print(f"[OK] Cursor at ({cx}, {cy}) -> {cur_mon}")

# 3. Window Manager テスト
from core.window_manager import get_visible_windows, get_windows_on_monitor
windows = get_visible_windows()
print(f"[OK] Visible windows: {len(windows)}")
for w in windows[:5]:
    print(f"     hwnd={w.hwnd}, z={w.z_index}, proc={w.process_name}, title={w.title[:50]}")
if len(windows) > 5:
    print(f"     ... and {len(windows) - 5} more")

# 4. Media Detector テスト
from core.media_detector import get_video_windows
video_wins = get_video_windows(windows, c.video_keywords)
print(f"[OK] Video windows: {len(video_wins)}")
for vw in video_wins:
    print(f"     {vw.title[:60]}")

# 5. PyQt6 インポートテスト
from PyQt6.QtWidgets import QApplication
print("[OK] PyQt6 imported successfully")

print("\n=== 全テスト通過 ===")
