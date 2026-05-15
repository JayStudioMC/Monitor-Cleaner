"""設定管理モジュール - %APPDATA%/MonitorCleaner/settings.json に永続化"""

import json
import os
from pathlib import Path


DEFAULT_SETTINGS = {
    "timeout_seconds": 30,
    "per_monitor_timeout": {},  # monitor_id -> seconds
    "auto_start": False,
    "video_detection_enabled": True,
    "video_fullscreen_only": False,   # True: フルスクリーン時のみ動画除外
    "video_keywords": [
        "YouTube", "Netflix", "Amazon Prime Video", "Disney+",
        "Twitch", "TVer", "ABEMA", "U-NEXT", "Hulu",
        "NHK", "DAZN", "Crunchyroll", "Paramount+",
        "ニコニコ動画", "ニコニコ生放送",
    ],
    "excluded_patterns": [],  # タイトルパターンによる永続除外
    "excluded_hwnds": [],     # セッション中のみ有効 (保存しない)
    "global_inactivity_enabled": True,
    "global_inactivity_seconds": 300,  # デフォルト 5分
    "license_key": "",         # Pro版ライセンスキー
}

# 保存しないキー
_TRANSIENT_KEYS = {"excluded_hwnds"}


def _settings_path() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    folder = Path(appdata) / "MonitorCleaner"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "settings.json"


class Config:
    """アプリケーション設定の管理クラス。変更時に自動保存する。"""

    def __init__(self):
        self._data: dict = {}
        self.load()

    def load(self):
        path = _settings_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # デフォルト値をベースにマージ
                self._data = {**DEFAULT_SETTINGS, **saved}
            except (json.JSONDecodeError, OSError):
                self._data = dict(DEFAULT_SETTINGS)
        else:
            self._data = dict(DEFAULT_SETTINGS)
        # Transient keys are always reset
        for k in _TRANSIENT_KEYS:
            self._data[k] = DEFAULT_SETTINGS.get(k, [])

    def save(self):
        path = _settings_path()
        to_save = {k: v for k, v in self._data.items() if k not in _TRANSIENT_KEYS}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)

    # --- Accessors ---
    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    @property
    def timeout_seconds(self) -> int:
        return self._data.get("timeout_seconds", 30)

    @timeout_seconds.setter
    def timeout_seconds(self, val: int):
        self._data["timeout_seconds"] = val
        self.save()

    def get_monitor_timeout(self, monitor_id: str) -> int:
        """モニター別タイムアウト。未設定ならデフォルト値を返す。"""
        return self._data.get("per_monitor_timeout", {}).get(
            monitor_id, self.timeout_seconds
        )

    def set_monitor_timeout(self, monitor_id: str, seconds: int):
        if "per_monitor_timeout" not in self._data:
            self._data["per_monitor_timeout"] = {}
        self._data["per_monitor_timeout"][monitor_id] = seconds
        self.save()

    @property
    def auto_start(self) -> bool:
        return self._data.get("auto_start", False)

    @auto_start.setter
    def auto_start(self, val: bool):
        self._data["auto_start"] = val
        self.save()

    @property
    def video_detection_enabled(self) -> bool:
        return self._data.get("video_detection_enabled", True)

    @video_detection_enabled.setter
    def video_detection_enabled(self, val: bool):
        self._data["video_detection_enabled"] = val
        self.save()

    @property
    def video_fullscreen_only(self) -> bool:
        return self._data.get("video_fullscreen_only", False)

    @video_fullscreen_only.setter
    def video_fullscreen_only(self, val: bool):
        self._data["video_fullscreen_only"] = val
        self.save()

    @property
    def video_keywords(self) -> list[str]:
        return self._data.get("video_keywords", [])

    @video_keywords.setter
    def video_keywords(self, val: list[str]):
        self._data["video_keywords"] = val
        self.save()

    @property
    def excluded_patterns(self) -> list[str]:
        return self._data.get("excluded_patterns", [])

    @excluded_patterns.setter
    def excluded_patterns(self, val: list[str]):
        self._data["excluded_patterns"] = val
        self.save()

    @property
    def excluded_hwnds(self) -> list[int]:
        return self._data.get("excluded_hwnds", [])

    @excluded_hwnds.setter
    def excluded_hwnds(self, val: list[int]):
        self._data["excluded_hwnds"] = val
        # Transient, don't save to disk

    def add_excluded_hwnd(self, hwnd: int):
        hwnds = self.excluded_hwnds
        if hwnd not in hwnds:
            hwnds.append(hwnd)
            self._data["excluded_hwnds"] = hwnds

    def remove_excluded_hwnd(self, hwnd: int):
        hwnds = self.excluded_hwnds
        if hwnd in hwnds:
            hwnds.remove(hwnd)
            self._data["excluded_hwnds"] = hwnds

    @property
    def global_inactivity_enabled(self) -> bool:
        return self._data.get("global_inactivity_enabled", True)

    @global_inactivity_enabled.setter
    def global_inactivity_enabled(self, val: bool):
        self._data["global_inactivity_enabled"] = val
        self.save()

    @property
    def global_inactivity_seconds(self) -> int:
        return self._data.get("global_inactivity_seconds", 300)

    @global_inactivity_seconds.setter
    def global_inactivity_seconds(self, val: int):
        self._data["global_inactivity_seconds"] = val
        self.save()

    @property
    def license_key(self) -> str:
        return self._data.get("license_key", "")

    @license_key.setter
    def license_key(self, val: str):
        self._data["license_key"] = val
        self.save()

    @property
    def is_pro(self) -> bool:
        from core.license import LicenseManager
        return LicenseManager.is_pro(self.license_key)
