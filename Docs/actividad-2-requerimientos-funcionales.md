# Actividad 2 — Requerimientos Funcionales

> Municipalidad Distrital de San Jerónimo — Cusco
> Entregable formal de la Actividad 2 · Fase de Diseño
> Historias de usuario, criterios de aceptación, reglas de negocio y mockups textuales.
> Julio 2026

---

## 1. Alcance y convenciones

### 1.1 Alcance del MVP

Se implementan los seis módulos definidos en la [idea principal, sección 10](idea-principal.md#10-priorización-del-mvp):

1. Portal de Obras (público)
2. Dashboard general de ejecución presupuestal (público)
3. Pipeline de pedidos y órdenes (interno)
4. Cruce SIAF-SIGA (interno)
5. Consulta de saldos presupuestales (interno)
6. Autenticación y roles

Se incorporan además al MVP por decisión del equipo:

- Mapa de obras interactivo con filtros y semáforo de estado
- Reportes exportables Excel + PDF
- Configuración de umbrales y alertas por decisor/admin
- Buzón de observaciones ciudadanas con captcha

### 1.2 Perfiles de usuario

| Rol | Alcance de datos | Acciones |
|---|---|---|
| **Ciudadano** | Portal público (anónimo) | Solo lectura + observaciones con captcha |
| **Funcionario Operativo** | Solo su(s) `CENTRO_COSTO` asignado(s) | Lectura + exportar |
| **Funcionario Decisor** | Su gerencia completa (usa jerarquía `CENTRO_PADRE`) | Lectura + exportar + configurar umbrales/alertas |
| **Administrador** | Todos los datos | Todo lo anterior + gestión de usuarios y roles |

### 1.3 Sistema es de solo lectura sobre las fuentes

El sistema **no modifica** el SIGA ni el SIAF. La única escritura permitida es a la base intermedia PostgreSQL (usuarios, configuración de alertas/umbrales, observaciones ciudadanas, logs, anotaciones internas).

### 1.4 Priorización MoSCoW

- **M (Must)** — obligatorio para el lanzamiento del MVP
- **S (Should)** — importante pero puede diferirse una iteración
- **C (Could)** — deseable si sobra capacidad
- **W (Won't)** — fuera del MVP (documentado como backlog)

### 1.5 Formato de historia de usuario

Cada historia incluye: identificador, rol, acción, beneficio, prioridad MoSCoW, criterios de aceptación, reglas de negocio aplicables y un mockup textual del flujo/pantalla.

### 1.6 Reglas transversales

**Filtro de entidad:** Toda consulta a fuentes externas fija `SEC_EJEC = 300687`.

**Sincronización:**
- SIAF: job diario nocturno (03:00) que actualiza `SIG_SIAF_SNAPSHOT` en PostgreSQL.
- SIGA: consulta directa a SQL Server en cada request (tiempo real).
- Invierte.pe: junto con el job SIAF (diario).

**Historial:** El MVP muestra solo el año vigente (2026). El modelo de datos y la arquitectura permitirán ingesta multianual en v2.

**Solo lectura:** No hay endpoints de escritura hacia SIGA/SIAF. Toda persistencia adicional va a PostgreSQL.

---

## 2. Reglas de negocio globales

### RN-01 · Semáforos configurables

Todo indicador de ejecución presupuestal se colorea según umbrales por módulo, configurables por Decisores/Admin. Valores por defecto sugeridos:

| Estado | Regla por defecto |
|---|---|
| Verde | Ejecución ≥ 90% del avance esperado para el periodo |
| Amarillo | Entre 60% y 89% |
| Rojo | Menor a 60% |

**Avance esperado por trimestre (base para el cálculo):** Q1 25%, Q2 50%, Q3 75%, Q4 100%.

Los umbrales se guardan en tabla `configuracion_semaforos` (por módulo, por rol). Cambios quedan en log de auditoría.

### RN-02 · Alertas del MVP

| Alerta | Condición | Configurable |
|---|---|---|
| **Pedido estancado** | `SIG_PEDIDOS` en un estado > X días sin cambio en `SIG_SEGUIMIENTO` | X (default: 15) |
| **Contrato por vencer** | `SIG_CONTRATOS.FECHA_FINAL - hoy` ≤ Y días | Y (default: 30) |
| **Meta con baja ejecución** | Devengado < Z% del PIM en el trimestre actual | Z (default: 50% en Q3) |

### RN-03 · Fuentes autoritativas

Cuando el mismo dato existe en varias fuentes, se usa siempre la fuente definida como autoritativa:

| Dato | Fuente autoritativa |
|---|---|
| PIM | `SIG_TECHO_PRESUPUESTO.PPTO_MODIF` |
| PIA | `SIG_TECHO_PRESUPUESTO.PPTO_PIA` (el de SIAF viene en 0) |
| Saldo disponible | `SIG_TECHO_PRESUPUESTO.PPTO_DISP_SIAF` |
| Devengado | `SIG_TECHO_PRESUPUESTO.MNTO_ACUM_DEVGDO_SIGA` o `ESTADO_SIAF='2'` en la orden |
| Avance físico de obra | Invierte.pe `AVANCE_FISICO` |
| Ejecución mensual | SIAF `MES_EJE` para dashboards agregados |

### RN-04 · Filtro por Centro de Costo (Operativos y Decisores)

- **Operativo:** ve únicamente los datos donde `CENTRO_COSTO` está en su lista asignada.
- **Decisor:** ve los datos de todos los `CENTRO_COSTO` cuyo `CENTRO_PADRE` (directa o transitivamente) coincide con su alcance.
- **Admin:** sin filtro.

### RN-05 · Registro en logs de auditoría

Se registra en `logs_auditoria` (PostgreSQL) cada:
- Login/logout de funcionarios
- Exportación de reportes (usuario, filtro, formato, timestamp)
- Cambio de umbrales/alertas
- Publicación de observación ciudadana

---

## 3. Módulo 1 — Portal de Obras (público)

### HU-01 · Listado de obras del distrito · **M**

**Como** ciudadano
**quiero** ver el listado de obras públicas del distrito con su estado
**para** conocer en qué se invierte el presupuesto y su avance.

**Criterios de aceptación:**
- AC-01.1: La página carga sin login.
- AC-01.2: Se listan los 70 proyectos activos (`TIPO_ACT_PROY = '2'`) de la Municipalidad para 2026.
- AC-01.3: Cada tarjeta muestra: nombre, código único, función, avance físico (barra), avance financiero, tipología, modalidad.
- AC-01.4: Filtros disponibles: función presupuestal, tipología, modalidad (contrata/admin. directa), estado del semáforo, texto libre.
- AC-01.5: Ordenamiento: por PIM, por avance físico, por fecha de inicio, alfabético.
- AC-01.6: Cada tarjeta enlaza a la ficha detallada (HU-02).

**Reglas de negocio:**
- RN-01 (semáforos por avance físico), RN-03 (fuentes autoritativas), datos combinados de Invierte.pe + `SIG_TECHO_PRESUPUESTO`.

**Mockup textual:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ Portal de Transparencia · Municipalidad de San Jerónimo             │
│ [Obras] [Ejecución] [Proveedores]                                    │
├──────────────────────────────────────────────────────────────────────┤
│ Obras Públicas 2026                                                  │
│                                                                       │
│ [ Buscar...  🔍 ] [Función ▼] [Tipología ▼] [Modalidad ▼] [Estado ▼]│
│                                                    Ordenar por [PIM▼]│
│                                                                       │
│ ┌─────────────────────────┐ ┌─────────────────────────┐              │
│ │ 🟢 Movilidad Urbana AV  │ │ 🟡 Mejoramiento I.E.    │              │
│ │ 2669624                 │ │ 2235850                 │              │
│ │ TRANSPORTE · CONTRATA   │ │ EDUCACION · CONTRATA    │              │
│ │ Físico ████████░ 82%    │ │ Físico ████░░░░░ 45%    │              │
│ │ Financiero ███████ 75%  │ │ Financiero ████░░░ 41%  │              │
│ │ PIM S/ 1,234,567        │ │ PIM S/ 890,000          │              │
│ │ [Ver ficha →]           │ │ [Ver ficha →]           │              │
│ └─────────────────────────┘ └─────────────────────────┘              │
│ ... (paginación 12 por página)                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

### HU-02 · Ficha detallada de una obra · **M**

**Como** ciudadano
**quiero** consultar la ficha completa de una obra
**para** conocer todos los datos disponibles: presupuesto, avance, contratista, plazos, ubicación y documentos.

**Criterios de aceptación:**
- AC-02.1: La ficha carga en <2 s con datos de Invierte.pe + SIAF + SIGA cruzados.
- AC-02.2: Muestra secciones: identificación, presupuesto, avance físico y financiero, contratista, cronograma, ubicación (mini-mapa), documentos, fotografías.
- AC-02.3: El bloque de contratista muestra RUC, razón social, monto total contratado (suma `SIG_CONTRATOS.VALOR_SOLES` del proyecto).
- AC-02.4: Enlace de descarga de documentos públicos si están cargados por funcionarios (F8, F9, expediente técnico, contrato).
- AC-02.5: Botón "Registrar observación" abre el buzón ciudadano (HU-24).

**Reglas de negocio:**
- Fuente principal: Invierte.pe (por `CODIGO_UNICO`) + `SIG_CONTRATOS` (por `NRO_CONTRATO`) + `SIG_TECHO_PRESUPUESTO` para el PIM y saldos.
- Solo datos públicos: no exponer nombres de empleados internos ni observaciones no publicadas.

**Mockup textual:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ ← Volver al listado                                                  │
│                                                                       │
│ Movilidad Urbana AV. Cantaritos                                      │
│ Código único: 2637963 · TRANSPORTE · CONTRATA · Estado: 🟢          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ ┌─ AVANCE ────────────┐  ┌─ PRESUPUESTO ────────┐                   │
│ │ Físico    82% ████░ │  │ PIA           S/  0  │                   │
│ │ Financ.   75% ████░ │  │ PIM      1,234,567   │                   │
│ │ Etapa: C (Ejec.)    │  │ Certificado  980,000 │                   │
│ │ Modalidad: CONTRATA │  │ Devengado    920,000 │                   │
│ └─────────────────────┘  │ Girado       850,000 │                   │
│                          └──────────────────────┘                   │
│                                                                       │
│ ┌─ CONTRATISTA ────────────────────────────────┐                    │
│ │ RUC 20xxxxxxxxx · Constructora ABC S.A.C.    │                    │
│ │ Monto contratado: S/ 1,180,000                │                    │
│ │ Contrato N° 015-2025 · Modalidad AS           │                    │
│ └────────────────────────────────────────────────┘                    │
│                                                                       │
│ ┌─ CRONOGRAMA ────────────────────────────────┐                     │
│ │ Inicio contractual: 2025-03-15               │                     │
│ │ Fin contractual:    2026-08-30               │                     │
│ │ Inicio físico:      2025-04-02               │                     │
│ │ Último devengado:   2026-07-05               │                     │
│ └───────────────────────────────────────────────┘                    │
│                                                                       │
│ ┌─ UBICACIÓN ──┐  ┌─ DOCUMENTOS ─────────────┐                      │
│ │ [Mini-mapa]  │  │ 📄 Expediente Técnico     │                      │
│ │ -13.5, -71.9 │  │ 📄 Formato F8             │                      │
│ │ San Jerónimo │  │ 📄 Contrato firmado       │                      │
│ └──────────────┘  └───────────────────────────┘                      │
│                                                                       │
│ ┌─ FOTOGRAFÍAS ────────────────────────────────┐                     │
│ │ [foto 1] [foto 2] [foto 3]                    │                     │
│ └────────────────────────────────────────────────┘                    │
│                                                                       │
│                                       [ Registrar observación ]      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### HU-03 · Carga de fotografías y documentos por funcionario · **S**

**Como** funcionario operativo del área de obras
**quiero** subir fotografías del avance de una obra y documentos públicos
**para** enriquecer la ficha pública sin salir del sistema.

**Criterios de aceptación:**
- AC-03.1: El botón "Editar ficha pública" solo aparece autenticado con permiso.
- AC-03.2: Se aceptan JPG/PNG máx 5 MB por foto, hasta 20 fotos por proyecto.
- AC-03.3: Documentos: PDF máx 20 MB, hasta 10 por proyecto.
- AC-03.4: Cada archivo se etiqueta con: proyecto, tipo, fecha, subido por.
- AC-03.5: Los archivos se almacenan en filesystem local del servidor, metadatos en tabla `documentos_obra`.
- AC-03.6: La publicación es inmediata; puede despublicarse pero queda en log.

**Reglas de negocio:**
- RN-05 (auditoría), permisos por `CENTRO_COSTO`.

**Mockup textual:**

```
┌── Editar ficha pública: Movilidad Urbana AV. Cantaritos ───────────┐
│                                                                     │
│ Fotografías (5/20)                                                  │
│ [+] Subir fotos    [🗑] Eliminar seleccionadas                     │
│ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐                                            │
│ │📷│ │📷│ │📷│ │📷│ │📷│                                            │
│ └──┘ └──┘ └──┘ └──┘ └──┘                                            │
│                                                                     │
│ Documentos (3/10)                                                   │
│ [+] Subir documento                                                 │
│ 📄 Expediente Técnico v2.pdf   · 2026-05-12 · [Eliminar]           │
│ 📄 Formato F8 aprobado.pdf     · 2026-06-01 · [Eliminar]           │
│ 📄 Contrato N° 015-2025.pdf    · 2025-03-14 · [Eliminar]           │
│                                                                     │
│                             [ Guardar cambios ]  [ Cancelar ]       │
└─────────────────────────────────────────────────────────────────────┘
```

---

### HU-04 · Mapa de obras · **M**

**Como** ciudadano
**quiero** ver todas las obras en un mapa del distrito
**para** ubicar geográficamente en qué zonas se está invirtiendo.

**Criterios de aceptación:**
- AC-04.1: Mapa base Leaflet + OpenStreetMap centrado en San Jerónimo.
- AC-04.2: Se dibujan marcadores para los proyectos con `LATITUD`/`LONGITUD` (~58 de 70).
- AC-04.3: Los proyectos sin coordenadas se listan aparte con un aviso.
- AC-04.4: Color del marcador según semáforo (RN-01) aplicado al avance físico.
- AC-04.5: Filtros: función, tipología, avance (rango), estado.
- AC-04.6: Popup en cada marcador con: nombre, avance físico, PIM y enlace a ficha (HU-02).
- AC-04.7: Botón "Ver como lista" alterna a HU-01.

**Reglas de negocio:**
- RN-01 (semáforos), RN-03 (fuentes).

**Mockup textual:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ Mapa de Obras 2026 · San Jerónimo — Cusco                           │
│ [Función▼] [Tipología▼] [Avance 0-100 ━━●━━] [Estado▼]  [Lista ↔]  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│                          🟢       🟡                                  │
│         🟢                    🔴         🟢                           │
│                🟡   🟢                       🟡                        │
│      🟢                🔴          🟢                                  │
│                                                                       │
│                    ┌── Popup activo ─────────────┐                   │
│                    │ 2669624 Manantiales         │                   │
│                    │ TRANSPORTE · 🟢 82%          │                   │
│                    │ PIM: S/ 1,234,567           │                   │
│                    │ [Ver ficha →]               │                   │
│                    └──────────────────────────────┘                   │
│                                                                       │
│ Sin coordenadas (12): 2xxxxxx, 2xxxxxx, 2xxxxxx, ...                 │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Módulo 2 — Dashboard general de ejecución (público)

### HU-05 · Vista general de ejecución presupuestal · **M**

**Como** ciudadano
**quiero** ver un dashboard con la ejecución presupuestal total del distrito
**para** entender cómo se está gastando el presupuesto del año.

**Criterios de aceptación:**
- AC-05.1: KPIs superiores: PIM total, Certificado, Devengado, Girado, % ejecución.
- AC-05.2: Gráfico de barras horizontales: ejecución por función presupuestal.
- AC-05.3: Gráfico de dona: distribución del PIM por fuente de financiamiento.
- AC-05.4: Gráfico de línea: devengado mensual acumulado (MES_EJE 1 al mes actual).
- AC-05.5: Filtros: función, fuente de financiamiento, categoría de gasto, mes.
- AC-05.6: Todas las cifras enlazan a la tabla detallada (HU-06).

**Reglas de negocio:**
- Fuente principal: `SIG_TECHO_PRESUPUESTO` para totales; SIAF para el corte mensual.
- Solo lectura pública, sin filtro por centro de costo.

**Mockup textual:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ Ejecución Presupuestal 2026                                          │
│ [Función▼] [Fuente▼] [Categoría▼] [Mes: Julio ▼]  🔄 Actualizado hoy│
├──────────────────────────────────────────────────────────────────────┤
│ ┌─ PIM ─────┐ ┌─ CERTIFIC.─┐ ┌─ DEVENGADO ┐ ┌─ GIRADO ─┐ ┌─ % ──┐  │
│ │ S/ 45.2M  │ │ S/ 32.1M   │ │ S/ 27.8M   │ │ S/ 24.6M │ │ 61%  │  │
│ └───────────┘ └────────────┘ └────────────┘ └──────────┘ └──────┘  │
│                                                                       │
│ Ejecución por Función                    Fuentes de Financiamiento   │
│ TRANSPORTE     ████████████░ 82%         ┌──────────────────┐        │
│ SANEAMIENTO   ██████░░░░░░ 45%           │  ⬤ Canon (42%)  │        │
│ EDUCACION     ████████░░░░ 61%           │  ⬤ FONCOMUN 28%│        │
│ AGROPECUARIA  ████░░░░░░░░ 32%           │  ⬤ RO       18%│        │
│ ...                                       │  ⬤ Otros    12%│        │
│                                           └──────────────────┘        │
│                                                                       │
│ Devengado mensual acumulado                                           │
│ 30M ┤                                          ╭──                    │
│ 20M ┤                             ╭────────────                       │
│ 10M ┤            ╭────────────────                                    │
│  0M ┴─────────────────────────────────────────────                    │
│      Ene Feb Mar Abr May Jun Jul                                     │
└──────────────────────────────────────────────────────────────────────┘
```

---

### HU-06 · Tabla detallada de ejecución con filtros · **M**

**Como** ciudadano
**quiero** consultar la tabla detallada de ejecución con capacidad de filtrar y ordenar
**para** encontrar el detalle específico que me interesa.

**Criterios de aceptación:**
- AC-06.1: Tabla con columnas: función, programa, producto/proyecto, meta, PIM, certificado, devengado, girado, % ejecución.
- AC-06.2: Filtros combinables: función, categoría de gasto, fuente, meta.
- AC-06.3: Ordenamiento por cualquier columna numérica.
- AC-06.4: Paginación 25/50/100 registros por página.
- AC-06.5: Botón de exportación (visible para funcionarios; ciudadano ve CSV público limitado).

**Mockup textual:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ Detalle de Ejecución                     [Función▼][Categ▼][Fuente▼]│
├──────────────────────────────────────────────────────────────────────┤
│ Función    │ Meta      │ Nombre         │ PIM ↓    │ Devengado │ %  │
│ TRANSPORTE │ 00121     │ Manantiales    │ 1,234,567│  920,000  │75% │
│ TRANSPORTE │ 00087     │ Portada Valle  │   987,654│  740,000  │75% │
│ SANEAMIENTO│ 00042     │ JAAS Agua      │   876,543│  350,000  │40% │
│ EDUCACION  │ 00018     │ Rosario Fe A.  │   765,432│  460,000  │60% │
│ ...        │           │                │          │           │    │
│                                                                       │
│              Mostrando 25 de 741 · [1] [2] [3] ... [30] →           │
└──────────────────────────────────────────────────────────────────────┘
```

---

### HU-07 · Directorio de proveedores público · **S**

**Como** ciudadano
**quiero** consultar el listado de proveedores adjudicados con la municipalidad
**para** conocer con quién contrata la entidad y por qué montos.

**Criterios de aceptación:**
- AC-07.1: Tabla: RUC, razón social, cantidad de órdenes en el año, monto acumulado, rubros principales.
- AC-07.2: Buscador por RUC o nombre.
- AC-07.3: Enlaza al perfil detallado con historial (HU-19).
- AC-07.4: No expone datos de contacto (email, teléfono) en la vista pública.

**Mockup textual:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ Proveedores Adjudicados 2026                            [Buscar 🔍] │
├──────────────────────────────────────────────────────────────────────┤
│ RUC          │ Razón Social            │ Órdenes │ Monto S/    │... │
│ 20xxxxxxxxx  │ Constructora ABC        │   47    │ 3,450,000   │→   │
│ 20xxxxxxxxx  │ Servicios XYZ           │   32    │ 1,890,000   │→   │
│ 10xxxxxxxxx  │ Juan Pérez (Natural)    │   12    │   240,000   │→   │
│ ...          │                         │         │             │    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 5. Módulo 3 — Pipeline de pedidos y órdenes (interno)

### HU-08 · Login de funcionario · **M**

**Como** funcionario
**quiero** ingresar con mi usuario y contraseña
**para** acceder al panel interno según mi rol.

**Criterios de aceptación:**
- AC-08.1: Formulario con usuario y contraseña. Sin registro público.
- AC-08.2: Autenticación contra tabla `usuarios` en PostgreSQL. Hash bcrypt.
- AC-08.3: Sesión con JWT (expiración 8 horas). Renovación silenciosa.
- AC-08.4: Bloqueo tras 5 intentos fallidos en 15 minutos.
- AC-08.5: Log en `logs_auditoria` de login exitoso/fallido.
- AC-08.6: Al entrar, redirige al dashboard adecuado según rol.

**Reglas de negocio:**
- RN-04 (filtro por centro de costo aplicable a partir del login), RN-05 (auditoría).

**Mockup textual:**

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Sistema de Gestión y Transparencia                 │
│                    Municipalidad de San Jerónimo                     │
│                                                                       │
│                    Usuario     [___________________]                  │
│                    Contraseña  [___________________]                  │
│                                                                       │
│                                    [  Ingresar  ]                     │
│                                                                       │
│                    ¿Olvidó su contraseña? Contacte al admin.         │
└──────────────────────────────────────────────────────────────────────┘
```

---

### HU-09 · Tablero pipeline por estado · **M**

**Como** funcionario operativo
**quiero** ver todos los pedidos de mi unidad organizados por su etapa actual
**para** identificar dónde están y qué requieren para avanzar.

**Criterios de aceptación:**
- AC-09.1: Vista tipo Kanban con 5 columnas: Solicitado, Con orden, En conformidad, Devengado, Cerrado.
- AC-09.2: Cada tarjeta muestra: N° pedido, tipo (B/S), monto, solicitante, días en estado actual.
- AC-09.3: Filtros: tipo (bien/servicio), rango de fechas, área usuaria (si tiene permiso), proveedor.
- AC-09.4: Clic en tarjeta abre el detalle (HU-10).
- AC-09.5: Aplicar filtro por `CENTRO_COSTO` según rol (RN-04).
- AC-09.6: Indicador visual (borde rojo) si el pedido supera el umbral configurado (alerta pedido estancado, RN-02).

**Mockup textual:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ Pipeline de Pedidos                      [Tipo▼][Fechas][Buscar 🔍] │
├──────────────────────────────────────────────────────────────────────┤
│ Solicitado (23) │ Con orden (41) │ Conformidad (12) │ Devengado (28)│
│ ┌─────────────┐ │┌─────────────┐│┌─────────────┐│┌─────────────┐   │
│ │N° 234-2026 B│ │N° 198-2026 S ││N° 155-2026 B ││N° 122-2026 S│   │
│ │S/ 12,450    │ │S/ 8,900     ││S/ 34,200    ││S/ 5,600     │   │
│ │Sub. Obras   │ │Log.         ││Salud        ││Educ.        │   │
│ │📅 3 días    │ │📅 12 días   ││📅 8 días    ││📅 45 días   │   │
│ └─────────────┘ │└─────────────┘│└─────────────┘│└─────────────┘   │
│ ┌─────────────┐ │┌─────────────┐│                                   │
│ │N° 235-2026 S│ │⚠️ 199-2026 B││                                   │
│ │📅 18 días⚠️│ │📅 21 días⚠️││                                   │
│ └─────────────┘ │└─────────────┘│                                   │
└──────────────────────────────────────────────────────────────────────┘
```

---

### HU-10 · Detalle de un pedido/orden · **M**

**Como** funcionario
**quiero** consultar el detalle completo de un pedido con su orden asociada
**para** entender el estado real y qué falta.

**Criterios de aceptación:**
- AC-10.1: Muestra cabecera del pedido (`SIG_PEDIDOS`) y todos sus ítems (`SIG_DETALLE_PEDIDOS`).
- AC-10.2: Si tiene orden emitida, muestra bloque de orden (`SIG_ORDEN_ADQUISICION`), afectación presupuestal, proveedor y conformidad.
- AC-10.3: Timeline con las fechas de cada estado (`SIG_SEGUIMIENTO`).
- AC-10.4: Botón "Anotar observación interna" persiste texto en `anotaciones_internas` (PostgreSQL).
- AC-10.5: Botón "Ver ejecución SIAF" enlaza al módulo de cruce (HU-16) filtrado por el `EXP_SIAF`.

**Mockup textual:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ ← Volver al pipeline                                                 │
│                                                                       │
│ Pedido N° 199-2026 · BIEN · Solicitante: Sub. Obras Públicas         │
│ Estado: 🟡 Con orden emitida · 21 días en este estado ⚠️            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ ┌─ PEDIDO ─────────────────────────────────────────┐                │
│ │ Fecha pedido: 2026-06-15                          │                │
│ │ Aprobado:     2026-06-18                          │                │
│ │ Meta 00121 (Movilidad Urbana Cantaritos)          │                │
│ │ Ítems: 3                                          │                │
│ │                                                    │                │
│ │ Ítem │ Descripción      │ Cant. │ Valor S/       │                │
│ │  1   │ Cemento Portland │ 200   │ 8,400          │                │
│ │  2   │ Fierro corrug.   │ 500   │ 12,500         │                │
│ │  3   │ Agregado grueso  │ 30 m³ │ 4,500          │                │
│ └────────────────────────────────────────────────────┘                │
│                                                                       │
│ ┌─ ORDEN ───────────────────────────────────────────┐                │
│ │ N° 187-2026 B · Estado SIAF: 0 (pendiente)        │                │
│ │ Proveedor: Constructora ABC (RUC 20xxxxxxxxx)     │                │
│ │ EXP_SIAF: 456789                                   │                │
│ │ Monto total: S/ 25,400                             │                │
│ │ [Ver ejecución SIAF →]                             │                │
│ └────────────────────────────────────────────────────┘                │
│                                                                       │
│ ┌─ TIMELINE ────────────────────────────────────────┐                │
│ │ 2026-06-15 · Solicitado                            │                │
│ │ 2026-06-18 · Aprobado                              │                │
│ │ 2026-06-30 · Orden emitida                         │                │
│ │ ⏳ Esperando conformidad...                        │                │
│ └────────────────────────────────────────────────────┘                │
│                                                                       │
│ ┌─ OBSERVACIONES INTERNAS ─────────────────────────┐                 │
│ │ [+] Nueva observación                             │                │
│ │ 2026-07-02 · J.Perez: "Se solicitó ampliación..." │                │
│ └────────────────────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────────────────┘
```

---

### HU-11 · Alerta de pedidos estancados · **M**

**Como** funcionario operativo
**quiero** recibir alertas de los pedidos de mi unidad que llevan más de X días sin avance
**para** desatorar el flujo.

**Criterios de aceptación:**
- AC-11.1: Widget en el dashboard interno con conteo de alertas del usuario.
- AC-11.2: Lista de pedidos que superan el umbral (default 15 días, configurable por Decisor/Admin).
- AC-11.3: Clic en cada alerta abre el detalle del pedido (HU-10).
- AC-11.4: Se puede marcar como "revisada" (persiste en `alertas_revisadas`).

**Reglas de negocio:**
- RN-02 (alertas), RN-04 (alcance por CC).

**Mockup textual:**

```
┌── Mis alertas (7) ──────────────────────────────────────────────────┐
│ ⚠️ Pedidos estancados                                                │
│ ─────────────────────                                                │
│ N° 199-2026 B · 21 días en "Con orden"          [Ver] [Marcar ✓]   │
│ N° 187-2026 S · 18 días en "Solicitado"         [Ver] [Marcar ✓]   │
│ N° 178-2026 B · 32 días en "Conformidad"        [Ver] [Marcar ✓]   │
│ ...                                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Módulo 4 — Cruce SIAF-SIGA (interno)

### HU-12 · Buscador por expediente SIAF · **M**

**Como** funcionario
**quiero** buscar por número de expediente SIAF
**para** ver de golpe todos los registros SIGA y datos de la meta asociada.

**Criterios de aceptación:**
- AC-12.1: Campo de búsqueda por `EXP_SIAF`. Autocompleta desde los existentes.
- AC-12.2: Resultado muestra: meta asociada, orden(es), pedido origen, conformidad, proveedor.
- AC-12.3: Enlaces a los detalles de cada componente.
- AC-12.4: Si el `EXP_SIAF` no existe en SIGA, mensaje claro con sugerencia de intentar por SEC_FUNC.

**Reglas de negocio:**
- Consulta a `SIG_ORDEN_PRESUPUESTO` y join con las tablas relacionadas (ver diccionario sección 17.1).

**Mockup textual:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ Cruce SIAF-SIGA · Buscador                                           │
│                                                                       │
│ Expediente SIAF: [ 456789    ]  [🔍 Buscar]                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Expediente 456789 encontrado.                                         │
│                                                                       │
│ ┌─ META ───────────────────────────────────────┐                    │
│ │ SEC_FUNC 12345 · Meta 00121                   │                    │
│ │ Movilidad Urbana AV. Cantaritos               │                    │
│ │ TRANSPORTE · Fuente: Canon                    │                    │
│ │ [Ver ejecución completa de la meta →]        │                    │
│ └───────────────────────────────────────────────┘                    │
│                                                                       │
│ ┌─ ÓRDENES (2) ─────────────────────────────────┐                    │
│ │ N° 187-2026 B · S/ 25,400 · Constructora ABC │                    │
│ │ N° 192-2026 S · S/ 8,000  · Servicios XYZ    │                    │
│ └───────────────────────────────────────────────┘                    │
│                                                                       │
│ ┌─ PEDIDOS ORIGEN ─────────────────────────────┐                    │
│ │ N° 199-2026 B · Sub. Obras Públicas          │                    │
│ └───────────────────────────────────────────────┘                    │
│                                                                       │
│ ┌─ CONFORMIDAD ────────────────────────────────┐                    │
│ │ Pendiente                                     │                    │
│ └───────────────────────────────────────────────┘                    │
└──────────────────────────────────────────────────────────────────────┘
```

---

### HU-13 · Vista consolidada por meta · **M**

**Como** funcionario decisor
**quiero** ver una vista consolidada de una meta con todos sus componentes
**para** tener contexto financiero y operativo en un solo lugar.

**Criterios de aceptación:**
- AC-13.1: Al ingresar un `SEC_FUNC` o seleccionar de un listado, se muestra: cabecera de META, PIM, ejecución SIAF (certificado/comprometido/devengado/girado), listado de órdenes SIGA, certificaciones, conformidades, saldo disponible.
- AC-13.2: Cada componente es expandible (acordeón) para ver detalle.
- AC-13.3: Semáforo de ejecución financiera con umbrales configurados (RN-01).
- AC-13.4: Exportable a Excel + PDF.

**Reglas de negocio:**
- RN-01, RN-03 (fuentes autoritativas), RN-04 (filtro por CC).

**Mockup textual:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ Vista consolidada · Meta 00121 (SEC_FUNC 12345)                     │
│ Movilidad Urbana AV. Cantaritos · TRANSPORTE                        │
│                                                    [Exportar Excel▼]│
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ ┌─ PRESUPUESTO ──────────────────────────────────────────┐          │
│ │ PIA        │  PIM       │ Certificado │ Devengado │ %  │          │
│ │ S/ 0       │ 1,234,567  │  980,000    │  920,000  │75% │ 🟢       │
│ │ Saldo disponible: S/ 254,567                            │          │
│ └────────────────────────────────────────────────────────┘          │
│                                                                       │
│ ▼ ÓRDENES SIGA (12) ─────── S/ 1,050,000 ──────────                 │
│    N° 187-2026 B · Constr. ABC · S/ 25,400 · SIAF: 0                │
│    N° 192-2026 S · XYZ        · S/  8,000 · SIAF: 2                │
│    N° 201-2026 B · ABC        · S/ 45,000 · SIAF: 2                │
│    ... (9 más)                                                       │
│                                                                       │
│ ▶ CERTIFICACIONES (18)     S/ 980,000                                │
│ ▶ CONFORMIDADES (14)                                                 │
│ ▶ PEDIDOS ORIGEN (15)                                                │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

### HU-14 · Drill-down bidireccional · **S**

**Como** funcionario
**quiero** desde cualquier registro navegar hacia arriba o abajo en la cadena
**para** rastrear la trazabilidad completa sin abrir varias pantallas.

**Criterios de aceptación:**
- AC-14.1: En cualquier tabla del cruce, cada fila incluye botones "↑ Ir a meta", "↑ Ir a orden", "↓ Ver ítems", "↓ Ver conformidad".
- AC-14.2: Los enlaces preservan el filtro (año, entidad).
- AC-14.3: Migas de pan (breadcrumbs) muestran el camino navegado.

**Mockup textual:**

```
Meta 00121 › Orden 187-2026 B › Ítem 2 (Fierro corrugado)

┌── Detalle ítem ─────────────────────────────────────────┐
│ [↑ Ir a orden] [↑ Ir a meta] [↓ Ver movimientos almacén]│
│                                                          │
│ Fierro corrugado 5/8" x 12m                             │
│ Cantidad: 500 unidades · Precio: S/ 25.00               │
│ Total: S/ 12,500                                         │
│ Clasificador: 2.3.1 6.1 1                               │
└─────────────────────────────────────────────────────────┘
```

---

## 7. Módulo 5 — Saldos presupuestales (interno)

### HU-15 · Consulta de saldo por meta y clasificador · **M**

**Como** funcionario operativo
**quiero** consultar el saldo disponible de una meta por clasificador
**para** saber si tengo margen antes de generar un pedido.

**Criterios de aceptación:**
- AC-15.1: Filtros: meta (SEC_FUNC), clasificador, fuente, centro de costo.
- AC-15.2: Tabla con: PIM, certificado, comprometido, devengado, saldo disponible, monto reservado por pedidos pendientes.
- AC-15.3: Semáforo del saldo: verde si >20%, amarillo 5-20%, rojo <5% (umbrales configurables).
- AC-15.4: Aplicar filtro por CC según rol (RN-04).
- AC-15.5: Exportable Excel + PDF.

**Reglas de negocio:**
- Fuente: `SIG_TECHO_PRESUPUESTO`. Fórmula preferida: `PPTO_DISP_SIAF` directo.

**Mockup textual:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ Saldos Presupuestales                    [Meta▼][Clas▼][Fuente▼]    │
├──────────────────────────────────────────────────────────────────────┤
│ Meta  │ Clasif.       │ Fuente │ PIM     │ Devengado │ Saldo  │ %  │
│ 00121 │ 2.3.1 5.1 2   │ Canon  │ 250,000 │ 180,000   │ 55,000 │22%🟢│
│ 00121 │ 2.6.2 3.4 1   │ Canon  │ 890,000 │ 750,000   │ 45,000 │ 5%🟡│
│ 00087 │ 2.3.2 2.1 5   │ RO     │ 120,000 │ 118,000   │  2,000 │ 2%🔴│
│ ...   │               │        │         │           │        │    │
│                                                                       │
│                          [ 📥 Exportar Excel ]  [ 📄 Exportar PDF ] │
└──────────────────────────────────────────────────────────────────────┘
```

---

### HU-16 · Alerta de metas con baja ejecución · **M**

**Como** funcionario decisor
**quiero** identificar rápidamente las metas de mi gerencia que están rezagadas
**para** tomar medidas correctivas.

**Criterios de aceptación:**
- AC-16.1: Panel muestra las metas con devengado por debajo del umbral esperado según el trimestre.
- AC-16.2: Umbral configurable (default: <50% en Q3).
- AC-16.3: Cada meta en la alerta enlaza a la vista consolidada (HU-13).
- AC-16.4: Aplicar RN-04 según jerarquía del decisor.

**Reglas de negocio:**
- RN-01, RN-02, RN-04.

**Mockup textual:**

```
┌── Metas rezagadas (12) ─── Q3 2026 · Umbral: 50% ──────────────────┐
│                                                                     │
│ SEC_FUNC │ Meta                       │ PIM        │ Dev.  │ %    │
│ 12345    │ Riego Picol Orccompucyo    │ 2,340,000  │ 340k  │ 15% 🔴│
│ 12876    │ Sistema Bibliotecarios     │ 1,450,000  │ 580k  │ 40% 🔴│
│ 13122    │ Recup. Servicios Cult.     │ 1,070,000  │ 480k  │ 45% 🔴│
│ ...                                                                 │
│                                                                     │
│ [ Ver todas las metas rezagadas → ]                                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 8. Módulo 6 — Autenticación y roles

### HU-17 · Gestión de usuarios y roles · **M**

**Como** administrador
**quiero** crear, editar y desactivar usuarios asignándoles rol y centros de costo
**para** controlar el acceso al sistema.

**Criterios de aceptación:**
- AC-17.1: CRUD de usuarios con campos: usuario, nombre, email, rol, centros de costo asignados, estado.
- AC-17.2: Cambio de contraseña obligatorio en el primer login.
- AC-17.3: Un Operativo puede tener 1+ `CENTRO_COSTO`. Un Decisor tiene su nodo raíz + descendientes.
- AC-17.4: Auditoría de cambios en `logs_auditoria`.
- AC-17.5: Solo Admin ve este módulo.

**Mockup textual:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ Gestión de Usuarios                                    [+ Nuevo]     │
├──────────────────────────────────────────────────────────────────────┤
│ Usuario   │ Nombre        │ Rol       │ Centros CC     │ Estado    │
│ jperez    │ José Pérez    │ Operativo │ CC-023, CC-041 │ Activo  ✏│
│ mrojas    │ María Rojas   │ Decisor   │ CC-010 (+15)   │ Activo  ✏│
│ jlopez    │ Juan López    │ Admin     │ Todos          │ Activo  ✏│
│ ...       │               │           │                │            │
└──────────────────────────────────────────────────────────────────────┘

┌── Nuevo usuario ────────────────────────────────────────────────────┐
│ Usuario:         [_______________]                                   │
│ Nombre completo: [_______________]                                   │
│ Email:           [_______________]                                   │
│ Rol:             [Operativo ▼]                                       │
│ Centros de costo:[+] CC-023, CC-041                                  │
│                                                                       │
│                                     [ Crear ]  [ Cancelar ]          │
└─────────────────────────────────────────────────────────────────────┘
```

---

### HU-18 · Configuración de umbrales y alertas · **S**

**Como** funcionario decisor o administrador
**quiero** ajustar los umbrales de semáforos y alertas
**para** adaptar el sistema a los criterios de gestión de la entidad.

**Criterios de aceptación:**
- AC-18.1: Pantalla con secciones por módulo (portal obras, saldos, pipeline, cruce).
- AC-18.2: Cada semáforo permite editar los umbrales verde/amarillo/rojo.
- AC-18.3: Cada alerta permite editar el umbral (días para estancado, días antes de vencer contrato, % mínimo por trimestre).
- AC-18.4: Cambios registrados en `logs_auditoria`.
- AC-18.5: Solo Decisor y Admin acceden.

**Mockup textual:**

```
┌── Configuración de umbrales ────────────────────────────────────────┐
│                                                                     │
│ SEMÁFOROS                                                           │
│ ─────────                                                           │
│ Portal de Obras (avance físico)                                     │
│   🟢 Verde   ≥ [ 90 ]%    🟡 Amarillo ≥ [ 60 ]%    🔴 Rojo <60%   │
│                                                                     │
│ Saldos disponibles                                                  │
│   🟢 Verde   > [ 20 ]%    🟡 Amarillo > [  5 ]%    🔴 Rojo ≤5%    │
│                                                                     │
│ ALERTAS                                                             │
│ ────────                                                            │
│ Pedidos estancados                                                  │
│   Umbral de días sin cambio: [ 15 ]                                 │
│                                                                     │
│ Contratos por vencer                                                │
│   Alertar cuando faltan menos de [ 30 ] días                        │
│                                                                     │
│ Metas con baja ejecución                                            │
│   Umbral Q3: [ 50 ]% · Umbral Q4: [ 90 ]%                          │
│                                                                     │
│                       [ Guardar cambios ]  [ Restablecer defaults ] │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 9. Módulos transversales del MVP

### HU-19 · Directorio de proveedores con historial (interno) · **S**

**Como** funcionario
**quiero** consultar el perfil detallado de un proveedor
**para** evaluar su historial de contratación antes de una nueva.

**Criterios de aceptación:**
- AC-19.1: Perfil con: datos de identificación, todas las órdenes (año seleccionable), contratos, cumplimiento de plazos (calculado a partir de `SIG_CONTRATOS.FECHA_FINAL` vs cierre real).
- AC-19.2: Alerta si tiene sanción vigente (`FECHA_FSANCION > hoy`).
- AC-19.3: Ordenes en tabla con: fecha, tipo, monto, estado SIAF.
- AC-19.4: Suma de monto acumulado por año.

**Mockup textual:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ Constructora ABC S.A.C. · RUC 20xxxxxxxxx                            │
│ Jurídica · MYPE: No · RNP: Sí                                        │
│ ⚠️ Sin sanción vigente                                                │
├──────────────────────────────────────────────────────────────────────┤
│ Monto acumulado 2026: S/ 3,450,000 · 47 órdenes                     │
│                                                                       │
│ ┌─ Órdenes ─────────────────────────────────────┐                    │
│ │ Fecha       │ Tipo │ Monto     │ Meta   │ SIAF │                   │
│ │ 2026-06-30  │ B    │  25,400   │ 00121  │ 0    │                   │
│ │ 2026-05-14  │ B    │  45,000   │ 00121  │ 2    │                   │
│ │ 2026-04-22  │ S    │  12,300   │ 00087  │ 2    │                   │
│ │ ...                                                                 │
│ └───────────────────────────────────────────────┘                    │
│                                                                       │
│ ┌─ Contratos ───────────────────────────────────┐                    │
│ │ N° 015-2025 · S/ 1,180,000 · AS · Fin: 2026-08│                    │
│ └───────────────────────────────────────────────┘                    │
└──────────────────────────────────────────────────────────────────────┘
```

---

### HU-20 · Alertas de contratos por vencer · **M**

**Como** funcionario decisor
**quiero** ver los contratos que están próximos a vencer
**para** anticipar renovaciones o cierres.

**Criterios de aceptación:**
- AC-20.1: Widget con listado de contratos con `FECHA_FINAL` a menos de N días (default 30).
- AC-20.2: Muestra: N° contrato, proveedor, objeto, fecha final, días restantes.
- AC-20.3: Umbral configurable.
- AC-20.4: Enlace al detalle del contrato.

**Mockup textual:**

```
┌── Contratos por vencer (5) ─── ≤ 30 días ──────────────────────────┐
│                                                                     │
│ Contrato   │ Proveedor        │ Objeto        │ Fin        │ Días  │
│ 015-2025   │ Constructora ABC │ Obra Cant.   │ 2026-08-30 │  22 ⚠️│
│ 032-2025   │ Servicios XYZ    │ Consultoría  │ 2026-09-15 │  38    │
│ 041-2026   │ Naturales JP     │ Suministros  │ 2026-08-05 │   4 🔴│
│ ...                                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

### HU-21 · Exportación de reportes Excel + PDF · **M**

**Como** funcionario
**quiero** exportar cualquier tabla del sistema a Excel o PDF
**para** compartir la información con mi área o adjuntarla a expedientes.

**Criterios de aceptación:**
- AC-21.1: Botón "Exportar" presente en todas las tablas del panel interno y del dashboard público.
- AC-21.2: Formatos: `.xlsx` (con formato, cabeceras y totales) y `.pdf` (con logo, encabezado, pie con fecha y usuario).
- AC-21.3: El export respeta los filtros aplicados.
- AC-21.4: Cada exportación queda en `logs_auditoria` con usuario, filtro y timestamp.
- AC-21.5: Para reportes grandes (>10K filas), procesar en background y notificar al usuario con enlace de descarga.

**Reglas de negocio:**
- RN-05 (auditoría).

**Mockup textual:**

```
┌── Exportar ─────────────────────────────────────────────────────────┐
│                                                                     │
│ Formato:  ( ) Excel (.xlsx)   ( ) PDF                              │
│                                                                     │
│ Datos incluidos: 1,234 registros (según filtros actuales)          │
│                                                                     │
│ □ Incluir totales al final                                         │
│ □ Incluir gráficos (solo PDF)                                      │
│                                                                     │
│                                     [ Exportar ]  [ Cancelar ]      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### HU-22 · Dashboard de bienvenida del funcionario · **M**

**Como** funcionario
**quiero** ver un dashboard resumen al entrar al sistema
**para** priorizar mi trabajo del día.

**Criterios de aceptación:**
- AC-22.1: Widgets: alertas asignadas (HU-11, HU-16, HU-20), últimos pedidos de mi unidad, KPIs de saldo.
- AC-22.2: Personalización según rol.
- AC-22.3: Acceso rápido a todos los módulos.

**Mockup textual:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ Bienvenido, José Pérez · Sub. Obras Públicas · Operativo             │
├──────────────────────────────────────────────────────────────────────┤
│ ┌─ Alertas ─────────┐ ┌─ Pipeline ────────┐ ┌─ Saldo mi unidad ──┐│
│ │ ⚠️ 3 pedidos       │ │ 8 solicitados     │ │ Saldo disponible   ││
│ │    estancados     │ │ 15 con orden      │ │ S/ 87,540 🟡       ││
│ │ [Ver →]           │ │ [Ver pipeline →]  │ │ [Ver saldos →]    ││
│ └────────────────────┘ └────────────────────┘ └────────────────────┘│
│                                                                       │
│ ┌─ Últimos pedidos de mi unidad ────────────────────────────────┐   │
│ │ N° 234-2026 · S/ 12,450 · Cemento · Estado: Solicitado        │   │
│ │ N° 235-2026 · S/  8,900 · Consultoría · Estado: Con orden     │   │
│ │ N° 236-2026 · S/  3,200 · Papelería · Estado: Conformidad     │   │
│ └────────────────────────────────────────────────────────────────┘   │
│                                                                       │
│ Accesos rápidos: [Pipeline] [Saldos] [Cruce SIAF-SIGA] [Reportes]   │
└──────────────────────────────────────────────────────────────────────┘
```

---

### HU-23 · Actualización nocturna del SIAF · **M**

**Como** sistema (funcionalidad automática)
**necesito** sincronizar los datos SIAF diariamente
**para** mantener el dashboard público al día.

**Criterios de aceptación:**
- AC-23.1: Job programado a las 03:00 diario que consulta la API MEF con `SEC_EJEC=300687` y persiste en `SIG_SIAF_SNAPSHOT`.
- AC-23.2: Mismo job actualiza `SIG_INVIERTEPE_SNAPSHOT` desde el resource `f9cc4ba0`.
- AC-23.3: Si la API falla, se conservan los datos del día anterior y se registra el error.
- AC-23.4: El dashboard público muestra un sello "Actualizado al DD/MM/YYYY".
- AC-23.5: Un log de sincronización queda en `logs_sincronizacion`.

**Reglas de negocio:**
- Estrategia de consulta API MEF: máx 8 columnas por request, `LIMIT 100 OFFSET n` (diccionario sección 18.5).

**Mockup textual:** (no aplica visualización de usuario final)

```
Log de sincronización (Admin):
2026-07-09 03:00:12 · Iniciado job SIAF-SYNC
2026-07-09 03:00:34 · Query 1/12 OK (12,450 filas)
2026-07-09 03:02:18 · Query 12/12 OK
2026-07-09 03:02:20 · Iniciado job INVIERTEPE-SYNC
2026-07-09 03:02:41 · 70 proyectos sincronizados
2026-07-09 03:02:42 · FIN. Total: 148,320 registros SIAF + 70 Invierte.pe
```

---

### HU-24 · Buzón de observaciones ciudadanas con captcha · **C**

**Como** ciudadano
**quiero** dejar una observación sobre una obra pública
**para** hacer llegar mi retroalimentación a la entidad.

**Criterios de aceptación:**
- AC-24.1: Formulario en la ficha de obra con: nombre (opcional), correo (opcional), texto (obligatorio).
- AC-24.2: Captcha (reCAPTCHA v3 o alternativa libre) para evitar spam.
- AC-24.3: Observación se guarda en `observaciones_ciudadanas` con estado "pendiente".
- AC-24.4: Un funcionario del área correspondiente puede marcarla como "leída" o "respondida".
- AC-24.5: Las observaciones publicadas no son visibles al público en el MVP (solo panel interno).

**Reglas de negocio:**
- RN-05 (log de publicación).

**Mockup textual:**

```
┌── Registrar observación · Obra: Movilidad Urbana Cantaritos ───────┐
│                                                                     │
│ Nombre (opcional):    [_______________________]                    │
│ Correo (opcional):    [_______________________]                    │
│                                                                     │
│ Su observación:                                                     │
│ ┌─────────────────────────────────────────────────────────────┐    │
│ │                                                              │    │
│ │                                                              │    │
│ └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│ [I'm not a robot ☐]                                                │
│                                                                     │
│                            [ Enviar observación ]  [ Cancelar ]     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 10. Resumen de historias por prioridad

### Must-have (MVP-crítico) — 15 HU

| ID | Historia | Módulo |
|---|---|---|
| HU-01 | Listado de obras | Portal público |
| HU-02 | Ficha de obra | Portal público |
| HU-04 | Mapa de obras | Portal público |
| HU-05 | Dashboard general | Portal público |
| HU-06 | Tabla detallada de ejecución | Portal público |
| HU-08 | Login funcionario | Auth |
| HU-09 | Pipeline por estado | Pipeline |
| HU-10 | Detalle de pedido/orden | Pipeline |
| HU-11 | Alerta pedidos estancados | Pipeline |
| HU-12 | Buscador por EXP_SIAF | Cruce |
| HU-13 | Vista consolidada por meta | Cruce |
| HU-15 | Consulta de saldos | Saldos |
| HU-16 | Alerta metas rezagadas | Saldos |
| HU-17 | Gestión de usuarios | Auth |
| HU-20 | Contratos por vencer | Alertas |
| HU-21 | Exportación Excel/PDF | Transversal |
| HU-22 | Dashboard bienvenida | Transversal |
| HU-23 | Job sincronización SIAF | Backend |

### Should-have (importante, diferible) — 5 HU

| ID | Historia | Módulo |
|---|---|---|
| HU-03 | Carga de fotos y documentos | Portal público |
| HU-07 | Directorio proveedores público | Portal público |
| HU-14 | Drill-down bidireccional | Cruce |
| HU-18 | Configuración de umbrales | Auth/Config |
| HU-19 | Directorio proveedores interno | Alertas/Proveedores |

### Could-have (opcional) — 1 HU

| ID | Historia | Módulo |
|---|---|---|
| HU-24 | Buzón de observaciones | Portal público |

### Won't (fuera del MVP)

- Comparativo histórico multianual (v2)
- Notificaciones por correo/WhatsApp (v2/backlog)
- Reportes automáticos de transparencia estándar (backlog)
- Integración con SSI del MEF (backlog)
- Semáforos con proyección de cierre (v2)

---

## 11. Pendientes para validación con usuarios

Aunque el MVP se documenta sin validación externa previa, se recomienda validar con al menos un representante de cada perfil antes de arrancar el desarrollo:

- **Operativos de logística:** confirmar el mapeo de etapas del pipeline (HU-09) y umbral de estancamiento (RN-02).
- **Presupuesto/planificación:** validar la vista de saldos (HU-15) y la vista consolidada por meta (HU-13).
- **Gerencia/decisores:** validar las alertas (HU-11, HU-16, HU-20) y umbrales por defecto (RN-01).
- **Áreas usuarias diversas:** validar el flujo de bienvenida (HU-22) y filtros del pipeline (HU-09).

---

## 12. Trazabilidad con la idea principal

| HU | Sección de idea principal |
|---|---|
| HU-01 a HU-04 | 6.1.1 Portal de Obras |
| HU-05 a HU-06 | 6.1.2 Consulta general de ejecución |
| HU-07 | 6.1.3 Directorio proveedores |
| HU-08, HU-17 | 5. Usuarios del sistema |
| HU-09, HU-10, HU-11 | 6.2.2 Seguimiento pedidos/órdenes |
| HU-12, HU-13, HU-14 | 6.2.4 Cruce SIAF-SIGA |
| HU-15, HU-16 | 6.2.3 Saldos presupuestales |
| HU-18 | 6.2.5 Alertas de gestión (parcial) |
| HU-19, HU-20 | 6.2.7 Proveedores con historial + 6.2.5 |
| HU-21 | 6.2.6 Reportes y exportación |
| HU-22 | Panel interno · general |
| HU-23 | 7. Arquitectura técnica |
| HU-24 | 6.1.5 Buzón observaciones |

---

*Documento generado como Actividad 2 — Requerimientos Funcionales · Fase de Diseño · Julio 2026. Se apoya en [idea-principal.md](idea-principal.md) y [diccionario-datos-unificado.md](diccionario-datos-unificado.md).*
