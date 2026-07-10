"""Hash y verificación de contraseñas con bcrypt.

Se usa la lib `bcrypt` directamente (no passlib) para evitar el bug de
detección de backend con bcrypt >= 4.1. Ver commit T-06 (0003 seed).
"""

from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    """Genera el hash bcrypt (salt aleatorio, cost por defecto)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica una contraseña contra su hash almacenado.

    Devuelve `False` ante cualquier error (hash mal formado, etc.) — nunca
    lanza. Así el service de login no distingue "hash inválido" de
    "contraseña incorrecta" en la respuesta HTTP.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False
