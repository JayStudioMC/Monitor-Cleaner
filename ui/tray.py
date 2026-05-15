"""システムトレイアイコン"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import pyqtSignal

from config import Config


import os
import sys

def get_app_icon() -> QIcon:
    """アプリのアイコンを取得する。icon.ico があればそれを、なければ生成する。"""
    if getattr(sys, 'frozen', False):
        # PyInstallerでビルドされた場合
        base_path = sys._MEIPASS
    else:
        # 通常のスクリプト実行の場合
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    icon_path = os.path.join(base_path, "icon.ico")
    if os.path.exists(icon_path):
        return QIcon(icon_path)

    # デフォルトのトレイアイコンをプログラム的に生成する。
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 背景円
    painter.setBrush(QColor("#89b4fa"))
    painter.setPen(QColor("#89b4fa"))
    painter.drawEllipse(2, 2, size - 4, size - 4)

    # "MC" テキスト
    painter.setPen(QColor("#1e1e2e"))
    font = QFont("Segoe UI", 20, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), 0x0084, "MC")  # AlignCenter

    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    """システムトレイアイコン。"""

    show_settings = pyqtSignal()
    show_exclusion_picker = pyqtSignal()
    toggle_pause = pyqtSignal()
    quit_app = pyqtSignal()
    restore_all = pyqtSignal()

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self._is_paused = False
        self.setIcon(get_app_icon())
        self.setToolTip("Monitor Cleaner - 動作中")
        self._build_menu()
        self.activated.connect(self._on_activated)

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 4px;
                font-family: "Segoe UI", "Yu Gothic UI", sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #45475a;
            }
            QMenu::separator {
                height: 1px;
                background-color: #45475a;
                margin: 4px 8px;
            }
        """)

        # 状態表示
        self.status_action = QAction("✅ 動作中", self)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)

        menu.addSeparator()

        # 一時停止/再開
        self.pause_action = QAction("⏸ 一時停止", self)
        self.pause_action.triggered.connect(self._toggle_pause)
        menu.addAction(self.pause_action)

        # 全復元
        restore_action = QAction("📺 全ウィンドウ復元", self)
        restore_action.triggered.connect(self.restore_all.emit)
        menu.addAction(restore_action)

        menu.addSeparator()

        # ウィンドウ除外
        exclusion_action = QAction("🖱 ウィンドウ除外選択...", self)
        exclusion_action.triggered.connect(self.show_exclusion_picker.emit)
        menu.addAction(exclusion_action)

        # 設定
        settings_action = QAction("⚙ 設定...", self)
        settings_action.triggered.connect(self.show_settings.emit)
        menu.addAction(settings_action)

        menu.addSeparator()

        # 終了
        quit_action = QAction("❌ 終了", self)
        quit_action.triggered.connect(self._on_quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_settings.emit()

    def _toggle_pause(self):
        self._is_paused = not self._is_paused
        if self._is_paused:
            self.pause_action.setText("▶ 再開")
            self.status_action.setText("⏸ 一時停止中")
            self.setToolTip("Monitor Cleaner - 一時停止中")
        else:
            self.pause_action.setText("⏸ 一時停止")
            self.status_action.setText("✅ 動作中")
            self.setToolTip("Monitor Cleaner - 動作中")
        self.toggle_pause.emit()

    def _on_quit(self):
        self.quit_app.emit()

    def update_monitor_state(self, monitor_id: str, is_hidden: bool):
        """モニター状態変化時のツールチップ更新。"""
        if self._is_paused:
            return
        # ツールチップを更新
        self.setToolTip(f"Monitor Cleaner - 動作中")
