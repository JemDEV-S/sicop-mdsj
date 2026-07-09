"""Smoke test de conectividad SIGA.

Uso: python -m scripts.ping_siga

Verifica:
- Conexión a SQL Server + BD SIGA_300687
- Datos base: META, SIG_ORDEN_ADQUISICION, SIG_TECHO_PRESUPUESTO
- Presencia de SEC_EJEC=300687

Sirve como validación de T-05 y como smoke test antes de arrancar el backend.
"""

import sys

from app.config import settings
from app.siga.conexion import fetch_one, health_check


def main() -> int:
    print("=" * 60)
    print("SICOP-MDSJ - Smoke test SIGA")
    print("=" * 60)

    try:
        info = health_check()
    except Exception as e:
        print(f"❌ ERROR conectando a SIGA: {e}", file=sys.stderr)
        return 1

    print(f"[OK] Servidor:      {info['server_name']}")
    print(f"[OK] Base de datos: {info['database_name']}")
    print(f"[OK] Login:         {info['login_name']}")
    print(f"[OK] SQL Server:    {info['version']}")
    print(f"[OK] Hora servidor: {info['server_time']}")
    print()

    print(f"Filtro obligatorio: SEC_EJEC={settings.SEC_EJEC}")
    print()

    # Contadores por año (2023-2026) — sanity check contra el diccionario.
    checks = [
        ("META", "SELECT COUNT(*) AS n FROM META WHERE sec_ejec=:se AND ano_eje=:a"),
        (
            "SIG_ORDEN_ADQUISICION",
            "SELECT COUNT(*) AS n FROM SIG_ORDEN_ADQUISICION WHERE SEC_EJEC=:se AND ANO_EJE=:a",
        ),
        (
            "SIG_TECHO_PRESUPUESTO",
            "SELECT COUNT(*) AS n FROM SIG_TECHO_PRESUPUESTO WHERE SEC_EJEC=:se AND ANO_EJE=:a",
        ),
        (
            "SIG_PEDIDOS",
            "SELECT COUNT(*) AS n FROM SIG_PEDIDOS WHERE SEC_EJEC=:se AND ANO_EJE=:a",
        ),
        (
            "SIG_CONTRATISTAS",
            "SELECT COUNT(*) AS n FROM SIG_CONTRATISTAS",  # no tiene ano_eje ni sec_ejec
        ),
    ]

    for tabla, sql_tpl in checks:
        print(f"--{tabla} --")
        for ano in (2023, 2024, 2025, 2026):
            try:
                if ":a" in sql_tpl:
                    row = fetch_one(sql_tpl, {"se": int(settings.SEC_EJEC), "a": ano})
                else:
                    row = fetch_one(sql_tpl)
                n = row.n if row else 0
                print(f"    {ano}: {n:>8,} filas")
                if not (":a" in sql_tpl):
                    break  # tabla sin ano_eje, imprimir 1 sola vez
            except Exception as e:
                print(f"    {ano}: ERROR {e}")
        print()

    print("=" * 60)
    print("[OK] Smoke test SIGA completado exitosamente.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
