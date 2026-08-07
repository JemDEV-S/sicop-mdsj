# Pipeline invertido: de la orden al pedido

_Generado por el script homónimo; no editar a mano._


## 1. Orden→CCMN: ruta cuadro vs ruta certificación

| TIPO_BIEN | ordenes | con_cert | concuerdan | difieren |
|---|---|---|---|---|
| S | 841 | 833 | 833 | 0 |
| B | 632 | 596 | 596 | 0 |


## 2. Distribución de pedidos por CCMN (tamaño de bolsa real)

| TIPO_BIEN | n_pedidos | ccmn |
|---|---|---|
| B | 1 | 595 |
| B | 2 | 66 |
| B | 3 | 20 |
| B | 4 | 5 |
| S | 1 | 338 |
| S | 2 | 130 |
| S | 3 | 110 |
| S | 4 | 27 |
| S | 5 | 54 |
| S | 6 | 35 |
| S | 7 | 13 |
| S | 8 | 46 |
| S | 10 | 10 |
| S | 11 | 10 |
| S | 12 | 20 |
| S | 13 | 25 |
| S | 14 | 24 |
| S | 21 | 22 |
| S | 22 | 44 |
| S | 23 | 23 |
| S | 39 | 39 |


### Pedidos según nº de CCMN candidatos en su bolsa

| TIPO_BIEN | n_ccmn | pedidos |
|---|---|---|
| B | 0 | 191 |
| B | 1 | 571 |
| B | 2 | 74 |
| B | 3 | 18 |
| B | 4 | 7 |
| B | 6 | 1 |
| S | 0 | 47 |
| S | 1 | 353 |
| S | 2 | 132 |
| S | 3 | 101 |
| S | 4 | 34 |
| S | 5 | 62 |
| S | 6 | 33 |
| S | 7 | 13 |
| S | 8 | 52 |
| S | 10 | 35 |
| S | 12 | 25 |
| S | 13 | 13 |
| S | 14 | 14 |
| S | 22 | 65 |
| S | 23 | 23 |
| S | 39 | 39 |


## 3. Cadena dura completa por orden (2026)

| TIPO_BIEN | ordenes | con_ccmn | con_ccp_siaf | con_exp_siaf | con_interfase |
|---|---|---|---|---|---|
| B | 632 | 632 | 596 | 630 | 630 |
| S | 841 | 841 | 833 | 839 | 839 |


## 4. Llaves de cruce orden→MEF: SEC_FUNC + CLASIFICADOR + EXP_SIAF

| TIPO_BIEN | ordenes | con_sec_func | con_clasificador | con_exp_siaf |
|---|---|---|---|---|
| B | 632 | 632 | 632 | 630 |
| S | 841 | 841 | 841 | 839 |


### Celdas meta+clasificador según nº de órdenes (atribución 1:1)

| celda | celdas | ordenes |
|---|---|---|
| 1 orden (atribuible 1:1) | 244 | 244 |
| 2-5 ordenes | 139 | 379 |
| 6+ ordenes | 50 | 928 |

