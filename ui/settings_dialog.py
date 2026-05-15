"""設定ダイアログ - モダンなダークテーマUI"""

import sys
import os
import winreg
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QCheckBox, QPushButton, QGroupBox, QFormLayout, QScrollArea,
    QWidget, QLineEdit, QListWidget, QListWidgetItem, QTabWidget,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from config import Config
from core.monitor import get_monitors

def get_asset_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'ui', filename).replace('\\', '/')
    return os.path.abspath(os.path.join(os.path.dirname(__file__), filename)).replace('\\', '/')

UI_CHECK = get_asset_path("check.svg")
UI_UP = get_asset_path("up.svg")
UI_DOWN = get_asset_path("down.svg")

# ダークテーマスタイルシート
DARK_STYLE = f"""
QDialog, QWidget {{
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Yu Gothic UI", sans-serif;
    font-size: 13px;
}}
QGroupBox {{
    border: 1px solid #45475a;
    border-radius: 8px;
    margin-top: 16px;
    padding: 16px;
    padding-top: 28px;
    font-weight: bold;
    color: #89b4fa;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    background-color: #313244;
    border-radius: 4px;
}}
QSpinBox {{
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 12px;
    color: #cdd6f4;
    min-width: 80px;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: #45475a;
    border-radius: 3px;
    width: 20px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: #585b70;
}}
QSpinBox::up-arrow {{
    image: url("{UI_UP}");
    width: 12px; height: 12px;
}}
QSpinBox::down-arrow {{
    image: url("{UI_DOWN}");
    width: 12px; height: 12px;
}}
QCheckBox {{
    spacing: 8px;
    color: #cdd6f4;
}}
QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid #45475a;
    background-color: #313244;
}}
QCheckBox::indicator:checked {{
    background-color: #313244;
    border-color: #89b4fa;
    image: url("{UI_CHECK}");
}}
QPushButton {{
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: #b4d0fb;
}}
QPushButton:pressed {{
    background-color: #74a8f7;
}}
QPushButton#dangerBtn {{
    background-color: #f38ba8;
}}
QPushButton#dangerBtn:hover {{
    background-color: #f5a0b8;
}}
QPushButton#secondaryBtn {{
    background-color: #45475a;
    color: #cdd6f4;
}}
QPushButton#secondaryBtn:hover {{
    background-color: #585b70;
}}
QTabWidget::pane {{
    border: 1px solid #45475a;
    border-radius: 8px;
    background-color: #1e1e2e;
    top: -1px;
}}
QTabBar::tab {{
    background-color: #313244;
    color: #a6adc8;
    padding: 10px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: #1e1e2e;
    color: #89b4fa;
    border-bottom: 2px solid #89b4fa;
}}
QTabBar::tab:hover {{
    background-color: #45475a;
}}
QListWidget {{
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px;
    color: #cdd6f4;
}}
QListWidget::item {{
    padding: 6px;
    border-radius: 4px;
}}
QListWidget::item:selected {{
    background-color: #45475a;
}}
QLineEdit {{
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 8px;
    color: #cdd6f4;
}}
QLineEdit:focus {{
    border-color: #89b4fa;
}}
QScrollArea {{
    border: none;
}}
QLabel#headerLabel {{
    font-size: 18px;
    font-weight: bold;
    color: #89b4fa;
    padding: 8px 0;
}}
QLabel#subLabel {{
    color: #a6adc8;
    font-size: 12px;
}}
"""





class SettingsDialog(QDialog):
    """設定ダイアログ。"""

    settings_changed = pyqtSignal()

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Monitor Cleaner - 設定")
        self.setMinimumSize(520, 580)
        self.setStyleSheet(DARK_STYLE)
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # ヘッダー
        header = QLabel("⚙ Monitor Cleaner 設定")
        header.setObjectName("headerLabel")
        layout.addWidget(header)

        # タブウィジェット
        tabs = QTabWidget()
        layout.addWidget(tabs)
        self.tabs = tabs

        is_pro = self.config.is_pro

        # --- 一般タブ ---
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_layout.setSpacing(12)

        # タイムアウト設定
        timeout_group = QGroupBox("⏱ モニター別タイムアウト")
        timeout_form = QFormLayout()
        timeout_form.setSpacing(10)

        timeout_desc = QLabel("カーソルが離れてからそのモニターのウィンドウを\n最小化するまでの時間です。")
        timeout_desc.setObjectName("subLabel")
        timeout_desc.setWordWrap(True)
        timeout_form.addRow(timeout_desc)

        self.default_timeout_spin = QSpinBox()
        self.default_timeout_spin.setRange(5, 3600)
        self.default_timeout_spin.setSuffix(" 秒")
        timeout_form.addRow("デフォルト (全モニター共通):", self.default_timeout_spin)

        # モニター別設定
        self.monitor_spins: dict[str, QSpinBox] = {}
        monitors = get_monitors()
        for i, mon in enumerate(monitors):
            spin = QSpinBox()
            spin.setRange(5, 3600)
            spin.setSuffix(" 秒")
            label = f"モニター {i + 1}"
            if mon.is_primary:
                label += " (プライマリ)"
            label += f" [{mon.width}x{mon.height}]"
            timeout_form.addRow(label + ":", spin)
            self.monitor_spins[mon.id] = spin

        timeout_group.setLayout(timeout_form)
        
        # Pro制限
        if not is_pro:
            pro_label = QLabel("※モニター別設定は Pro版限定 です")
            pro_label.setStyleSheet("color: #f9e2af;")
            timeout_form.addRow(pro_label)
            for spin in self.monitor_spins.values():
                spin.setEnabled(False)
                
        general_layout.addWidget(timeout_group)

        # グローバル非アクティブ設定
        global_group = QGroupBox("💤 全体非アクティブ設定")
        global_layout = QVBoxLayout()

        global_desc = QLabel("マウス・キーボード等、あらゆる入力が一定時間ない場合に\n全モニターのウィンドウを最小化します。\n動画再生中はスキップされます。")
        global_desc.setObjectName("subLabel")
        global_desc.setWordWrap(True)
        global_layout.addWidget(global_desc)

        self.global_inactivity_check = QCheckBox("全体非アクティブ検知を有効にする")
        global_layout.addWidget(self.global_inactivity_check)

        global_form = QFormLayout()
        self.global_timeout_spin = QSpinBox()
        self.global_timeout_spin.setRange(10, 7200)
        self.global_timeout_spin.setSuffix(" 秒")
        global_form.addRow("全体非アクティブ タイムアウト:", self.global_timeout_spin)
        global_layout.addLayout(global_form)

        if not is_pro:
            pro_label2 = QLabel("※全体非アクティブ検知は Pro版限定 です")
            pro_label2.setStyleSheet("color: #f9e2af;")
            global_layout.addWidget(pro_label2)
            self.global_inactivity_check.setEnabled(False)
            self.global_timeout_spin.setEnabled(False)

        global_group.setLayout(global_layout)
        general_layout.addWidget(global_group)

        # 起動設定
        startup_group = QGroupBox("🚀 起動設定")
        startup_layout = QVBoxLayout()

        self.auto_start_check = QCheckBox("PC起動時に自動で起動する")
        startup_layout.addWidget(self.auto_start_check)

        startup_note = QLabel("※ Windowsのスタートアップに登録されます")
        startup_note.setObjectName("subLabel")
        startup_layout.addWidget(startup_note)

        startup_group.setLayout(startup_layout)
        general_layout.addWidget(startup_group)

        general_layout.addStretch()
        tabs.addTab(general_tab, "一般")

        # --- 動画検知タブ ---
        video_tab = QWidget()
        video_layout = QVBoxLayout(video_tab)
        video_layout.setSpacing(12)

        video_group = QGroupBox("🎬 動画再生検知")
        video_grp_layout = QVBoxLayout()

        self.video_detection_check = QCheckBox("動画再生中のウィンドウを自動除外する")
        video_grp_layout.addWidget(self.video_detection_check)

        self.video_fullscreen_only_check = QCheckBox("フルスクリーン時のみ除外する")
        self.video_fullscreen_only_check.setToolTip(
            "チェックを入れると、ブラウザが F11 でフルスクリーンになっているときだけ\n"
            "動画ウィンドウが除外されます。通常ウィンドウで YouTube を開いていても\n"
            "フルスクリーンでなければ最小化対象になります。"
        )
        video_grp_layout.addWidget(self.video_fullscreen_only_check)

        desc = QLabel("ウィンドウタイトルに下記キーワードが含まれる場合、\nそのウィンドウは最小化されません。")
        desc.setObjectName("subLabel")
        desc.setWordWrap(True)
        video_grp_layout.addWidget(desc)

        self.keyword_list = QListWidget()
        self.keyword_list.setMaximumHeight(200)
        video_grp_layout.addWidget(self.keyword_list)

        kw_btn_layout = QHBoxLayout()
        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText("キーワードを入力...")
        kw_btn_layout.addWidget(self.kw_input)

        add_kw_btn = QPushButton("追加")
        add_kw_btn.clicked.connect(self._add_keyword)
        kw_btn_layout.addWidget(add_kw_btn)

        del_kw_btn = QPushButton("削除")
        del_kw_btn.setObjectName("dangerBtn")
        del_kw_btn.clicked.connect(self._remove_keyword)
        kw_btn_layout.addWidget(del_kw_btn)

        video_grp_layout.addLayout(kw_btn_layout)
        video_group.setLayout(video_grp_layout)
        video_layout.addWidget(video_group)

        video_layout.addStretch()
        tabs.addTab(video_tab, "動画検知")
        
        if not is_pro:
            video_tab.setEnabled(False)
            tabs.setTabToolTip(tabs.count() - 1, "Pro版限定機能です")
            pro_label_video = QLabel("※動画検知機能は Pro版限定 です。\nライセンスタブからアンロックしてください。")
            pro_label_video.setStyleSheet("color: #f9e2af; font-weight: bold; margin-bottom: 10px;")
            video_layout.insertWidget(0, pro_label_video)

        # --- 除外パターンタブ ---
        exclude_tab = QWidget()
        exclude_layout = QVBoxLayout(exclude_tab)
        exclude_layout.setSpacing(12)

        pattern_group = QGroupBox("📋 除外パターン（タイトルマッチ）")
        pattern_grp_layout = QVBoxLayout()

        pattern_desc = QLabel("ウィンドウタイトルに下記の文字列が含まれる場合、\nそのウィンドウは最小化されません。再起動後も保持されます。")
        pattern_desc.setObjectName("subLabel")
        pattern_desc.setWordWrap(True)
        pattern_grp_layout.addWidget(pattern_desc)

        self.pattern_list = QListWidget()
        self.pattern_list.setMaximumHeight(200)
        pattern_grp_layout.addWidget(self.pattern_list)

        pat_btn_layout = QHBoxLayout()
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("除外パターンを入力...")
        pat_btn_layout.addWidget(self.pattern_input)

        add_pat_btn = QPushButton("追加")
        add_pat_btn.clicked.connect(self._add_pattern)
        pat_btn_layout.addWidget(add_pat_btn)

        del_pat_btn = QPushButton("削除")
        del_pat_btn.setObjectName("dangerBtn")
        del_pat_btn.clicked.connect(self._remove_pattern)
        pat_btn_layout.addWidget(del_pat_btn)

        pattern_grp_layout.addLayout(pat_btn_layout)
        pattern_group.setLayout(pattern_grp_layout)
        exclude_layout.addWidget(pattern_group)

        exclude_layout.addStretch()
        tabs.addTab(exclude_tab, "除外パターン")
        
        if not is_pro:
            exclude_tab.setEnabled(False)
            tabs.setTabToolTip(tabs.count() - 1, "Pro版限定機能です")
            pro_label_pattern = QLabel("※除外パターン設定は Pro版限定 です。\nライセンスタブからアンロックしてください。")
            pro_label_pattern.setStyleSheet("color: #f9e2af; font-weight: bold; margin-bottom: 10px;")
            exclude_layout.insertWidget(0, pro_label_pattern)

        # --- ライセンスタブ ---
        license_tab = QWidget()
        license_layout = QVBoxLayout(license_tab)
        license_layout.setSpacing(12)

        license_group = QGroupBox("🔑 ライセンス認証")
        license_grp_layout = QVBoxLayout()

        license_desc = QLabel("ライセンスキーを入力して Pro版 機能をアンロックします。\n"
                              "Pro版ではモニター別の個別設定や、動画検知機能が利用可能になります。")
        license_desc.setObjectName("subLabel")
        license_desc.setWordWrap(True)
        license_grp_layout.addWidget(license_desc)

        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("MCPRO-XXXX-XXXX-XXXX")
        license_grp_layout.addWidget(self.license_input)

        status_layout = QHBoxLayout()
        self.license_status_label = QLabel()
        self.license_status_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.update_license_status()
        status_layout.addWidget(self.license_status_label)
        status_layout.addStretch()
        
        # Verify button will be handled via save but we can add a visual indicator
        
        license_grp_layout.addLayout(status_layout)
        license_group.setLayout(license_grp_layout)
        license_layout.addWidget(license_group)
        license_layout.addStretch()
        
        tabs.addTab(license_tab, "ライセンス")

        # 保存/閉じるボタン
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton("閉じる")
        close_btn.setObjectName("secondaryBtn")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_values(self):
        self.default_timeout_spin.setValue(self.config.timeout_seconds)
        for mid, spin in self.monitor_spins.items():
            spin.setValue(self.config.get_monitor_timeout(mid))
        self.auto_start_check.setChecked(self.config.auto_start)
        self.video_detection_check.setChecked(self.config.video_detection_enabled)
        self.video_fullscreen_only_check.setChecked(self.config.video_fullscreen_only)
        self.global_inactivity_check.setChecked(self.config.global_inactivity_enabled)
        self.global_timeout_spin.setValue(self.config.global_inactivity_seconds)

        self.keyword_list.clear()
        for kw in self.config.video_keywords:
            self.keyword_list.addItem(kw)

        self.pattern_list.clear()
        for pat in self.config.excluded_patterns:
            self.pattern_list.addItem(pat)
            
        self.license_input.setText(self.config.license_key)
        
    def update_license_status(self):
        if self.config.is_pro:
            self.license_status_label.setText("現在の状態: Pro版 (認証済み)")
            self.license_status_label.setStyleSheet("color: #a6e3a1;")
        else:
            self.license_status_label.setText("現在の状態: 無料版")
            self.license_status_label.setStyleSheet("color: #bac2de;")

    def _save(self):
        self.config.timeout_seconds = self.default_timeout_spin.value()
        for mid, spin in self.monitor_spins.items():
            self.config.set_monitor_timeout(mid, spin.value())

        new_auto_start = self.auto_start_check.isChecked()
        if new_auto_start != self.config.auto_start:
            self.config.auto_start = new_auto_start
            self._set_auto_start(new_auto_start)

        self.config.video_detection_enabled = self.video_detection_check.isChecked()
        self.config.video_fullscreen_only = self.video_fullscreen_only_check.isChecked()
        self.config.global_inactivity_enabled = self.global_inactivity_check.isChecked()
        self.config.global_inactivity_seconds = self.global_timeout_spin.value()

        keywords = []
        for i in range(self.keyword_list.count()):
            keywords.append(self.keyword_list.item(i).text())
        self.config.video_keywords = keywords

        patterns = []
        for i in range(self.pattern_list.count()):
            patterns.append(self.pattern_list.item(i).text())
        self.config.excluded_patterns = patterns
        
        old_is_pro = self.config.is_pro
        self.config.license_key = self.license_input.text().strip()
        new_is_pro = self.config.is_pro
        
        if old_is_pro != new_is_pro:
            if new_is_pro:
                QMessageBox.information(self, "ライセンス", "Pro版の認証に成功しました！\n全機能が利用可能です。")
            else:
                QMessageBox.information(self, "ライセンス", "無料版に戻りました。")

        self.settings_changed.emit()
        self.close()

    def _add_keyword(self):
        text = self.kw_input.text().strip()
        if text:
            self.keyword_list.addItem(text)
            self.kw_input.clear()

    def _remove_keyword(self):
        for item in self.keyword_list.selectedItems():
            self.keyword_list.takeItem(self.keyword_list.row(item))

    def _add_pattern(self):
        text = self.pattern_input.text().strip()
        if text:
            self.pattern_list.addItem(text)
            self.pattern_input.clear()

    def _remove_pattern(self):
        for item in self.pattern_list.selectedItems():
            self.pattern_list.takeItem(self.pattern_list.row(item))

    def _set_auto_start(self, enabled: bool):
        """レジストリでスタートアップ登録/解除する。"""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "MonitorCleaner"
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
            )
            if enabled:
                # 実行ファイルのパスを取得
                import sys
                exe_path = sys.executable
                if exe_path.endswith("python.exe") or exe_path.endswith("pythonw.exe"):
                    # 開発中: pythonw.exe + スクリプトのパスを登録
                    import os
                    script_path = os.path.abspath(
                        os.path.join(os.path.dirname(__file__), "..", "main.py")
                    )
                    exe_path = f'"{sys.executable}" "{script_path}"'
                else:
                    exe_path = f'"{exe_path}"'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            QMessageBox.warning(
                self, "エラー",
                f"スタートアップ設定の変更に失敗しました:\n{e}"
            )
