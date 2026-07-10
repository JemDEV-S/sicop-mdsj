"""Validacion de reCAPTCHA v3 contra Google.

Si `RECAPTCHA_SECRET` esta vacio (dev sin captcha), la validacion se salta y
devuelve un score fijo — util para tests locales. En prod el secret DEBE
estar seteado.
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
UMBRAL_MINIMO_SCORE = 0.5


class CaptchaInvalido(RuntimeError):
    pass


def verificar(token: str, ip: str | None = None) -> float:
    """Verifica el token contra Google. Devuelve el score (0.0–1.0).

    Lanza `CaptchaInvalido` si el token no es valido o el score esta bajo el
    umbral.
    """
    if not settings.RECAPTCHA_SECRET:
        logger.warning("RECAPTCHA_SECRET vacio — validacion desactivada (dev)")
        return 1.0

    if not token:
        raise CaptchaInvalido("token vacio")

    data = {"secret": settings.RECAPTCHA_SECRET, "response": token}
    if ip:
        data["remoteip"] = ip

    try:
        r = httpx.post(VERIFY_URL, data=data, timeout=5.0)
        r.raise_for_status()
        payload = r.json()
    except httpx.HTTPError as exc:
        raise CaptchaInvalido(f"error contactando reCAPTCHA: {exc}") from exc

    if not payload.get("success"):
        raise CaptchaInvalido(
            f"reCAPTCHA rechazo el token: {payload.get('error-codes')}"
        )
    score = float(payload.get("score", 0.0))
    if score < UMBRAL_MINIMO_SCORE:
        raise CaptchaInvalido(f"score {score:.2f} bajo umbral {UMBRAL_MINIMO_SCORE}")
    return score
