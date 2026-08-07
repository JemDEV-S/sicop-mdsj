# Hallazgos de la exploración SIGA (2026-07-30)

Basado en las corridas de los scripts 00–06 contra `SIGA_300687` local
(datos hasta ~2026-06-11). Cada afirmación cita el resultado que la sustenta.

## H1. El backend usa 24 tablas; hay 148 con datos 2026 sin usar

`resultados/00-inventario.md`. De 937 tablas, 431 tienen datos y 171 tienen
movimiento 2026. El backend actual referencia solo 24. Entre las no usadas
están las que resuelven los problemas actuales: `SIG_CERTIFICACION_FASE`,
`SIG_SEGUIMIENTO_ESTADO`, `SIG_ORDEN_PRESUPUESTO`, `INTF_CAB/INTF_DET`.

## H2. El CCMN de cada orden es un HECHO, no una inferencia

`resultados/04-vinculos-duros.md` §C y `resultados/06-pipeline-invertido.md` §1.

Dos rutas duras independientes dan el CCMN de una orden:

- cuadro: `SIG_ORDEN_ADQUISICION.SEC_CUADRO → SIG_CUADRO_ADQUISICION.NRO_CONS_PAAC`
- certificación: `SIG_CERTIFICACION_FASE.NRO_ORDEN → NRO_CONSOLID`

Concuerdan en **100%** de los casos (833/833 S, 596/596 B, 0 discrepancias).
Además `SIG_CERTIFICACION_FASE` trae `NRO_CERTIFICA_SIAF` (CCP) poblado al
100%. **Todo el tramo CCMN → cotización → cuadro → orden → certificación →
EXP_SIAF es cadena dura verificada** (cobertura §3: 630/632 B y 839/841 S
órdenes llegan hasta EXP_SIAF e interfase).

Implicación: la única frontera difusa real del pipeline es **pedido → CCMN**.
Las etapas 4–16 no necesitan heurística ninguna si se cuelgan del CCMN/orden
en vez del pedido.

## H3. La ambigüedad pedido→CCMN es un problema de SERVICIOS, no de bienes

`resultados/06-pipeline-invertido.md` §2.

- Bienes: 595 de 686 CCMN (87%) tienen exactamente 1 pedido en su bolsa;
  571 de 862 pedidos tienen 1 solo candidato.
- Servicios: solo 338 CCMN tienen 1 pedido; hay bolsas de hasta 39 pedidos.

La estrategia de mostrar "pedido con su avance individual" es estructuralmente
imposible para gran parte de servicios: el avance ocurre a nivel de bolsa/CCMN.

## H4. Las columnas de FK pedido→cuadro EXISTEN pero están vacías en esta muni

`resultados/03-estructuras-candidatas.md` y `resultados/04-vinculos-duros.md` §A/§B.

`SIG_DETALLE_BSERV_CUADRO.nro_pedido/sec_item_pedido/tipo_pedido` y
`SIG_CUADRO_NECESIDAD_DET.NRO_PEDIDO/NRO_CONSOLID` son el vínculo oficial del
esquema SIGA — pero **0%** pobladas en 2026 (0 de 4,405 items; 0 de 2,183).
Confirma que logística NO usa el flujo "generar cuadro desde pedido": crea el
CCMN a mano. El desvínculo es operativo, no del esquema. (Vale monitorear:
si algún año empiezan a poblarlas, el problema desaparece de raíz.)

## H5. SIG_SEGUIMIENTO + SIG_SEGUIMIENTO_ESTADO: timeline real, 100% cobertura

`resultados/01-seguimiento-eventos.md` y `resultados/02-decodificar-seguimiento.md`.

- El **100%** de los pedidos 2026 (864 B + 1,048 S) tiene rastro en
  `SIG_SEGUIMIENTO`, con fecha, usuario y estado.
- `SIG_SEGUIMIENTO_ESTADO` (16,578 filas 2026, no usada) guarda la HISTORIA
  de estados por documento (`SEC_ESTADO` incremental), y el catálogo
  `SIG_TRANSACCION_ESTADO` la traduce a texto: Pendiente, VB Jefe, Aprobado,
  **Denegado**, Pecosa parcial…, incluidos estados que el pipeline actual no
  modela (denegados, anulados, extornados).
- Ojo: NO es tabla de vínculos. En eventos tipo 8/9 (órdenes B/S) el campo
  `NRO_PEDIDO` repite el número de ORDEN, no el pedido. `NRO_CONSOLID` está
  siempre vacío en 2026. `SIG_SEGUIMIENTO_SECUENCIA` (grafo doc→doc) está
  casi vacía (2 filas 2026).
- Cada `TIPO_TRANSACCION` es un tipo de documento: 1=pedido interno,
  2=pedido de compra/servicio, 4=proceso PAO/cuadro, 7=contrato, 8=orden de
  compra (estados Comprometido/SIAF), 9=orden de servicio, 19/20=pecosa y
  conformidad del pedido interno.
- Riesgo detectado: el pipeline actual usa `t=19` como evidencia de CIERRE,
  pero en el catálogo el módulo 19 son estados de PECOSA del pedido interno
  (estado 7 = "PECOSA"). Para servicios no aplica; revisar si infla cierres.

## H6. Los montos SIGA no sirven como autoridad presupuestal (regla del proyecto)

`resultados/05-cadena-montos-siaf.md`. Confirmado por el usuario: **el
presupuesto no se maneja en SIGA; la única fuente real y precisa es la API
MEF** que el sistema ya consume.

Evidencia local que lo respalda:

- `SIG_EXP_SIGA_SECU` solo registra fase **C** (compromiso). No hay fase D
  (devengado) ni G (girado) en 2026: la muni devenga directo en SIAF.
- `SIG_TECHO_PRESUPUESTO 2026`: `MNTO_ACUM_DEVGDO_SIGA` = NULL,
  `MNTO_ACUM_DEVGDO_SIAF` = 0, `MNTO_ACUM_COMA/COMM_SIAF` = 0,
  `PPTO_DISP_SIAF` suma 13.8M frente a un PIM de 163M (solo 1,065 de 2,218
  filas tienen `FECHA_SIAF`). **Los campos que los Docs declaran
  "autoritativos" (regla de negocio #3) están vacíos o desactualizados en
  2026 — esta es una causa directa de los números incorrectos del dashboard.**
- `INTF_CAB` (interfase SIGA→SIAF) solo transmite fase C.

Lo que SÍ aporta SIGA: llaves de cruce perfectas hacia MEF (H7) y la
existencia/fecha del compromiso por orden.

## H7. Llaves de cruce orden→MEF al 100%

`resultados/06-pipeline-invertido.md` §4. `SIG_ORDEN_PRESUPUESTO` da por cada
orden: `SEC_FUNC` (100%), `CLASIFICADOR` (100%), `EXP_SIAF` (99.7%).

Granularidad del cruce contra el snapshot MEF (meta+clasificador):

- 244 celdas meta+clasificador tienen exactamente 1 orden → el devengado MEF
  de esa celda es atribuible 1:1 a la orden.
- 139 celdas con 2–5 órdenes, 50 celdas con 6+ (928 órdenes) → ahí el
  devengado solo puede mostrarse agregado a nivel de celda, no por orden
  (mostrar "cobertura: devengado MEF de la celda vs suma comprometida de sus
  órdenenes").

## H8. Estados negativos invisibles hoy

El catálogo `TIPO_MODULO` define estados Denegado (3), Anulado (4-6 en
órdenes), Extornado — y `SIG_SEGUIMIENTO_ESTADO` los registra con fecha y
usuario. El pipeline actual solo modela avance "hacia adelante": un pedido
denegado o una orden anulada aparecen como "estancados" en vez de cerrados
negativamente. Esto también distorsiona los conteos del kanban.
