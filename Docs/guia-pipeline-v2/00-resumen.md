# Guía Pipeline v2 — Resumen y principios

**Fecha:** 2026-07-30 · **Base:** exploración `exploracion-siga/` (hallazgos H1–H8)
**Propósito:** guía de implementación para las próximas sesiones. Cada documento
es autocontenido y cita los datos medidos que lo sustentan.

## Documentos de la guía

| Doc | Qué cubre |
|---|---|
| [01-capa-datos.md](01-capa-datos.md) | Ampliar los datos que se extraen de SIGA sin saturar su BD ni el sistema: snapshot incremental a PostgreSQL, cadencias, cache |
| [02-modelo-pipeline.md](02-modelo-pipeline.md) | El modelo corregido del pipeline: etapas con fecha cierta, advertencias con datos ciertos, estados negativos, cierre real de servicios (caso 232/S) |
| [03-vistas-ui.md](03-vistas-ui.md) | Kanban, detalle de pedido y vista de bolsa: qué se mantiene, qué se completa, diseño visual y dinamismo |

## Principios no negociables de la v2

1. **Montos solo del MEF.** El presupuesto no se maneja en SIGA (confirmado y
   medido: el techo SIGA está vacío/desactualizado en 2026). Todo monto
   presupuestal en pantalla sale del snapshot MEF. SIGA aporta proceso,
   fechas, estados y llaves de cruce.

2. **Tres identificadores principales, visibles en todas las vistas:**
   - `N° Pedido` (con tipo B/S y año) — identidad de la demanda.
   - `N° Orden` (O/C u O/S) — identidad del contrato.
   - `EXP SIAF` (+ `CCP` cuando exista) — identidad presupuestal, la que el
     funcionario puede buscar en SIAF.
   Toda tarjeta/fila/detalle muestra los tres cuando existen; el usuario debe
   poder copiar cualquiera con un click.

3. **Ninguna advertencia sin dato cierto.** El sistema solo alarma cuando
   puede probar el problema con una fecha o estado de SIGA/MEF. Si un dato es
   inferido (ambiguo, sin resolución del puente), la UI lo presenta como
   "pendiente de confirmación", nunca como alerta roja. Ver 02 §Advertencias.

4. **La ambigüedad vive solo en el puente pedido↔CCMN.** Del CCMN hacia
   adelante todo es cadena dura verificada al 100% (orden, certificación,
   CCP, EXP SIAF, compromiso, conformidad). Un pedido "ambiguo" NO significa
   "sin avance": su bolsa puede tener órdenes emitidas y servicios concluidos
   — y eso se muestra (como avance de la bolsa, no del pedido).

5. **La bolsa se mantiene y se refuerza.** La vista de bolsa con asignación
   manual pedido↔CCMN (ya construida en `BolsaPedido.tsx` / `PedidoDetalle.tsx`)
   es la preferencia del usuario y es la pieza que resuelve la ambigüedad.
   Se mejora gráficamente (grafo de dos columnas) sin cambiar su regla de oro:
   nunca sugerir un ganador.

6. **SIGA no se consulta en caliente para vistas masivas.** El kanban y el
   dashboard leen de PostgreSQL (snapshot sincronizado por jobs). SIGA solo
   se toca en jobs programados y en el refresh puntual de UN documento cuando
   el usuario lo pide. Ver 01 §Cadencias.

7. **Cada etapa del pipeline lleva su fecha.** No hay etapa sin fecha de
   origen: si no hay fecha, la etapa no está alcanzada. Fuentes de fecha por
   etapa en 02 §Tabla de etapas.

8. **Sin redundancia de datos.** Cada dato tiene UNA tabla dueña en Postgres;
   las vistas derivan por JOIN. No se copia lo que ya existe en `ref.*` ni
   en `siaf.*` (MEF). Ver 01 §Esquema.

## El caso que motiva la corrección (pedido de servicio 232)

Medido en BD (2026-07-30):

- El pedido 232/S está en bolsa `SEC_CUA_MOD_SAL=11553` con **3 CCMN
  candidatos** (2266, 2281, 3532) → hoy queda `ambiguo`.
- Esos CCMN tienen órdenes emitidas **conocidas por vínculo duro** (132, 155,
  802, vía `SIG_CERTIFICACION_FASE`, con CCP SIAF 230, 234, 1631).
- Además existe la O/S 232 (2026-03-03, S/ 1,400, EXP SIAF 596) **con
  conformidad de servicio registrada el 2026-03-12**.
- `SIG_MOVIM_CONFOR_SERVICIO` trae `ESTADO_DEVENG`, `EXPEDIENTE_SIAF` y
  `SECUENCIA_SIAF`: la conformidad sabe si ya se devengó y contra qué
  expediente.

Es decir: el servicio ya se ejecutó y probablemente ya se devengó, pero el
kanban lo muestra "en ejecución" y con alerta, porque (a) el devengado de
servicios está deshabilitado en `pipeline_repo` (pendiente del "Fix #2"),
(b) el cierre solo se detecta con `ESTADO='7'` o seguimiento t=19 (que en
realidad son estados de pecosa de pedido interno, no cierre de servicios), y
(c) la alerta de estancamiento cuenta días sin considerar que la etapa
siguiente sí ocurrió. La v2 corrige las tres cosas con los datos de arriba.
