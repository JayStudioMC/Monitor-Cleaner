"""非アクティブ検知モジュール - モニター別のカーソル追跡と最小化/復元制御
   + グローバル非アクティブ検知 (GetLastInputInfo API)"""

import time
import re
import ctypes
import ctypes.wintypes
import win32gui
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from core.monitor import get_monitors, get_cursor_position, monitor_from_point, MonitorInfo
from core.window_manager import (
    get_visible_windows, get_windows_on_monitor, WindowInfo,
    minimize_window, restore_windows_with_zorder, is_window_minimized,
    is_window_fullscreen,
)
from core.media_detector import get_video_window_hwnds
from config import Config


# --- GetLastInputInfo 構造体 ---
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]


def get_idle_duration_ms() -> int:
    """システム全体の最後の入力からの経過ミリ秒を返す。
    マウス移動、キーボード入力、タッチ等すべての入力を検知する。
    """
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        tick_count = ctypes.windll.kernel32.GetTickCount()
        elapsed = tick_count - lii.dwTime
        # tick countは49日でオーバーフローするが、差分は正しい
        if elapsed < 0:
            elapsed += 0xFFFFFFFF
        return elapsed
    return 0


class InactivityManager(QObject):
    """モニター別の非アクティブ検知と最小化/復元を管理する。
    
    2つの最小化モード:
    1. モニター別: カーソルが離れたモニターをタイムアウト後に最小化
    2. グローバル: マウス/キーボード等の全入力がない場合に全モニターを最小化
    """

    # シグナル: (monitor_id, is_hidden)
    monitor_state_changed = pyqtSignal(str, bool)

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config

        # モニター別の最終アクティブ時刻
        self._last_active: dict[str, float] = {}
        # モニター別の最小化中ウィンドウ情報
        self._hidden_windows: dict[str, list[WindowInfo]] = {}
        # 各モニターが最小化状態かどうか
        self._is_hidden: dict[str, bool] = {}
        # 一時停止フラグ
        self._paused: bool = False
        # ロック状態のログ出力フラグ
        self._locked_logged: bool = False
        # グローバル非アクティブで最小化済みかどうか
        self._global_hidden: bool = False
        # グローバル最小化中のウィンドウ情報 (全モニター分)
        self._global_hidden_windows: dict[str, list[WindowInfo]] = {}

        # ポーリングタイマー (500ms)
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)

    def start(self):
        # 初期化: 全モニターの最終アクティブ時刻を現在にリセット
        monitors = get_monitors()
        now = time.time()
        for mon in monitors:
            self._last_active[mon.id] = now
            self._is_hidden[mon.id] = False
        self._timer.start()

    def stop(self):
        self._timer.stop()
        # 全復元
        self.restore_all()

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False
        # 全モニターのタイマーをリセット
        now = time.time()
        for mid in self._last_active:
            self._last_active[mid] = now

    @property
    def is_paused(self) -> bool:
        return self._paused

    def restore_all(self):
        """全モニターのウィンドウを復元する。"""
        # グローバル最小化分を復元
        if self._global_hidden:
            self._restore_global()
        # モニター別最小化分を復元
        for monitor_id in list(self._hidden_windows.keys()):
            self._restore_monitor(monitor_id)

    def _is_excluded(self, w: WindowInfo) -> bool:
        """ウィンドウが除外対象かどうか。"""
        # hwndベースの除外 (セッション中)
        if w.hwnd in self.config.excluded_hwnds:
            return True
        # タイトル/プロセス名パターンベースの永続除外
        for pattern in self.config.excluded_patterns:
            try:
                if re.search(pattern, w.title, re.IGNORECASE) or re.search(pattern, w.process_name, re.IGNORECASE):
                    return True
            except re.error:
                if pattern.lower() in w.title.lower() or pattern.lower() in w.process_name.lower():
                    return True
        return False

    def _tick(self):
        """500ms毎に呼ばれるメインループ。"""
        if self._paused:
            return

        import logging
        logger = logging.getLogger("MonitorCleaner")

        try:
            cx, cy = get_cursor_position()
            if cx == -1:
                # デスクトップにアクセスできない (ロック中、UAC画面、スリープ移行中など)
                if not self._locked_logged:
                    logger.info("Desktop side-channel inaccessible (locked or sleep). Suspending checks.")
                    self._locked_logged = True
                return
            
            if self._locked_logged:
                logger.info("Desktop focus restored. Resuming checks.")
                self._locked_logged = False

            monitors = get_monitors()
            now = time.time()
            current_monitor = monitor_from_point(cx, cy, monitors)

            # フォアグラウンドウィンドウの変化も検出 (Alt+Tab対応)
            fg_hwnd = win32gui.GetForegroundWindow()
            fg_monitor_id = None
            if fg_hwnd:
                try:
                    fg_rect = win32gui.GetWindowRect(fg_hwnd)
                    fg_cx = (fg_rect[0] + fg_rect[2]) // 2
                    fg_cy = (fg_rect[1] + fg_rect[3]) // 2
                    fg_mon = monitor_from_point(fg_cx, fg_cy, monitors)
                    if fg_mon:
                        fg_monitor_id = fg_mon.id
                except Exception:
                    pass

            # カーソルのあるモニターのタイマーをリセット
            if current_monitor:
                self._last_active[current_monitor.id] = now

            # Alt+Tabでアクティブになったウィンドウのモニターもリセット
            if fg_monitor_id and fg_monitor_id != (current_monitor.id if current_monitor else None):
                self._last_active[fg_monitor_id] = now

            # 動画検知
            video_hwnds: set[int] = set()
            all_windows = get_visible_windows()
            if self.config.video_detection_enabled:
                video_hwnds = get_video_window_hwnds(
                    all_windows,
                    self.config.video_keywords,
                    fullscreen_only=self.config.video_fullscreen_only,
                )

            # --- グローバル非アクティブ検知 ---
            if self.config.global_inactivity_enabled:
                idle_ms = get_idle_duration_ms()
                idle_seconds = idle_ms / 1000.0
                global_timeout = self.config.global_inactivity_seconds

                if self._global_hidden:
                    # 復元条件: 何かしらの入力があった (idle < 1秒)
                    if idle_seconds < 1.0:
                        self._restore_global(target_hwnd=fg_hwnd if fg_hwnd else None)
                else:
                    # 最小化条件: グローバルタイムアウト超過
                    # グローバルタイムアウトは全てを超越する
                    # (除外設定、動画再生、フルスクリーン表示も全て最小化)
                    if idle_seconds > global_timeout:
                        self._minimize_global(monitors, all_windows)
                        return  # グローバル最小化した場合、モニター別は不要

            # グローバル最小化中は、モニター別の処理をスキップ
            if self._global_hidden:
                return

            # --- モニター別非アクティブ検知 ---
            for mon in monitors:
                mid = mon.id
                if mid not in self._last_active:
                    self._last_active[mid] = now
                    self._is_hidden[mid] = False

                timeout = self.config.get_monitor_timeout(mid)
                elapsed = now - self._last_active.get(mid, now)
                is_current = current_monitor and current_monitor.id == mid
                is_fg = fg_monitor_id == mid

                if self._is_hidden.get(mid, False):
                    # 復元条件: カーソルがこのモニターにいる or Alt+Tabでこのモニターのウィンドウがアクティブ
                    if is_current or is_fg:
                        self._restore_monitor(mid, target_hwnd=fg_hwnd if is_fg else None)
                else:
                    # 最小化条件: タイムアウト超過 & カーソルがこのモニターにいない & Alt+Tabアクティブでない
                    if elapsed > timeout and not is_current and not is_fg:
                        self._minimize_monitor(mon, mid, video_hwnds)

        except Exception as e:
            # スリープ中や画面オフ、セッションロック中などは API 呼び出しが失敗することがある
            # 例外によってループが停止・アプリがクラッシュするのを防ぐため、無視して次回ループへ
            import logging
            logging.getLogger("MonitorCleaner").error(f"_tick encountered exception: {e}", exc_info=True)
            pass

    def _minimize_monitor(self, monitor: MonitorInfo, monitor_id: str, video_hwnds: set[int]):
        """モニター上のウィンドウを最小化する。"""
        import logging
        logger = logging.getLogger("MonitorCleaner")
        all_windows = get_visible_windows()
        windows = get_windows_on_monitor(all_windows, monitor)

        # フルスクリーンウィンドウがこのモニターにある場合、
        # モニター全体の最小化をスキップする。
        # フルスクリーンが画面を完全に覆っているので、裏のウィンドウを
        # 最小化しても見た目に影響がなく、Z-order問題も回避できる。
        for w in windows:
            if is_window_fullscreen(w.hwnd):
                logger.info(f"Monitor {monitor_id} has fullscreen window: {w.title[:40]} - skipping all minimization")
                self._is_hidden[monitor_id] = True
                return

        # 除外対象と動画ウィンドウをフィルタ
        to_minimize: list[WindowInfo] = []
        for w in windows:
            if self._is_excluded(w):
                logger.debug(f"  SKIP excluded: {w.title[:40]}")
                continue
            if w.hwnd in video_hwnds:
                logger.debug(f"  SKIP video: {w.title[:40]}")
                continue
            if is_window_minimized(w.hwnd):
                continue
            to_minimize.append(w)

        if not to_minimize:
            self._is_hidden[monitor_id] = True
            return

        logger.info(f"Minimizing {len(to_minimize)} windows on monitor {monitor_id}: {[w.title[:30] for w in to_minimize]}")

        # Z-order情報を保存
        self._hidden_windows[monitor_id] = to_minimize

        # 最小化実行
        for w in to_minimize:
            minimize_window(w.hwnd)

        self._is_hidden[monitor_id] = True
        self.monitor_state_changed.emit(monitor_id, True)

    def _restore_monitor(self, monitor_id: str, target_hwnd: int | None = None):
        """モニターのウィンドウを復元する。"""
        import logging
        logger = logging.getLogger("MonitorCleaner")

        windows = self._hidden_windows.pop(monitor_id, [])
        if windows:
            restore_windows_with_zorder(windows, target_hwnd=target_hwnd)

        # 復元後、このモニター上の除外/フルスクリーンウィンドウを最前面に再配置
        self._raise_protected_windows(monitor_id, logger)

        self._is_hidden[monitor_id] = False
        self.monitor_state_changed.emit(monitor_id, False)

    def _raise_protected_windows(self, monitor_id: str, logger):
        """モニター上の除外/フルスクリーンウィンドウを最前面に再配置する。"""
        try:
            monitors = get_monitors()
            target_mon = None
            for mon in monitors:
                if mon.id == monitor_id:
                    target_mon = mon
                    break
            if not target_mon:
                return

            all_windows = get_visible_windows()
            mon_windows = get_windows_on_monitor(all_windows, target_mon)

            # 動画検知
            video_hwnds: set[int] = set()
            if self.config.video_detection_enabled:
                from core.media_detector import get_video_window_hwnds
                video_hwnds = get_video_window_hwnds(
                    all_windows,
                    self.config.video_keywords,
                    fullscreen_only=self.config.video_fullscreen_only,
                )

            # 除外/フルスクリーン/動画ウィンドウを収集して最前面に再配置
            # 逆順(下→上)で HWND_TOP に配置して、上にあるべきものが最後に来る
            protected: list[int] = []
            for w in reversed(mon_windows):
                if self._is_excluded(w) or w.hwnd in video_hwnds or is_window_fullscreen(w.hwnd):
                    protected.append(w.hwnd)

            for hwnd in protected:
                try:
                    if win32gui.IsWindow(hwnd) and not is_window_minimized(hwnd):
                        win32gui.SetWindowPos(
                            hwnd,
                            win32con.HWND_TOP,
                            0, 0, 0, 0,
                            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
                        )
                        logger.debug(f"  Raised protected window: hwnd={hwnd}")
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"_raise_protected_windows error: {e}", exc_info=True)

    def _minimize_global(self, monitors: list[MonitorInfo], all_windows: list[WindowInfo]):
        """全モニターのウィンドウを最小化する (グローバル非アクティブ)。
        
        優先順位: フルスクリーン > グローバルタイムアウト > 除外設定・動画再生
        - フルスクリーンウィンドウがあるモニターはスキップ（動画視聴中の可能性）
        - それ以外は除外設定・動画再生に関係なく全ウィンドウを最小化
        """
        import logging
        logger = logging.getLogger("MonitorCleaner")
        self._global_hidden_windows.clear()

        for mon in monitors:
            windows = get_windows_on_monitor(all_windows, mon)

            # フルスクリーンウィンドウがあるモニターはスキップ
            has_fullscreen = any(is_window_fullscreen(w.hwnd) for w in windows)
            if has_fullscreen:
                logger.info(f"Global minimize: skipping monitor {mon.id} (fullscreen detected)")
                continue

            to_minimize: list[WindowInfo] = []
            for w in windows:
                if is_window_minimized(w.hwnd):
                    continue
                to_minimize.append(w)

            if to_minimize:
                logger.info(f"Global minimize: {len(to_minimize)} windows on {mon.id}")
                self._global_hidden_windows[mon.id] = to_minimize
                for w in to_minimize:
                    minimize_window(w.hwnd)
                self._is_hidden[mon.id] = True
                self.monitor_state_changed.emit(mon.id, True)

        self._global_hidden = True

    def _restore_global(self, target_hwnd: int | None = None):
        """グローバル最小化分を全復元する。"""
        import logging
        logger = logging.getLogger("MonitorCleaner")

        for monitor_id, windows in self._global_hidden_windows.items():
            if windows:
                restore_windows_with_zorder(windows, target_hwnd=target_hwnd)
            # 復元後に除外/フルスクリーンウィンドウを再前面化
            self._raise_protected_windows(monitor_id, logger)
            self._is_hidden[monitor_id] = False
            self.monitor_state_changed.emit(monitor_id, False)
        self._global_hidden_windows.clear()
        self._global_hidden = False

    def get_monitor_states(self) -> dict[str, bool]:
        """各モニターの状態を返す (True=最小化中)。"""
        return dict(self._is_hidden)
