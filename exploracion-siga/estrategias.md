# Estrategias nuevas (propuestas a partir de los hallazgos)

Regla marco (confirmada por el usuario): **los montos presupuestales vienen
SIEMPRE de la API MEF**. SIGA aporta el proceso (documentos, fechas, estados)
y las llaves de cruce. Ninguna estrategia de abajo usa montos SIGA como
autoridad.

---

## E1. Pipeline de dos carriles: demanda (pedidos) y abastecimiento (expedientes CCMN)

Hoy el kanban fuerza a que cada pedido tenga "su" avance individual, y para
lograrlo adivina qué orden/CCMN le pertenece (composite por monto, cascada).
Los hallazgos H2/H3 muestran que eso es pelear contra la estructura real:

- El avance de contratación ocurre a nivel **CCMN** (expediente), y del CCMN
  hacia adelante todo es cadena dura y exacta (H2).
- En servicios, muchas bolsas tienen 5–39 pedidos: el avance individual por
  pedido **no existe** como dato; existe el avance de la bolsa.

Propuesta: dos entidades de primera clase en la UI.

1. **Carril demanda** — tarjeta por pedido, con lo que sí es del pedido:
   registrado → aprobado → en cuadro de necesidad → consolidado en bolsa.
   Fechas y estados reales desde `SIG_SEGUIMIENTO(_ESTADO)` (H5), incluidos
   Denegado/Anulado (H8).
2. **Carril abastecimiento** — tarjeta por **CCMN/expediente**: CCMN →
   cotización → cuadro adquisición → orden → certificación (CCP SIAF) →
   compromiso (fecha interfase) → devengado (desde MEF, ver E3). Todo duro,
   sin nivel de confianza, sin heurística.
3. **El puente** entre carriles es la asociación pedido↔CCMN con su nivel
   (único / declarado / manual / ambiguo). La ambigüedad queda confinada al
   puente y visible como tal, en vez de contaminar 12 etapas.

Ventaja: el 100% de lo que se muestra en el carril 2 es exacto; el usuario
de logística ve su trabajo real (expedientes), y el usuario solicitante ve
su pedido y a qué expediente(s) de su bolsa está conectado.

## E2. Timeline auditable por documento (nueva fuente: SIG_SEGUIMIENTO_ESTADO)

Para el detalle de un pedido u orden, reemplazar el timeline inferido por el
**historial real**: `SIG_SEGUIMIENTO_ESTADO` (fecha, usuario, equipo, estado)
traducido con `SIG_TRANSACCION_ESTADO`. Cobertura 100% de pedidos 2026 (H5).

- Muestra quién aprobó y cuándo, cuánto demoró cada V°B°, y los finales
  negativos (denegado/anulado) que hoy son invisibles.
- Métrica nueva de gestión: **tiempo por transición de estado** por CC y por
  usuario aprobador — de dónde salen los cuellos de botella reales, en lugar
  del genérico "días sin cambio de etapa".

## E3. Cruce SIGA↔MEF por celda meta+clasificador con atribución honesta

En vez de intentar "devengado por pedido" (imposible con datos SIGA de esta
muni, H6), cruzar así:

1. Celda = (`SEC_FUNC`, `CLASIFICADOR`). Del lado SIGA: órdenes de la celda
   con su fecha de compromiso (llaves al 100%, H7). Del lado MEF: PIM,
   certificado, comprometido, devengado, girado de la celda (fuente única de
   montos).
2. **Atribución 1:1** cuando la celda tiene una sola orden (244 celdas):
   el devengado MEF de la celda ES de esa orden — mostrarlo en la tarjeta
   del expediente.
3. Celdas con N órdenes: mostrar el devengado **a nivel de celda** con una
   barra de cobertura (devengado MEF vs. total comprometido de las órdenes),
   nunca repartido por heurística.
4. `EXP_SIAF` y `NRO_CERTIFICA_SIAF` quedan registrados por orden para
   validación manual puntual (el funcionario puede buscar el expediente en
   SIAF) y para un futuro cruce expediente-a-expediente si se consigue una
   fuente MEF a ese grano.

## E4. Semáforo de frescura de fuente (dashboard)

Causa raíz de "datos incorrectos" en el dashboard: los campos de
`SIG_TECHO_PRESUPUESTO` que los Docs declaraban autoritativos están vacíos o
viejos en 2026 (H6). Estrategia:

- Eliminar del dashboard todo monto tomado de SIGA (PIM/saldo/devengado del
  bloque "SIGA operativo") y dejar los montos solo del snapshot MEF.
- El bloque SIGA del widget pasa a mostrar lo que SIGA sí sabe: nº de
  pedidos, expedientes y órdenes por estado, compromisos del mes, denegados.
- Cada widget declara su fuente y frescura: "MEF: snapshot del YYYY-MM-DD" /
  "SIGA: datos al YYYY-MM-DD" (max `FECHA_REG` relevante). Si la frescura
  supera un umbral, el widget se marca ámbar en vez de mostrar números viejos
  como si fueran actuales.

## E5. Cascada pedido↔CCMN simplificada (solo el puente)

La cascada de confianza existente sigue siendo válida pero ahora solo tiene
que resolver el puente (E1.3), no las etapas. Y puede validarse mejor:

- Nueva verificación cruzada: si un pedido se asocia a un CCMN, la orden de
  ese CCMN es conocida (H2). El texto libre de esa orden
  (`ESPECIFICACIONES`) debería nombrar al pedido — si nombra a OTRO pedido
  de la bolsa, la asociación es sospechosa → marcar conflicto.
- Los 191 pedidos B / 47 S sin ningún CCMN candidato (H3) son una cola
  visible: "aún no consolidados" — etapa real, no dato faltante.

## E6. Vistas nuevas de pipeline (frontend)

1. **Sankey del flujo anual**: pedidos → bolsas/CCMN → órdenes → compromiso
   → devengado (MEF). Los anchos son conteos (o montos MEF en los tramos
   donde la fuente es MEF). Muestra de un vistazo dónde se angosta el flujo
   (cuántos pedidos mueren sin consolidar, cuántos expedientes sin orden…).
2. **Matriz CC × etapa** (heatmap): filas = centros de costo (jerarquía
   ltree), columnas = etapas del carril correspondiente; celda = nº de
   documentos y edad mediana. Sustituye al kanban global cuando hay miles de
   tarjetas.
3. **Vista de bolsa como grafo pequeño**: pedidos a la izquierda, CCMN a la
   derecha, aristas = asociaciones (color por nivel de confianza). Es la
   visualización natural del puente E1.3 y de la resolución manual.
4. **Cohortes de flujo** ("funnel por mes de registro"): de los pedidos
   registrados en enero, ¿qué % llegó a orden en ≤30/60/90 días? Compara
   meses y detecta degradación del proceso — imposible de ver en un kanban.

## Orden sugerido de implementación

| Paso | Qué | Por qué primero |
|---|---|---|
| 1 | E4 (dashboard solo montos MEF + frescura) | Elimina los números incorrectos visibles hoy; cambio pequeño |
| 2 | E1 carril abastecimiento (expediente CCMN→orden→compromiso) | 100% datos duros; reemplaza las etapas heurísticas 4-10 |
| 3 | E2 timeline real en el detalle | Tabla nueva pero de solo lectura; alto valor percibido |
| 4 | E3 cruce por celda | Necesita el snapshot MEF ya existente + repos nuevos |
| 5 | E5/E6 | Refinamiento del puente y visualizaciones |
