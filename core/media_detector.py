"""動画再生検知モジュール - ウィンドウタイトルとフルスクリーン状態による検知"""

from core.window_manager import WindowInfo, is_window_fullscreen


def is_video_window(
    window: WindowInfo,
    keywords: list[str],
    fullscreen_only: bool = False,
) -> bool:
    """ウィンドウが動画再生中かどうかを判定する。

    Args:
        window: 判定対象のウィンドウ
        keywords: 動画サービスのキーワードリスト (例: ["YouTube", "Netflix"])
        fullscreen_only: True の場合、フルスクリーン時のみ除外対象とする

    タイトル判定例:
        "動画タイトル - YouTube - Google Chrome"
        "映画タイトル | Netflix"

    fullscreen_only=True の場合:
        ブラウザが F11 でフルスクリーンになっているときのみ除外される。
        通常ウィンドウで YouTube を開いていても除外されない。
    """
    title_lower = window.title.lower()
    keyword_matched = any(kw.lower() in title_lower for kw in keywords)

    if not keyword_matched:
        return False

    if fullscreen_only:
        return is_window_fullscreen(window.hwnd)

    return True


def get_video_windows(
    windows: list[WindowInfo],
    keywords: list[str],
    fullscreen_only: bool = False,
) -> list[WindowInfo]:
    """動画再生中のウィンドウを全て返す。"""
    return [w for w in windows if is_video_window(w, keywords, fullscreen_only)]


def get_video_window_hwnds(
    windows: list[WindowInfo],
    keywords: list[str],
    fullscreen_only: bool = False,
) -> set[int]:
    """動画再生中のウィンドウのhwndセットを返す。"""
    return {w.hwnd for w in windows if is_video_window(w, keywords, fullscreen_only)}
