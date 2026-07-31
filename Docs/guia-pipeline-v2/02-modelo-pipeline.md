# 02 — Modelo del pipeline v2: etapas con fecha cierta y advertencias honestas

## 1. Las dos entidades del pipeline

- **Pedido** (demanda): lo que un CC solicita. Sus etapas propias terminan al
  entrar a una bolsa.
- **Expediente CCMN** (abastecimiento): lo que logística tramita. Del CCMN en
  adelante TODO es cadena dura medida al 100% (cuadro, orden, certificación,
  CCP, EXP SIAF, compromiso, conformidad/almacén).
- **El puente** pedido↔CCMN es la única relación inferida. Niveles: `unico`
  (bolsa con 1 CCMN), `declarado` (texto de orden/certificación),
  `resuelto_manual` (vista de bolsa), `ambiguo`, `conflicto`, `sin_ccmn`.

Regla de presentación: **el avance del expediente se muestra siempre** (es
cierto); lo que depende del puente es *a qué pedido se atribuye*. Un pedido
`ambiguo` en una bolsa con órdenes muestra: "tu bolsa ya tiene N órdenes
emitidas (O/S 132, 155, 802) — confirma cuál corresponde a tu pedido".
Nunca más un "sin avance" falso ni un avance inventado.

## 2. Tabla de etapas con su FECHA (fuente exacta)

Cada etapa se considera alcanzada **solo si tiene fecha**. Grano pedido (P),
expediente (E) o puente (⇄):

| # | Etapa | Grano | Fecha (fuente en snapshot) |
|---|---|---|---|
| 1 | Registrado | P | `SIG_PEDIDOS.FECHA_PEDIDO` |
| 2 | Aprobado | P | `FECHA_APROB`; historial VB: `seguimiento_estados` (t=2) |
| 3 | En cuadro de necesidad | P | `FECHA_REG` del item con `SEC_CUA_MOD_SAL` |
| 4 | Consolidado (bolsa/CCMN) | ⇄ | `SIG_PAAC_CONSOLIDADO.FECHA_CONS` |
| 5 | Cotización | E | `SIG_SOLICITUD_COTIZACION.FECHA_REG` |
| 6 | Cuadro de adquisición | E | `SIG_CUADRO_ADQUISICION.FECHA_CUADRO` |
| 7 | Certificación / CCP | E | `SIG_CERTIFICACION.FECHA` + fase con `NRO_CERTIFICA_SIAF` |
| 8 | Orden emitida | E | `SIG_ORDEN_ADQUISICION.FECHA_ORDEN` |
| 9 | Compromiso SIAF | E | `SIG_EXP_SIGA_DOCU.FECHA_INTERFASE` |
| 10 | Ejecución — S: conformidad(es) · B: entrada almacén | E | `SIG_MOVIM_CONFOR_SERVICIO.FECHA_MOVIMTO` / `SIG_MOVIM_ALMACEN(I,1).FECHA_MOVIMTO` |
| 11 | Devengado | E | S: conformidad con `ESTADO_DEVENG` devengado o devengado MEF de la celda cubre la orden · B: fase DV en expediente |
| 12 | Atendido / cierre | P | B: pecosa (`SIG_MOVIM_ALMACEN(S,1)`) · S: última conformidad con orden cubierta · o `ESTADO='7'` |

Notas de corrección sobre el modelo actual:

- **Quitar t=19 como evidencia de cierre**: el módulo 19 del catálogo son
  estados de PECOSA del pedido interno, no cierre genérico. Para bienes la
  pecosa ya se detecta por almacén; para servicios usar conformidades.
- **Cierre de servicios (caso 232/S)**: una O/S con conformidad registrada y
  `ESTADO_DEVENG` en estado devengado (o suma de conformidades que cubre
  `TOTAL_FACT_SOLES`) = servicio concluido. Etapa 11/12 con fecha de la
  última conformidad. Esto reemplaza el `tiene_devengado = 0` hardcodeado.
- **Órdenes/pedidos anulados o denegados**: leer `ESTADO` de la orden y los
  estados negativos del seguimiento (Denegado=3, Anulado). Nuevo estado
  terminal `cerrado_negativo` con su fecha — sale del flujo activo y del
  cálculo de alertas.

## 3. API del pipeline: qué devuelve cada tarjeta

```jsonc
{
  "nro_pedido": 232, "tipo_bien": "S", "ano": 2026,
  "identificadores": {            // los 3 principales, siempre presentes
    "pedido": "232-2026/S",
    "orden": "O/S 232" | null,     // null si el puente no está resuelto
    "exp_siaf": 596 | null,
    "ccp_siaf": 230 | null
  },
  "etapa": "devengado",
  "fechas": {                      // TODAS las etapas alcanzadas con fecha
    "registrado": "2026-02-05", "aprobado": "2026-02-05",
    "consolidado": "2026-02-18", "certificacion": "2026-02-27",
    "orden": "2026-03-03", "compromiso": "2026-03-04",
    "ejecucion": "2026-03-12", "devengado": "2026-03-12"
  },
  "puente": {
    "nivel": "resuelto_manual",
    "bolsa": 11553,
    "candidatos": [2266, 2281, 3532],
    "avance_bolsa": {              // avance CIERTO aunque el puente no esté resuelto
      "ordenes": [{"orden": "O/S 132", "fecha": "2026-02-20"}, ...],
      "max_etapa": "ejecucion"
    }
  },
  "alerta": null | { "tipo": "...", "evidencia": "...", "desde": "fecha" },
  "sincronizado_hasta": "2026-07-30T08:30:00"
}
```

La clasificación de etapa se calcula en la vista materializada (01 §1) y el
service solo aplica umbrales/permisos: el kanban carga en una query Postgres.

## 4. Advertencias con datos ciertos (rediseño de alertas)

Principio: **una alerta necesita evidencia y fecha**. Tipos v2:

| Alerta | Condición (todo con datos del snapshot) | Severidad |
|---|---|---|
| `estancado_real` | Etapa actual con fecha > umbral por macrofase Y ninguna etapa posterior tiene fecha NI en el pedido NI en su bolsa | rojo |
| `puente_pendiente` | Bolsa con avance (orden/conformidad) pero puente no resuelto — "confirma tu CCMN para atribuir el avance" | **info/ámbar, no rojo** |
| `conflicto_puente` | Fuente declarativa apunta a CCMN fuera de los candidatos | ámbar |
| `cerrado_negativo` | Denegado/anulado con fecha y usuario del seguimiento | gris (terminal) |
| `sin_consolidar` | Aprobado hace > umbral y sin `SEC_CUA_MOD_SAL` | ámbar |
| `desfase_devengado` | Compromiso hace > umbral y devengado MEF de la celda = 0 | ámbar |

Reglas anti-alarma (lo que pedía el usuario):

1. Antes de marcar `estancado_real`, comprobar el **avance de la bolsa**: si
   la bolsa del pedido ya tiene orden o conformidad, el pedido NO está
   estancado — está `puente_pendiente`. El 232/S pasa de "⚠ en ejecución,
   estancado" a "✔ servicio concluido (O/S con conformidad 12-mar) — puente
   por confirmar".
2. El reloj de "días en etapa" corre desde la **fecha de la etapa**, no desde
   la última sincronización ni desde el registro del pedido.
3. Etapas terminales (cierre y cerrado_negativo) nunca alertan.
4. Cada alerta muestra su evidencia en el tooltip: "sin cotización desde el
   18-feb (fecha CCMN)" — el usuario ve POR QUÉ se alerta.

## 5. El puente: cascada v2 (simplificada + verificable)

Orden de resolución (por pedido):

1. `resuelto_manual` (tabla de resoluciones — se mantiene tal cual).
2. `unico` (bolsa con 1 CCMN — 571 B + 353 S pedidos, medido).
3. `declarado` (texto de orden / certificación — regex ya validado).
4. `ambiguo` (con `avance_bolsa` visible) / `conflicto` / `sin_ccmn`.

Verificación cruzada nueva: al resolver (manual o declarado), si el CCMN
tiene orden (duro), comprobar que el texto de esa orden no nombre a OTRO
pedido de la bolsa; si lo hace → degradar a `conflicto` y mostrarlo en la
vista de bolsa. El composite por monto ya no asigna órdenes; puede quedar
como señal informativa en la bolsa ("monto del pedido ≈ monto de la O/S X").

## 6. Cruce MEF (devengado por celda)

- Celda = (`SEC_FUNC`, `CLASIFICADOR`), llaves 100% pobladas por orden.
- Si la celda tiene 1 sola orden → el devengado MEF de la celda se atribuye a
  esa orden (fecha: mes MEF del devengado).
- Si tiene N órdenes → mostrar cobertura a nivel celda (devengado MEF vs suma
  comprometida de las órdenes) en el detalle del expediente; sin reparto.
- `EXP_SIAF`/`CCP` se muestran como identificadores para verificación manual
  en SIAF.
