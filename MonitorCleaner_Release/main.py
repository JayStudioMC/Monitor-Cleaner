"""Monitor Cleaner - メインエントリポイント

デュアルモニター環境で非アクティブなモニターのウィンドウを自動最小化し、
壁紙を表示するWindows 11デスクトップユーティリティ。
"""

import sys
import os
import ctypes

# アプリのルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSharedMemory

from config import Config
from core.inactivity import InactivityManager
from ui.tray import TrayIcon
from ui.settings_dialog import SettingsDialog
from ui.exclusion_picker import ExclusionPicker


class MonitorCleanerApp:
    """アプリケーションメインクラス。"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)  # トレイ常駐のため

        # 多重起動防止
        self.shared_memory = QSharedMemory("MonitorCleaner_SingleInstance")
        if not self.shared_memory.create(1):
            if self.shared_memory.error() != QSharedMemory.SharedMemoryError.NoError:
                # 既に起動中
                ctypes.windll.user32.MessageBoxW(
                    0,
                    "Monitor Cleaner は既に起動中です。\nシステムトレイを確認してください。",
                    "Monitor Cleaner",
                    0x40  # MB_ICONINFORMATION
                )
                sys.exit(0)

        # 設定
        self.config = Config()
        # ... (以下略、コンストラクタの残りは維持)
        # 非アクティブマネージャー
        self.inactivity = InactivityManager(self.config)

        # アプリ全体にアイコンを適用
        try:
            from ui.tray import get_app_icon
            self.app.setWindowIcon(get_app_icon())
        except Exception:
            pass

        # システムトレイ
        self.tray = TrayIcon(self.config)
        self.tray.show_settings.connect(self._show_settings)
        self.tray.show_exclusion_picker.connect(self._show_exclusion_picker)
        self.tray.toggle_pause.connect(self._toggle_pause)
        self.tray.quit_app.connect(self._quit)
        self.tray.restore_all.connect(self._restore_all)
        self.tray.show()

        # モニター状態変更シグナル
        self.inactivity.monitor_state_changed.connect(
            self.tray.update_monitor_state
        )

        # ダイアログ参照
        self._settings_dialog = None
        self._exclusion_picker = None

        # 開始
        self.inactivity.start()

    def _show_settings(self):
        if self._settings_dialog and self._settings_dialog.isVisible():
            self._settings_dialog.activateWindow()
            return
        self._settings_dialog = SettingsDialog(self.config)
        self._settings_dialog.settings_changed.connect(self._on_settings_changed)
        self._settings_dialog.show()

    def _show_exclusion_picker(self):
        if self._exclusion_picker and self._exclusion_picker.isVisible():
            self._exclusion_picker.activateWindow()
            return
        self._exclusion_picker = ExclusionPicker(self.config)
        self._exclusion_picker.show()

    def _toggle_pause(self):
        if self.inactivity.is_paused:
            self.inactivity.resume()
        else:
            self.inactivity.pause()

    def _restore_all(self):
        self.inactivity.restore_all()

    def _on_settings_changed(self):
        pass

    def _quit(self):
        self.inactivity.stop()
        self.tray.hide()
        self.app.quit()

    def run(self) -> int:
        return self.app.exec()


import logging
from pathlib import Path

def setup_logging():
    """ロギングの設定。ファイルがロックされている場合は標準出力のみにする。"""
    appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    log_dir = Path(appdata) / "MonitorCleaner"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "monitor_cleaner.log"

    handlers: list[logging.Handler] = []
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file, encoding='utf-8',
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        handlers.append(file_handler)
    except Exception:
        pass

    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))

    if not handlers:
        handlers.append(logging.NullHandler())

    logging.basicConfig(
        level=logging.INFO,  # 発売版: INFO のみ (DEBUG は除外)
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=handlers
    )
    return logging.getLogger("MonitorCleaner")


# グローバルな未捕捉例外のハンドラ
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.getLogger("MonitorCleaner").critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

from PyQt6.QtCore import qInstallMessageHandler

def _qt_message_handler(mode, context, message):
    logger = logging.getLogger("MonitorCleaner")
    if mode == 0: logger.debug(f"QtDebug: {message}")
    elif mode == 1: logger.warning(f"QtWarning: {message}")
    elif mode == 2: logger.critical(f"QtCritical: {message}")
    elif mode == 3: logger.fatal(f"QtFatal: {message}")
    elif mode == 4: logger.info(f"QtInfo: {message}")

def main():
    # ロギング開始
    logger = setup_logging()
    logger.info("--- Monitor Cleaner Starting ---")
    
    qInstallMessageHandler(_qt_message_handler)

    try:
        app = MonitorCleanerApp()
        exit_code = app.run()
        logger.info(f"--- Monitor Cleaner Exited Normally (code {exit_code}) ---")
        sys.exit(exit_code)
    except Exception as e:
        logger.exception(f"Fatal error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
