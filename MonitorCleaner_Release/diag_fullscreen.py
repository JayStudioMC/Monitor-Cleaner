"""フルスクリーン検知デバッグ - 15秒間連続監視"""
import time
import win32gui
import win32api
from core.window_manager import get_visible_windows, is_window_fullscreen

print("15秒間、全ウィンドウを監視します。")
print("今すぐYouTubeをフルスクリーンにしてください！")
print("=" * 60)

monitors = []
for hMon, hdc, rect in win32api.EnumDisplayMonitors():
    monitors.append(rect)
    print(f"Monitor: {rect}")

found_any = False
for tick in range(30):
    time.sleep(0.5)
    windows = get_visible_windows()
    for w in windows:
        try:
            rect = win32gui.GetWindowRect(w.hwnd)
        except:
            continue
        wl, wt, wr, wb = rect
        for mi, (ml, mt, mr, mb) in enumerate(monitors):
            # モニターに近いウィンドウだけ表示
            if (abs(wl - ml) <= 20 and abs(wt - mt) <= 20 and
                    abs(wr - mr) <= 20 and abs(wb - mb) <= 20):
                is_fs = is_window_fullscreen(w.hwnd)
                print(f"[{tick*0.5:.1f}s] '{w.title[:40]}' (pid={w.pid})")
                print(f"   Window=({wl},{wt},{wr},{wb}) Monitor{mi}=({ml},{mt},{mr},{mb})")
                print(f"   差分: L={abs(wl-ml)} T={abs(wt-mt)} R={abs(wr-mr)} B={abs(wb-mb)}")
                print(f"   is_fullscreen={is_fs}")
                found_any = True

if not found_any:
    print("\nフルスクリーンに近いウィンドウは検出されませんでした。")
    print("全ウィンドウの矩形:")
    windows = get_visible_windows()
    for w in windows[:10]:
        try:
            rect = win32gui.GetWindowRect(w.hwnd)
            print(f"  '{w.title[:40]}' rect={rect}")
        except:
            pass
print("\n完了")
