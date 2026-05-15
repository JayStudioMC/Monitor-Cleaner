"""ウィンドウ管理モジュール - 最小化/復元とZ-order管理"""

import ctypes
import ctypes.wintypes
import win32gui
import win32con
import win32process
import os
from dataclasses import dataclass, field
from core.monitor import MonitorInfo, monitor_from_point


# ウィンドウ情報
@dataclass
class WindowInfo:
    hwnd: int
    title: str
    process_name: str
    pid: int
    rect: tuple  # (left, top, right, bottom)
    z_index: int = 0  # Z-order index (0 = top)


def _get_process_name_native(hwnd: int) -> tuple[str, int]:
    """psutilなしでプロセス名を取得する。"""
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        # OpenProcess + GetModuleFileNameEx
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid
        )
        if handle:
            buf = ctypes.create_unicode_buffer(512)
            ctypes.windll.psapi.GetModuleFileNameExW(handle, None, buf, 512)
            ctypes.windll.kernel32.CloseHandle(handle)
            name = os.path.basename(buf.value) if buf.value else ""
            return name, pid
        return "", pid
    except Exception:
        return "", 0


def is_real_window(hwnd: int) -> bool:
    """管理対象のウィンドウかどうかを判定する。"""
    if not win32gui.IsWindowVisible(hwnd):
        return False
    if not win32gui.GetWindowText(hwnd):
        return False
    # ツールウィンドウやポップアップを除外
    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    if ex_style & win32con.WS_EX_TOOLWINDOW:
        return False
    # オーナーウィンドウがあるものを除外 (子ウィンドウ)
    if win32gui.GetParent(hwnd):
        return False
    # Shell窓 (デスクトップ) を除外
    try:
        shell_hwnd = ctypes.windll.user32.GetShellWindow()
    except Exception:
        shell_hwnd = 0
    if hwnd == shell_hwnd:
        return False
    # Cloaked windows (UWP hidden windows) を除外
    try:
        DWMWA_CLOAKED = 14
        cloaked = ctypes.c_int(0)
        ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
        )
        if cloaked.value:
            return False
    except Exception:
        pass
    return True


def get_visible_windows() -> list[WindowInfo]:
    """可視ウィンドウをZ-order順に列挙する (前面から背面の順)。"""
    windows: list[WindowInfo] = []
    z_index = 0

    def _callback(hwnd, _):
        nonlocal z_index
        try:
            if is_real_window(hwnd):
                title = win32gui.GetWindowText(hwnd)
                rect = win32gui.GetWindowRect(hwnd)
                pname, pid = _get_process_name_native(hwnd)
                windows.append(WindowInfo(
                    hwnd=hwnd,
                    title=title,
                    process_name=pname,
                    pid=pid,
                    rect=rect,
                    z_index=z_index,
                ))
                z_index += 1
        except Exception as e:
            import logging
            logging.getLogger("MonitorCleaner").error(f"EnumWindows callback exception: {e}", exc_info=True)
            pass
        return True

    win32gui.EnumWindows(_callback, None)
    return windows


def get_windows_on_monitor(
    windows: list[WindowInfo], monitor: MonitorInfo
) -> list[WindowInfo]:
    """指定モニター上のウィンドウを返す。
    ウィンドウの中心点がモニター領域にあるかで判定。
    """
    result = []
    for w in windows:
        left, top, right, bottom = w.rect
        cx = (left + right) // 2
        cy = (top + bottom) // 2
        if monitor.contains(cx, cy):
            result.append(w)
    return result


def is_window_minimized(hwnd: int) -> bool:
    """ウィンドウが最小化状態かどうか。"""
    return bool(win32gui.IsIconic(hwnd))


def minimize_window(hwnd: int):
    """ウィンドウを最小化する。"""
    try:
        if win32gui.IsWindow(hwnd) and not is_window_minimized(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    except Exception:
        pass


def restore_window(hwnd: int):
    """ウィンドウを復元する。"""
    try:
        if win32gui.IsWindow(hwnd) and is_window_minimized(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    except Exception:
        pass


def _restore_without_activate(hwnd: int):
    """最小化されたウィンドウをアクティブ化せずに復元する。

    SW_RESTORE はウィンドウをアクティブ化(フォアグラウンド化)するため、
    他モニターのウィンドウのZ-orderに影響する。
    SetWindowPlacement + SW_SHOWNOACTIVATE を使うことで、
    ウィンドウをアクティブ化せずに元のサイズ・位置に復元する。
    """
    try:
        placement = win32gui.GetWindowPlacement(hwnd)
        # placement = (flags, showCmd, ptMinPosition, ptMaxPosition, rcNormalPosition)
        # showCmd を SW_SHOWNOACTIVATE (4) に変更して復元
        new_placement = (
            placement[0],               # flags
            win32con.SW_SHOWNOACTIVATE,  # showCmd: アクティブ化しない
            placement[2],               # ptMinPosition
            placement[3],               # ptMaxPosition
            placement[4],               # rcNormalPosition
        )
        win32gui.SetWindowPlacement(hwnd, new_placement)
    except Exception:
        # フォールバック: 従来の方法
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        except Exception:
            pass


def restore_windows_with_zorder(window_infos: list[WindowInfo], target_hwnd: int | None = None):
    """Z-order を保って復元する。他モニターのZ-orderに影響しない。

    復元対象ウィンドウ同士の相対的なZ-orderを保持する。
    除外/フルスクリーンウィンドウとの位置関係は呼び出し側で別途処理する。

    手順:
    1. 記憶された順序(z_index=0が一番上)でソート
    2. target_hwnd がある場合は先頭に
    3. 全ウィンドウをアクティブ化せずに復元
    4. チェーン配置でZ-orderを構築（HWND_TOPは target_hwnd がある場合のみ）
    """
    import time as _time

    if not window_infos:
        return

    # 1. z_indexでソート
    sorted_wins = sorted(window_infos, key=lambda w: w.z_index)

    # 2. ターゲットがある場合は先頭に
    if target_hwnd is not None:
        target_win = next((w for w in sorted_wins if w.hwnd == target_hwnd), None)
        if target_win:
            sorted_wins.remove(target_win)
            sorted_wins.insert(0, target_win)

    # 3. 全ウィンドウをアクティブ化せずに復元
    for w in sorted_wins:
        try:
            if win32gui.IsWindow(w.hwnd) and is_window_minimized(w.hwnd):
                _restore_without_activate(w.hwnd)
        except Exception:
            pass

    _time.sleep(0.05)

    if not sorted_wins:
        return

    # 4. Z-order チェーン配置
    # target_hwnd がある場合のみ HWND_TOP を使用（意図的にフォアグラウンドにする）
    # それ以外は現在のZ-orderの中でチェーン配置し、他モニターに影響しない
    first_w = sorted_wins[0]
    if target_hwnd is not None:
        # ターゲットがある = Alt+Tab等でユーザーが意図的に選んだウィンドウ
        try:
            if win32gui.IsWindow(first_w.hwnd):
                win32gui.SetWindowPos(
                    first_w.hwnd,
                    win32con.HWND_TOP,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
                )
        except Exception:
            pass
    else:
        # ターゲットなし = カーソル移動による自動復元
        # HWND_TOP を使わず、復元ウィンドウ同士の相対順序だけ保つ
        # 最初のウィンドウの現在位置を基準にチェーン配置する
        pass

    prev_hwnd = first_w.hwnd
    for w in sorted_wins[1:]:
        try:
            if win32gui.IsWindow(w.hwnd):
                win32gui.SetWindowPos(
                    w.hwnd,
                    prev_hwnd,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
                )
                prev_hwnd = w.hwnd
        except Exception:
            pass

    # 5. ターゲットウィンドウを最前面に（ユーザーが意図的に選んだ場合のみ）
    if target_hwnd is not None:
        try:
            if win32gui.IsWindow(target_hwnd):
                win32gui.SetWindowPos(
                    target_hwnd,
                    win32con.HWND_TOP,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
                )
        except Exception:
            pass


def capture_window_thumbnail(hwnd: int, width: int = 200, height: int = 150) -> bytes | None:
    """ウィンドウのサムネイル画像をキャプチャしてPNGバイト列を返す。"""
    try:
        import win32ui
        import win32gui
        import win32con
        from PIL import Image
        import io

        # ウィンドウのDC取得
        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()

        rect = win32gui.GetWindowRect(hwnd)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]

        if w <= 0 or h <= 0:
            return None

        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(bmp)

        # PrintWindow API
        ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)

        bmp_info = bmp.GetInfo()
        bmp_bits = bmp.GetBitmapBits(True)

        img = Image.frombuffer(
            "RGBA", (bmp_info["bmWidth"], bmp_info["bmHeight"]),
            bmp_bits, "raw", "BGRA", 0, 1
        )
        img = img.resize((width, height), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="PNG")

        # Cleanup
        win32gui.DeleteObject(bmp.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)

        return buf.getvalue()
    except Exception:
        return None


def is_window_fullscreen(hwnd: int) -> bool:
    """ウィンドウがフルスクリーン（全画面）表示かどうかを判定する。

    判定ロジック:
    - ウィンドウの rect がいずれかのモニターの物理解像度（left,top,right,bottom）と
      ±2px の誤差範囲内で一致する場合にフルスクリーンと判定する。
    - 通常の「最大化」はタスクバー分だけ縮小されるため、区別できる。
    - ブラウザの F11 フルスクリーンを正しく検知できる。
    """
    try:
        import win32api
        rect = win32gui.GetWindowRect(hwnd)
        if not rect:
            return False
        left, top, right, bottom = rect

        TOLERANCE = 2
        for hMonitor, hdcMonitor, PyRECT in win32api.EnumDisplayMonitors():
            ml, mt, mr, mb = PyRECT
            if (abs(left - ml) <= TOLERANCE and
                    abs(top - mt) <= TOLERANCE and
                    abs(right - mr) <= TOLERANCE and
                    abs(bottom - mb) <= TOLERANCE):
                return True
    except Exception as e:
        import logging
        logging.getLogger("MonitorCleaner").error(f"is_window_fullscreen error: {e}")
    return False
