import hashlib

class LicenseManager:
    """ライセンス管理クラス
    将来的にGumroad等のAPI連携に差し替えるための基盤。
    """

    @staticmethod
    def verify_key(key: str) -> bool:
        """ライセンスキーを検証する。"""
        if not key:
            return False
        
        key = key.strip()
        # 今回はシンプルなオフライン検証
        # 形式: MCPRO-XXXX-XXXX-XXXX (文字数は適当でOKだが、MCPRO-で始まることとする)
        if key.startswith("MCPRO-") and len(key) >= 10:
            # 簡易チェックサム: 最後の文字が何か、とかでも良いが、今回は Prefix だけでOKとする
            # 本番リリース時には、もう少し複雑なハッシュチェックやAPI通信に差し替えます。
            return True
            
        return False

    @staticmethod
    def get_tier(key: str) -> str:
        """現在のライセンスティアを取得する (Free または Pro)"""
        if LicenseManager.verify_key(key):
            return "Pro"
        return "Free"

    @staticmethod
    def is_pro(key: str) -> bool:
        return LicenseManager.get_tier(key) == "Pro"
