import hashlib
import secrets

class PasswordHasher:
    """비밀번호 해시 관리 클래스"""
    
    @staticmethod
    def hash_password(password):
        """비밀번호를 SHA256으로 해시"""
        # 솔트 생성 (32바이트)
        salt = secrets.token_hex(32)
        # 비밀번호 + 솔트를 해시
        password_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        # 솔트와 해시를 함께 저장 (솔트:해시 형식)
        return f"{salt}:{password_hash}"
    
    @staticmethod
    def verify_password(password, stored_hash):
        """비밀번호 검증"""
        try:
            # 저장된 해시에서 솔트와 해시 분리
            salt, stored_password_hash = stored_hash.split(':', 1)
            # 입력된 비밀번호 + 솔트를 해시
            password_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
            # 해시 비교
            return password_hash == stored_password_hash
        except (ValueError, AttributeError):
            # 잘못된 형식이거나 None인 경우
            return False
    
    @staticmethod
    def is_hashed(stored_value):
        """값이 해시된 형태인지 확인"""
        try:
            if not stored_value or ':' not in stored_value:
                return False
            salt, password_hash = stored_value.split(':', 1)
            # 솔트가 64자리 hex이고 해시가 64자리 hex인지 확인
            return len(salt) == 64 and len(password_hash) == 64
        except (ValueError, AttributeError):
            return False
