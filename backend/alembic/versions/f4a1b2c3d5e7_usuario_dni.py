"""Añadir DNI a auth.usuarios (gestión de usuarios T-08/T-54)

El DNI identifica a la persona y es la contraseña inicial del usuario al crearlo
desde la pantalla de gestión (el cambio posterior es opcional). Se añade como
nullable para no romper los usuarios existentes del seed (que no tienen DNI);
la obligatoriedad se exige a nivel de la API al crear, no en la columna.

Índice único parcial (solo donde dni IS NOT NULL): dos personas no comparten
DNI, pero los usuarios legados sin DNI no colisionan entre sí.

Revision ID: f4a1b2c3d5e7
Revises: b1f2a3c4d5e6
Create Date: 2026-08-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f4a1b2c3d5e7'
down_revision: Union[str, Sequence[str], None] = 'b1f2a3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'usuarios',
        sa.Column('dni', sa.String(length=15), nullable=True),
        schema='auth',
    )
    op.create_index(
        'ix_usuarios_dni',
        'usuarios',
        ['dni'],
        unique=True,
        postgresql_where=sa.text('dni IS NOT NULL'),
        schema='auth',
    )


def downgrade() -> None:
    op.drop_index('ix_usuarios_dni', table_name='usuarios', schema='auth')
    op.drop_column('usuarios', 'dni', schema='auth')
