# Cadena de montos SIAF dentro de SIGA

_Generado por el script homónimo; no editar a mano._


## 1. SIG_EXP_SIGA_SECU: fases y estados (2026)

| CICLO | FASE | ESTADO_FASE | ESTADO_EXP | secuencias | expedientes | con_exp_siaf |
|---|---|---|---|---|---|---|
| G | C | 0 |  | 6 | 5 | 0 |
| G | C | 0 | 0 | 1 | 1 | 0 |
| G | C | 2 | 2 | 1481 | 1453 | 1481 |


### Montos por fase (SECU × PPTO)

| CICLO | FASE | ESTADO_FASE | expedientes | monto_soles |
|---|---|---|---|---|
| G | C | 0 | 5 | 252558.02 |
| G | C | 2 | 1453 | 11616983.24 |


### Vínculo expediente → orden (NRO_ORDEN_SOS)

| TIPO_BIEN_SOS | secuencias | con_orden |
|---|---|---|
| S | 4 | 4 |
|  | 1484 | 0 |


## 2. SIG_ORDEN_PRESUPUESTO: cobertura EXP_SIAF y fase

| TIPO_BIEN | FASE | ESTADO_EXP | ordenes | filas_con_exp_siaf | monto_soles |
|---|---|---|---|---|---|
| B |  |  | 2 | 0 | 34297.00 |
| B |  | 2 | 630 | 712 | 6349140.48 |
| S |  |  | 2 | 0 | -279421.00 |
| S |  | 0 | 1 | 0 | 279421.00 |
| S |  | 2 | 839 | 847 | 5267842.76 |


## 3. SIG_TECHO_PRESUPUESTO 2026: totales por campo

| filas | pia | pim | acum_cert | acum_cert_siaf | acum_com_anual_siaf | acum_com_mensual_siaf | acum_dev_siga | acum_dev_siaf | disponible_siaf | reserva_pedido |
|---|---|---|---|---|---|---|---|---|---|---|
| 2218 | 65978168.00 | 163255720.00 | 15787701.61 | 25032363.20 | 0.00 | 0.00 |  | 0.00 | 13862777.80 | 431472.05 |


### EJEC_01..12 (¿ejecución mensual poblada?)

| e01 | e02 | e03 | e04 | e05 | e06 | e07 | e08 |
|---|---|---|---|---|---|---|---|
| 233292.00 | 1764364.76 | 3477722.62 | 2289246.01 | 3083488.59 | 803166.26 | 0.00 | 0.00 |


### FECHA_SIAF del techo: ¿cuándo se sincronizó por última vez?

| min_fecha | max_fecha | filas_con_fecha |
|---|---|---|
| 2026-01-12 13:26:48.620000 | 2026-06-10 11:39:21.740000 | 1065 |


## 4. INTF_CAB: operaciones por ciclo/fase/estado MEF (2026)

| CICLO | FASE | ESTADO | MEF_ESTADO | operaciones | con_exp_siaf |
|---|---|---|---|---|---|
| G | C |   |   | 1470 | 1470 |
| G | C | A |   | 9 | 9 |
| G | C | R |   | 4 | 4 |


### Montos de la interfase (INTF_CAB × INTF_DET) por fase

| CICLO | FASE | MEF_ESTADO | operaciones | monto_mn |
|---|---|---|---|---|
| G | C |   | 1483 | 11852439.24 |


## 5. Órdenes con devengado según SECU fase D

_(sin filas)_


### Devengado 2026 por meta vía expedientes (top 15)

_(sin filas)_

