"""ウィンドウ除外ピッカー - 視覚的にウィンドウを選択して除外するUI（チェックボックス方式）

除外の仕組み:
  - 個別ウィンドウ除外: HWND ベース (excluded_hwnds) → セッション中のみ有効
  - プロセス全体除外: プロセス名ベース (excluded_patterns) → 再起動後も永続
  
この2段階設計により:
  - Chrome ウィンドウA/B/C のうち B だけを除外 → HWND で正確に特定 (タイトル変化の影響なし)
  - 「常に Discord を除外したい」→ プロセス名で永続除外
"""
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QGridLayout,
    QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage

from config import Config
from core.window_manager import get_visible_windows, WindowInfo, capture_window_thumbnail


DARK_STYLE = """
QDialog {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Yu Gothic UI", sans-serif;
}
QLabel { color: #cdd6f4; }
QLabel#headerLabel {
    font-size: 18px; font-weight: bold;
    color: #89b4fa; padding: 8px 0;
}
QLabel#subLabel { color: #a6adc8; font-size: 12px; }
QPushButton {
    background-color: #89b4fa; color: #1e1e2e;
    border: none; border-radius: 6px;
    padding: 8px 20px; font-weight: bold; font-size: 13px;
}
QPushButton:hover { background-color: #b4d0fb; }
QPushButton#secondaryBtn { background-color: #45475a; color: #cdd6f4; }
QPushButton#secondaryBtn:hover { background-color: #585b70; }
QScrollArea { border: none; background-color: #1e1e2e; }
QWidget#cardsContainer { background-color: #1e1e2e; }
QCheckBox { spacing: 6px; color: #cdd6f4; font-size: 11px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 3px;
    border: 2px solid #45475a; background-color: #313244;
}
QCheckBox::indicator:checked { background-color: #313244; border-color: #f38ba8; image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZjM4YmE4IiBzdHJva2Utd2lkdGg9IjQiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+"); }
QCheckBox#persistCheck::indicator:checked { background-color: #313244; border-color: #a6e3a1; image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjYTZlM2ExIiBzdHJva2Utd2lkdGg9IjQiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+"); }
"""


class WindowCard(QFrame):
    """1ウィンドウを表すカード。

    除外制御:
      ・「除外 (今回のみ)」: HWND ベース。セッション中有効。タイトル変化の影響なし。
      ・「常に除外」: プロセス名ベース。再起動後も永続。同プロセス全ウィンドウに適用。
    """

    # (hwnd, is_hwnd_excluded, process_name, is_persist_excluded)
    toggled = pyqtSignal(int, bool, str, bool)

    def __init__(
        self,
        window_info: WindowInfo,
        is_hwnd_excluded: bool,
        is_persist_excluded: bool,
        is_pro: bool,
        parent=None,
    ):
        super().__init__(parent)
        self.window_info = window_info
        self._hwnd_exc = is_hwnd_excluded
        self._persist_exc = is_persist_excluded
        self.is_pro = is_pro
        self.setFixedSize(220, 230)
        self.setStyleSheet("""
            WindowCard {
                background-color: #313244;
                border: 2px solid #45475a;
                border-radius: 10px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(3)

        # サムネイル
        thumb = QLabel()
        thumb.setFixedSize(200, 112)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setStyleSheet("background-color: #1e1e2e; border-radius: 5px;")
        data = capture_window_thumbnail(self.window_info.hwnd, 200, 112)
        if data:
            img = QImage()
            img.loadFromData(data)
            thumb.setPixmap(QPixmap.fromImage(img))
        else:
            thumb.setText("📷 プレビュー不可")
            thumb.setStyleSheet(
                "background-color: #1e1e2e; border-radius: 5px; color: #6c7086; font-size: 10px;"
            )
        layout.addWidget(thumb)

        # タイトル
        title = self.window_info.title
        display = title[:25] + "..." if len(title) > 28 else title
        title_lbl = QLabel(display)
        title_lbl.setStyleSheet("font-size: 10px; color: #cdd6f4;")
        title_lbl.setToolTip(title)
        title_lbl.setWordWrap(True)
        title_lbl.setMaximumHeight(26)
        layout.addWidget(title_lbl)

        # プロセス名
        proc_lbl = QLabel(self.window_info.process_name)
        proc_lbl.setStyleSheet("font-size: 9px; color: #6c7086;")
        layout.addWidget(proc_lbl)

        # --- チェックボックス行 1: 今回のみ除外 ---
        self.hwnd_check = QCheckBox("除外 (今回のみ)")
        self.hwnd_check.setChecked(self._hwnd_exc)
        self.hwnd_check.setToolTip(
            "このウィンドウをセッション中のみ除外します。\n"
            "アプリ再起動後はリセットされます。"
        )
        self.hwnd_check.stateChanged.connect(self._on_changed)
        layout.addWidget(self.hwnd_check)

        # --- チェックボックス行 2: 常に除外 (プロセス名) ---
        self.persist_check = QCheckBox("常に除外 (全ウィンドウ)")
        self.persist_check.setObjectName("persistCheck")
        self.persist_check.setChecked(self._persist_exc)
        if not self.is_pro:
            self.persist_check.setEnabled(False)
            self.persist_check.setToolTip("※再起動後も保持される「常に除外」は Pro版限定 です。")
        else:
            self.persist_check.setToolTip(
                f"{self.window_info.process_name} の全ウィンドウを常に除外します。\\n"
                "設定ファイルに保存され、再起動後も有効です。"
            )
        self.persist_check.stateChanged.connect(self._on_changed)
        layout.addWidget(self.persist_check)

    def _on_changed(self):
        self._hwnd_exc = self.hwnd_check.isChecked()
        self._persist_exc = self.persist_check.isChecked()
        self.toggled.emit(
            self.window_info.hwnd,
            self._hwnd_exc,
            self.window_info.process_name,
            self._persist_exc,
        )


class ExclusionPicker(QDialog):
    """ウィンドウ除外ピッカーダイアログ。"""

    exclusion_changed = pyqtSignal()

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Monitor Cleaner - ウィンドウ除外選択")
        self.setMinimumSize(760, 560)
        self.setStyleSheet(DARK_STYLE)
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("🖱 ウィンドウ除外選択")
        header.setObjectName("headerLabel")
        layout.addWidget(header)

        desc = QLabel(
            "「除外 (今回のみ)」: このウィンドウだけをセッション中除外。Chrome 複数ウィンドウも個別に設定可能。\n"
            "「常に除外 (全ウィンドウ)」: 同じアプリの全ウィンドウを再起動後も除外。"
        )
        desc.setObjectName("subLabel")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.cards_container = QWidget()
        self.cards_container.setObjectName("cardsContainer")
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setSpacing(12)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 更新")
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.clicked.connect(self._populate)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addStretch()
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _populate(self):
        """ウィンドウ一覧を取得してカードを配置する。

        除外状態の判定:
          - 「今回のみ」: excluded_hwnds に hwnd が含まれるか
          - 「常に除外」: excluded_patterns にプロセス名が含まれるか
        """
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        all_windows = get_visible_windows()
        excluded_hwnds: set[int] = set(self.config.excluded_hwnds)
        excluded_patterns: list[str] = list(self.config.excluded_patterns)

        my_hwnd = int(self.winId())
        col, row = 0, 0
        cols_per_row = 3

        for winfo in all_windows:
            if winfo.hwnd == my_hwnd:
                continue
            if "Monitor Cleaner" in winfo.title:
                continue

            # HWND ベースの除外状態
            is_hwnd_exc = winfo.hwnd in excluded_hwnds

            # プロセス名ベースの永続除外状態
            is_persist_exc = self._is_process_in_patterns(
                winfo.process_name, excluded_patterns
            )

            card = WindowCard(winfo, is_hwnd_exc, is_persist_exc, self.config.is_pro, self.cards_container)
            card.toggled.connect(self._on_toggle)
            self.cards_layout.addWidget(card, row, col)

            col += 1
            if col >= cols_per_row:
                col = 0
                row += 1

    @staticmethod
    def _is_process_in_patterns(process_name: str, patterns: list[str]) -> bool:
        """プロセス名が excluded_patterns に含まれるか判定。"""
        for pat in patterns:
            try:
                if re.search(pat, process_name, re.IGNORECASE):
                    return True
            except re.error:
                if pat.lower() in process_name.lower():
                    return True
        return False

    def _on_toggle(
        self,
        hwnd: int,
        is_hwnd_excluded: bool,
        process_name: str,
        is_persist_excluded: bool,
    ):
        """カードのチェック変更時に呼ばれる。HWND と プロセス名 を独立して管理する。"""
        # --- 1. HWND ベース (セッション中のみ) ---
        if is_hwnd_excluded:
            if not self.config.is_pro and len(self.config.excluded_hwnds) >= 1:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Pro版限定機能", "無料版では「今回のみ除外」できるウィンドウは1つまでです。")
                self._populate()
                return
            self.config.add_excluded_hwnd(hwnd)
        else:
            self.config.remove_excluded_hwnd(hwnd)

        # --- 2. プロセス名ベース (永続) ---
        patterns = list(self.config.excluded_patterns)
        already_in_patterns = self._is_process_in_patterns(process_name, patterns)

        if is_persist_excluded and not already_in_patterns:
            patterns.append(process_name)
            self.config.excluded_patterns = patterns  # save() が呼ばれる
        elif not is_persist_excluded and already_in_patterns:
            # プロセス名と完全一致するエントリのみ削除
            patterns = [p for p in patterns if p.lower() != process_name.lower()]
            self.config.excluded_patterns = patterns  # save() が呼ばれる

        self.exclusion_changed.emit()
