"""Seed de roles, usuario admin inicial, umbrales de semáforo y alertas por defecto.

Revision ID: 0003_seed_auth_umbrales
Revises: 0002_seed_ref_catalogos
Create Date: 2026-07-09

Fuentes:
- `Docs/actividad-2-requerimientos-funcionales.md` §2 RN-01 (semáforos por defecto)
  y RN-02 (alertas por defecto).

**Nota de seguridad:** el usuario `admin` se crea con contraseña por defecto
`ChangeMe!2026` y `debe_cambiar_password=true`. Debe cambiarse en el primer
login (bloqueado por HU-08 en T-08). Nunca desplegar a producción sin
haber rotado esta credencial.
"""

from collections.abc import Sequence

import bcrypt as _bcrypt
import sqlalchemy as sa

from alembic import op

revision: str = "0003_seed_auth_umbrales"
down_revision: str | None = "0002_seed_ref_catalogos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ROLES = [
    ("ciudadano", "Ciudadano"),
    ("operativo", "Operativo"),
    ("decisor", "Decisor"),
    ("admin", "Administrador"),
]

# (modulo, metrica, umbral_verde, umbral_amarillo, direccion)
# RN-01: verde ≥90%, amarillo 60-89%, rojo <60% para avance. Saldo es inverso.
UMBRALES_SEMAFOROS = [
    # Portal de obras — avance físico (más = mejor)
    ("portal_obras", "avance_fisico", 90.00, 60.00, "mayor"),
    # Portal de obras — avance financiero (más = mejor)
    ("portal_obras", "avance_financiero", 90.00, 60.00, "mayor"),
    # Saldos — % devengado del PIM (más = mejor)
    ("saldos", "avance_devengado", 90.00, 60.00, "mayor"),
    # Saldos — saldo disponible (menor = mejor cuando estamos a fin de año)
    ("saldos", "saldo_disponible_pct", 10.00, 40.00, "menor"),
    # Metas — devengado vs esperado por trimestre (más = mejor)
    ("metas", "ejecucion_trimestre", 90.00, 60.00, "mayor"),
    # Ejecución global — devengado vs PIM
    ("ejecucion", "devengado_vs_pim", 90.00, 60.00, "mayor"),
]

# codigo_alerta -> parámetros (RN-02)
UMBRALES_ALERTAS = [
    ("pedido_estancado", '{"dias": 15}'),
    ("contrato_por_vencer", '{"dias": 30}'),
    ("meta_baja_ejecucion", '{"pct_q3": 50, "pct_q4": 90}'),
]


def upgrade() -> None:
    conn = op.get_bind()

    # Roles
    conn.execute(
        sa.text(
            "INSERT INTO auth.roles (codigo, nombre) "
            "VALUES (CAST(:c AS codigo_rol), :n)"
        ),
        [{"c": c, "n": n} for c, n in ROLES],
    )

    # Usuario admin inicial.
    # Se usa la lib `bcrypt` directamente (no passlib) para evitar el bug
    # de detección de backend en passlib 1.7.4 con bcrypt >= 4.1.
    password_hash = _bcrypt.hashpw(
        b"ChangeMe!2026", _bcrypt.gensalt()
    ).decode("utf-8")
    conn.execute(
        sa.text(
            """
            INSERT INTO auth.usuarios (
                usuario, password_hash, nombre_completo, email,
                rol_id, debe_cambiar_password
            )
            SELECT
                :usuario, :password_hash, :nombre, :email,
                r.id, true
            FROM auth.roles r
            WHERE r.codigo = 'admin'
            """
        ),
        {
            "usuario": "admin",
            "password_hash": password_hash,
            "nombre": "Administrador del Sistema",
            "email": None,
        },
    )

    # Umbrales de semáforos
    conn.execute(
        sa.text(
            "INSERT INTO sistema.umbrales_semaforos "
            "(modulo, metrica, umbral_verde, umbral_amarillo, direccion) "
            "VALUES (:modulo, :metrica, :verde, :amarillo, CAST(:dir AS direccion_semaforo))"
        ),
        [
            {
                "modulo": m,
                "metrica": met,
                "verde": v,
                "amarillo": a,
                "dir": d,
            }
            for m, met, v, a, d in UMBRALES_SEMAFOROS
        ],
    )

    # Umbrales de alertas
    conn.execute(
        sa.text(
            "INSERT INTO sistema.umbrales_alertas (codigo_alerta, parametros) "
            "VALUES (:codigo, CAST(:params AS jsonb))"
        ),
        [{"codigo": c, "params": p} for c, p in UMBRALES_ALERTAS],
    )


def downgrade() -> None:
    op.execute("DELETE FROM sistema.umbrales_alertas")
    op.execute("DELETE FROM sistema.umbrales_semaforos")
    op.execute("DELETE FROM auth.usuarios WHERE usuario = 'admin'")
    op.execute("DELETE FROM auth.roles")
