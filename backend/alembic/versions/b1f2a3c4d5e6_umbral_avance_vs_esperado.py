"""Umbral de semáforo temporal: rezago (avance esperado − real) para saldos.

El semáforo de saldos deja de usar un corte fijo de % devengado (que en julio
alarmaría de más) y pasa a medir el REZAGO contra el avance esperado por el mes
de corte del snapshot. Este umbral parametriza la brecha en puntos porcentuales:

  - rezago ≤ verde (10 pp)     → verde   (al día o adelantado)
  - rezago ≤ amarillo (25 pp)  → amarillo (rezago moderado)
  - rezago >  amarillo         → rojo     (rezago severo)

direccion='menor' porque menos rezago es mejor. Ver semaforo_service.color_temporal.

Revision ID: b1f2a3c4d5e6
Revises: a9f1c7d3e8b4
"""

from __future__ import annotations

from alembic import op

revision: str = "b1f2a3c4d5e6"
down_revision: str | None = "a9f1c7d3e8b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotente: no duplica si ya existe (permite re-correr en dev).
    op.execute(
        """
        INSERT INTO sistema.umbrales_semaforos
            (modulo, metrica, umbral_verde, umbral_amarillo, direccion)
        SELECT 'saldos', 'avance_vs_esperado', 10.00, 25.00, 'menor'
        WHERE NOT EXISTS (
            SELECT 1 FROM sistema.umbrales_semaforos
             WHERE modulo = 'saldos' AND metrica = 'avance_vs_esperado'
        )
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM sistema.umbrales_semaforos "
        "WHERE modulo = 'saldos' AND metrica = 'avance_vs_esperado'"
    )
