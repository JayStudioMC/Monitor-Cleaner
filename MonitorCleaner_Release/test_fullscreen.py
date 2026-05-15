import win32gui
import ctypes
import ctypes.wintypes
from core.window_manager import is_window_fullscreen, get_visible_windows
import time

print("※次の8秒以内に、ブラウザでYoutubeやdアニメの動画をフルスクリーンにしてください！")
for i in range(8):
    print(f"待機中... {8-i}")
    time.sleep(1)

windows = get_visible_windows()
print("\n--- 現在表示されているウィンドウ ---")
found_video = False
for w in windows[:10]:
    rect = win32gui.GetWindowRect(w.hwnd)
    is_fs = is_window_fullscreen(w.hwnd)
    # 動画っぽいタイトルを探す
    if "動画" in w.title or "- Google Chrome" in w.title or "YouTube" in w.title:
        found_video = True
        print(f"Title: {w.title[:40]}")
        print(f"  Rect: {rect}")
        print(f"  Is Fullscreen: {is_fs}")

print("\n--- モニターの解像度情報 ---")
monitors = []
def _mon_callback(hmon, hdc, lprect, lparam):
    try:
        info = win32gui.GetMonitorInfo(hmon)
        monitors.append(info["Monitor"])
    except:
        pass
    return True

ctypes.windll.user32.EnumDisplayMonitors(None, None,
    ctypes.WINFUNCTYPE(ctypes.c_bool,
        ctypes.c_ulong, ctypes.c_ulong,
        ctypes.POINTER(ctypes.wintypes.RECT), ctypes.c_double)(_mon_callback),
    0)
for m in monitors:
    print(f"Monitor rect: {m}")
