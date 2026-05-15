# Monitor Cleaner

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/JayStudioMC/Monitor-Cleaner/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)]()

> **あなたのデスクトップが、きれいに。**

Monitor Cleanerは、マルチモニター環境での作業をより快適にするための自動ウィンドウ管理ツールです。

---

## 主な機能

- **スタイリッシュな自動最小化**
  モニターからマウスが離れると、そのモニターにあるウィンドウを自動的に最小化。常にクリーンなデスクトップを保ちます。
- **便利な除外機能**
  作業中の資料や動画再生ウィンドウなど、最小化されたくないアプリを簡単に除外設定可能。
- **スマート操作検知 (Pro)**
  PCから離れた際の全モニター一括クリーンアップや、動画再生中の自動保留など、より高度な自動化を提供します。

## Free vs Pro

| 機能 | Free | Pro |
| :--- | :---: | :---: |
| 自動最小化 (基本) | YES | YES |
| デフォルト秒数設定 | YES | YES |
| ウィンドウ一時除外 | 1つまで | 無制限 |
| モニター別個別設定 | NO | YES |
| 全体非アクティブ検知 | NO | YES |
| 動画再生検知（自動保留） | NO | YES |
| 除外パターンの保存 | NO | YES |

---

## はじめかた

### 1. ダウンロード
[Releases](https://github.com/JayStudioMC/Monitor-Cleaner/releases) ページから最新の MonitorCleaner_Setup.exe をダウンロードしてください。

### 2. インストール
ダウンロードした実行ファイルをダブルクリックし、画面の指示に従ってインストールを完了させてください。

### 3. ライセンスの有効化 (Pro版)
[BOOTH販売ページ](https://your-booth-url.booth.pm) でライセンスキーを購入し、アプリの設定画面「ライセンス」タブに入力してください。

---

## 開発者向け

このプロジェクトは Python と PyQt6 で構築されています。

```bash
# クローン
git clone https://github.com/JayStudioMC/Monitor-Cleaner.git

# 依存関係のインストール
pip install -r requirements.txt

# 実行
python main.py
```

## ライセンス

このソフトウェアは MIT ライセンスの下で公開されています。

---

**Official Website:** [https://JayStudioMC.github.io/Monitor-Cleaner/](https://JayStudioMC.github.io/Monitor-Cleaner/)
