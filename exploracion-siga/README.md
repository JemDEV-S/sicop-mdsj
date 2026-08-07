# Exploración SIGA — proyecto de re-evaluación de datos

**Fecha de inicio:** 2026-07-30
**BD:** SQL Server local `PC_OTI_03`, base `SIGA_300687` (backup muni, 2023–2026), Windows Auth.
**Entidad:** `SEC_EJEC = 300687` · Año foco: `2026`.

## Por qué existe esta carpeta

Los reportes internos (dashboard y pipeline) siguen mostrando datos incorrectos.
Las estrategias documentadas en `Docs/` (match composite por monto, cascada de
confianza pedido↔CCMN, flags de evidencia por etapa) se dan aquí por
**no vinculantes**: este proyecto parte de cero, re-explora la base completa
(980 tablas) y busca estrategias nuevas para:

1. Reconstruir el pipeline de un pedido con la menor heurística posible.
2. Mostrar montos correctos (PIM, certificado, comprometido, devengado, saldo).
3. Cruzar SIGA ↔ SIAF con cobertura medida, no asumida.
4. Proponer nuevas formas de visualizar el pipeline (más allá del kanban).

## Estructura

| Ruta | Qué es |
|---|---|
| `README.md` | Este documento: contexto, método y estado |
| `_db.py` | Utilidad compartida de conexión y volcado de resultados |
| `00_inventario_tablas.py` | Censo de las 937 tablas: filas, cobertura 2026, qué usa el backend |
| `01_seguimiento_eventos.py` | Estructura y cobertura de las tablas de seguimiento/estado |
| `02_decodificar_seguimiento.py` | Semántica de cada TIPO_TRANSACCION del seguimiento |
| `03_estructuras_candidatas.py` | Columnas + muestra de 24 tablas candidatas no usadas |
| `04_vinculos_duros.py` | Cobertura de vínculos duros pedido↔cuadro↔orden↔certificación |
| `05_cadena_montos_siaf.py` | Qué fases/acumulados SIAF existen realmente dentro de SIGA |
| `06_pipeline_invertido.py` | Concordancia orden→CCMN, bolsas reales y llaves de cruce a MEF |
| `resultados/` | Salidas de cada script (markdown), versionadas |
| `hallazgos.md` | **Síntesis H1–H8 de lo encontrado** |
| `estrategias.md` | **Estrategias nuevas E1–E6 (pipeline, cruces, visualización)** |

## Método

- Todo script es **solo lectura** contra SIGA (regla de negocio #2 del proyecto).
- Cada script se puede correr solo: `backend/.venv/Scripts/python.exe exploracion-siga/NN_*.py`
- Cada script escribe su salida a `resultados/NN-*.md` — el resultado queda
  versionado junto al código que lo produjo.
- Ninguna conclusión sin medición: si una llave "debería" cruzar, se mide el
  % de cobertura real en 2026 antes de proponerla.

## Regla marco (confirmada por el usuario durante la exploración)

**El presupuesto NO se maneja en SIGA.** La única fuente real y precisa de
montos (PIA/PIM/certificado/comprometido/devengado/girado) es la **API del
MEF** que el sistema ya consume. SIGA aporta el proceso (documentos, fechas,
estados, 100% de cobertura en seguimiento) y las llaves de cruce
(`SEC_FUNC`, `CLASIFICADOR`, `EXP_SIAF`, `NRO_CERTIFICA_SIAF`).

## Estado

- [x] Conectividad verificada (937 tablas; 2,358 pedidos 2026)
- [x] Inventario de tablas (`resultados/00-inventario.md`)
- [x] Seguimiento como log de eventos (`resultados/01-*.md`, `02-*.md`)
- [x] Estructuras candidatas (`resultados/03-*.md`)
- [x] Vínculos duros (`resultados/04-*.md`) — **orden↔CCMN es un hecho, 100%**
- [x] Cadena de montos SIAF (`resultados/05-*.md`) — solo fase C en SIGA
- [x] Pipeline invertido y llaves a MEF (`resultados/06-*.md`)
- [x] Hallazgos H1–H8 y estrategias E1–E6

Siguiente paso: la guía de implementación derivada de esta exploración está
en [Docs/guia-pipeline-v2/](../Docs/guia-pipeline-v2/00-resumen.md)
(capa de datos sin saturar SIGA, modelo de etapas con fechas, vistas).
