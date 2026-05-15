"""モニター情報取得モジュール"""

import ctypes
import ctypes.wintypes
import win32api
import win32con


class MonitorInfo:
    """1つのモニターの情報を保持する。"""

    def __init__(self, handle, rect: tuple, is_primary: bool = False):
        self.handle = handle
        self.left, self.top, self.right, self.bottom = rect
        self.is_primary = is_primary

    @property
    def rect(self) -> tuple:
        return (self.left, self.top, self.right, self.bottom)

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def id(self) -> str:
        """モニター識別子 (位置ベース)。"""
        return f"{self.left},{self.top},{self.right},{self.bottom}"

    def contains(self, x: int, y: int) -> bool:
        """座標がこのモニター内にあるか判定。"""
        return self.left <= x < self.right and self.top <= y < self.bottom

    def __repr__(self):
        p = " [PRIMARY]" if self.is_primary else ""
        return f"Monitor({self.left},{self.top} {self.width}x{self.height}{p})"


import time

# モニター情報のキャッシュ
_monitors_cache: list[MonitorInfo] = []
_last_monitors_refresh = 0.0

def get_monitors() -> list[MonitorInfo]:
    """接続されている全モニターの情報を取得する (5秒間キャッシュ)。"""
    global _monitors_cache, _last_monitors_refresh
    now = time.time()
    if _monitors_cache and (now - _last_monitors_refresh < 5.0):
        return _monitors_cache

    monitors: list[MonitorInfo] = []

    # ctypes でコールバック型を定義
    MONITORENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,  # hMonitor
        ctypes.c_void_p,  # hdcMonitor
        ctypes.POINTER(ctypes.wintypes.RECT),  # lprcMonitor
        ctypes.c_void_p,  # dwData
    )

    def _callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        try:
            info = win32api.GetMonitorInfo(hMonitor)
            rect = info["Monitor"]
            is_primary = bool(info["Flags"] & win32con.MONITORINFOF_PRIMARY)
            monitors.append(MonitorInfo(hMonitor, rect, is_primary))
        except Exception as e:
            import logging
            logging.getLogger("MonitorCleaner").error(f"EnumDisplayMonitors callback exception: {e}")
            pass
        return True

    cb = MONITORENUMPROC(_callback)
    try:
        ctypes.windll.user32.EnumDisplayMonitors(None, None, cb, 0)
        _monitors_cache = monitors
        _last_monitors_refresh = now
    except Exception as e:
        import logging
        logging.getLogger("MonitorCleaner").error(f"EnumDisplayMonitors failed: {e}")

    return monitors or _monitors_cache


def get_cursor_position() -> tuple[int, int]:
    """現在のカーソル位置を返す。アクセス失敗時は (-1, -1) を返す。"""
    try:
        pt = win32api.GetCursorPos()
        return pt[0], pt[1]
    except Exception:
        return -1, -1


def monitor_from_point(x: int, y: int, monitors: list[MonitorInfo]) -> MonitorInfo | None:
    """座標がどのモニターに属するかを判定する。"""
    if x == -1: return None
    for mon in monitors:
        if mon.contains(x, y):
            return mon
    return None
