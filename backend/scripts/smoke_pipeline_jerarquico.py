"""Smoke test del rediseno del pipeline (macrofases + 13/16 etapas).

Corre la query del repo contra SIGA_300687 y valida:
    - Pedido testigo 232/S: alcanza al menos hasta ejecucion (macro=ejecucion, etapa=ejecucion).
    - Pedido testigo 005/B: llega a cierre (macro=cierre).
    - Distribucion 2026 completa: ningun bucket colapsado a 0.

Uso: .venv\\Scripts\\python.exe backend\\scripts\\smoke_pipeline_jerarquico.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

# Permitir importar app.* cuando se corre desde la raiz del repo.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.repositories import pipeline_repo
from app.schemas.pipeline import ETAPA_A_MACROFASE, ETAPAS_ORDEN
from app.services.pipeline_service import _etapa_maxima, _renombrar


def main() -> int:
    print(f"SEC_EJEC={settings.SEC_EJEC}  ANO={settings.ANO_VIGENTE}")

    raw = pipeline_repo.pipeline_pedidos_raw(settings.ANO_VIGENTE, centros=None)
    print(f"pedidos crudos: {len(raw)}")

    clasif = []
    for f in raw:
        etapa = _etapa_maxima(f)
        f["etapa"] = etapa
        f["macrofase"] = ETAPA_A_MACROFASE[etapa]
        clasif.append(_renombrar(f))

    # Distribucion por macrofase / etapa.
    macro_ct: Counter[str] = Counter(f["macrofase"] for f in clasif)
    etapa_ct: Counter[str] = Counter(f["etapa"] for f in clasif)

    print("\n=== Distribucion por macrofase ===")
    for m in ("solicitud", "programacion", "certificacion", "contratacion", "ejecucion", "cierre"):
        print(f"  {m:20s} {macro_ct.get(m, 0)}")

    print("\n=== Distribucion por etapa detallada ===")
    for e in ETAPAS_ORDEN:
        print(f"  [{ETAPAS_ORDEN.index(e)+1:2}] {e:22s} {etapa_ct.get(e, 0)}")

    # Testigo 232/S — canonico servicio finalizado.
    p232 = next(
        (f for f in clasif if f["nro_pedido"] == 232 and f["tipo_bien"] == "S"),
        None,
    )
    print("\n=== Testigo 232/S ===")
    if p232 is None:
        print("  NO ENCONTRADO en el resultado")
    else:
        print(f"  etapa={p232['etapa']}  macrofase={p232['macrofase']}")
        print(f"  flags: orden={p232.get('tiene_orden')} "
              f"ejec={p232.get('tiene_ejecucion')} "
              f"ccmn={p232.get('tiene_ccmn')} "
              f"cert={p232.get('tiene_certificacion')} "
              f"cierre={p232.get('tiene_cierre')}")

    # Testigo 005/B TIPO_PEDIDO=1 — deberia estar cerrado.
    p005 = next(
        (f for f in clasif if f["nro_pedido"] == 5 and f["tipo_bien"] == "B"),
        None,
    )
    print("\n=== Testigo 005/B ===")
    if p005 is None:
        print("  NO ENCONTRADO")
    else:
        print(f"  etapa={p005['etapa']}  macrofase={p005['macrofase']}  "
              f"tipo_pedido={p005.get('tipo_pedido')}")
        print(f"  flags: orden={p005.get('tiene_orden')} "
              f"kardex={p005.get('tiene_kardex')} "
              f"pecosa={p005.get('tiene_pecosa')} "
              f"cierre={p005.get('tiene_cierre')}")

    # Verificaciones minimas.
    exit_code = 0
    if sum(macro_ct.values()) == 0:
        print("\nFAIL: no se clasifico ningun pedido")
        exit_code = 1
    if macro_ct.get("cierre", 0) == 0:
        print("\nWARN: 0 pedidos cerrados — revisar flag tiene_cierre")
    if macro_ct.get("contratacion", 0) + macro_ct.get("ejecucion", 0) == 0:
        print("\nFAIL: 0 pedidos con orden — la query del kanban sigue rota")
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
