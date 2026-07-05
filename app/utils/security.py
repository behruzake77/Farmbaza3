"""✅ Xavfsizlik yordamchi funksiyalari — parol himoyasi."""

from passlib.context import CryptContext
from typing import Optional
import secrets

# ✅ BCrypt kontekstini yaratish
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Xavfsizlik darajasi
)


def hash_password(password: str) -> str:
    """
    Parolni xavfsiz tarzda hash qilish.
    
    Parametrlar:
        password: Ochiq matnli parol
        
    Qaytaradi:
        Hash qilingan parol satri
        
    Misol:
        >>> hash_password("mening_parolim")
        '$2b$12$...'
    """
    try:
        if not password or len(password) < 4:
            raise ValueError("Parol kamida 4 belgidan iborat bo'lishi kerak")
        return pwd_context.hash(password)
    except Exception as e:
        raise ValueError(f"Parol hash qilishda xatoli: {str(e)}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Parolni tekshirish.
    
    Parametrlar:
        plain_password: Kiritilgan ochiq matnli parol
        hashed_password: Saqlangan hash parol
        
    Qaytaradi:
        Parol to'g'ri bo'lsa True, aks holda False
        
    Misol:
        >>> verify_password("mening_parolim", "$2b$12$...")
        True
    """
    try:
        if not hashed_password or hashed_password is None:
            return False
        if not plain_password:
            return False
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def generate_secure_token(length: int = 32) -> str:
    """
    Xavfsiz token yaratish.
    
    Parametrlar:
        length: Token uzunligi (baytlarda)
        
    Qaytaradi:
        O'n oltilik token
        
    Misol:
        >>> token = generate_secure_token()
        >>> len(token)
        64
    """
    return secrets.token_hex(length)


class PasswordValidator:
    """Parol kuchini tekshirish."""
    
    @staticmethod
    def is_strong(password: str) -> tuple[bool, str]:
        """
        Parol kuchini tekshirish.
        
        Qaytaradi:
            (kuchli_mi, xabar)
        """
        if not password:
            return False, "Parol kiritilmagan"
        
        if len(password) < 8:
            return False, "Parol kamida 8 belgidan iborat bo'lishi kerak"
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)
        
        score = sum([has_upper, has_lower, has_digit, has_special])
        
        if score < 4:
            return False, (
                "Parol kuchli emas. Katta harf, kichik harf, raqam va "
                "maxsus belgi bo'lishi kerak"
            )
        
        return True, "✅ Parol kuchli"


# ✅ O'rnatish skripti — parol hash qilish uchun
if __name__ == "__main__":
    import getpass
    
    print("=" * 50)
    print("PharmBaseUZ - Admin Parol Hash Generatori")
    print("=" * 50)
    print()
    
    while True:
        password = getpass.getpass("Parol kiriting: ")
        
        # Tekshirish
        is_strong, message = PasswordValidator.is_strong(password)
        print(f"Parol kuchi: {message}")
        
        if not is_strong:
            print("❌ Parol kuchsiz. Iltimos, boshqa parol kiriting.\n")
            continue
        
        confirm = getpass.getpass("Parolni qayta kiriting: ")
        
        if password != confirm:
            print("❌ Parollar mos kelmadi. Iltimos, qayta harakat qiling.\n")
            continue
        
        # Hash qilish
        hashed = hash_password(password)
        
        print("\n" + "=" * 50)
        print("✅ PAROL HASH QILINDI!")
        print("=" * 50)
        print(f"\nBu qiymatni .env fayliga yozing:\n")
        print(f"ADMIN_PASSWORD_HASH={hashed}\n")
        print("=" * 50)
        
        # Test
        print("\n🔍 Tekshirilmoqda...")
        if verify_password(password, hashed):
            print("✅ Test muvaffaqiyatli!")
        else:
            print("❌ Test muvaffaqiyatsiz!")
        
        break
