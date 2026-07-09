# Sistema de Transparencia y Gestión Presupuestal

## Municipalidad Distrital de San Jerónimo — Cusco, Perú

**Versión:** 1.0  
**Fecha:** Julio 2026  
**Estado:** Formalización de idea y planificación de fase de diseño

---

## 1. Resumen Ejecutivo

El presente documento formaliza la propuesta de desarrollo de un sistema web que integra dos fuentes de datos institucionales — el SIAF (Sistema Integrado de Administración Financiera), accesible mediante la API de datos abiertos del MEF, y el SIGA (Sistema Integrado de Gestión Administrativa), mediante conexión directa a su base de datos SQL Server — con el propósito de ofrecer una plataforma dual: un portal de transparencia presupuestal orientado a la ciudadanía del distrito de San Jerónimo y un conjunto de herramientas de gestión y análisis para los funcionarios de la entidad.

El sistema tiene como eje central la **visibilización de las obras públicas** y la ejecución presupuestal asociada, respondiendo a la demanda ciudadana más frecuente: saber en qué se invierte el presupuesto público y cuál es el estado real de las obras en su distrito.

---

## 2. Problemática Identificada

La información presupuestal de la Municipalidad Distrital de San Jerónimo se encuentra dispersa en dos sistemas que no se comunican entre sí:

- **SIAF:** Registra la ejecución presupuestal (certificación, compromiso, devengado, girado) pero no contiene el detalle operativo de los procesos logísticos que originan cada gasto.
- **SIGA:** Contiene la trazabilidad operativa — pedidos de compra y servicio, órdenes, conformidades, proveedores — pero no refleja el estado financiero de la ejecución.

Esta desconexión genera las siguientes consecuencias:

- Los ciudadanos no tienen acceso fácil ni comprensible a la información sobre cómo se gasta el presupuesto, especialmente en obras públicas.
- Los funcionarios deben consultar ambos sistemas por separado para rastrear el estado completo de un proceso, desde el requerimiento hasta el pago.
- La gerencia carece de una vista consolidada para la toma de decisiones oportunas sobre ejecución presupuestal y gestión logística.
- El cumplimiento de obligaciones de transparencia se realiza de forma manual y con esfuerzo redundante.

---

## 3. Objetivo General

Desarrollar un sistema web que integre la información presupuestal del SIAF y la información logística del SIGA, ofreciendo a la ciudadanía un portal de transparencia centrado en obras públicas y a los funcionarios herramientas de seguimiento, análisis y reportería para la gestión institucional.

### 3.1 Objetivos Específicos

1. Proveer a la ciudadanía una plataforma accesible para consultar la ejecución presupuestal del distrito, con énfasis en obras públicas: ubicación, presupuesto, avance financiero, contratista y plazos.
2. Integrar los datos del SIAF y SIGA mediante llaves de cruce confiables que permitan vincular la ejecución financiera con los procesos operativos.
3. Ofrecer a los funcionarios tableros de seguimiento de pedidos, alertas de gestión, consulta de saldos presupuestales y reportes consolidados.
4. Generar reportes automatizados que faciliten el cumplimiento de las obligaciones de transparencia de la entidad.
5. Establecer una base tecnológica escalable para incorporar funcionalidades futuras como geolocalización de obras, participación ciudadana y notificaciones.

---

## 4. Fuentes de Datos

### 4.1 SIAF — API de Datos Abiertos del MEF

- **Endpoint:** `https://api.datosabiertos.mef.gob.pe/DatosAbiertos/v1/datastore_search`
- **Consulta SQL:** `https://api.datosabiertos.mef.gob.pe/DatosAbiertos/v1/datastore_search_sql`
- **Resource ID:** `615644aa-ef73-4358-b4e0-0c20931632f3`
- **Contenido:** Ejecución presupuestal diaria por entidad, incluyendo: año fiscal, sector, pliego, unidad ejecutora, categoría presupuestal, producto/proyecto, función, división funcional, grupo funcional, meta, fuente de financiamiento, genérica de gasto, y montos de PIA, PIM, certificación, compromiso anual, compromiso mensual, devengado y girado.
- **Modalidad de acceso:** API REST pública, sin autenticación.

### 4.2 SIGA — Base de Datos SQL Server

- **Motor:** Microsoft SQL Server.
- **Acceso:** Conexión directa desde la misma red local de la entidad.
- **Contenido:** Pedidos de compra y servicio, órdenes de compra y servicio, cuadros de necesidades, catálogo de bienes y servicios, proveedores, conformidades, almacén, entre otros módulos.
- **Autorización:** Se requiere autorización formal de la municipalidad para el acceso y exposición de datos.

### 4.3 Llave de Cruce SIAF ↔ SIGA

La vinculación entre ambas fuentes se realizará mediante la combinación de: año fiscal, meta presupuestal, clasificador de gasto, y el número de expediente SIAF registrado en las órdenes del SIGA. La validación definitiva de estos campos se realizará durante la fase de diseño, al explorar la estructura real de ambas bases de datos.

---

## 5. Usuarios del Sistema

### 5.1 Ciudadano

Acceso público, sin necesidad de registro ni autenticación. Perfil orientado a la transparencia y fiscalización ciudadana. Interés principal: conocer el estado de las obras públicas, los montos involucrados y los responsables de su ejecución.

### 5.2 Funcionario Operativo

Acceso autenticado. Perfil orientado a la gestión diaria: personal de logística, abastecimiento, presupuesto y las áreas usuarias que generan requerimientos. Interés principal: seguimiento de pedidos, consulta de saldos y ejecución presupuestal por clasificador y meta, estado de órdenes y conformidades, y verificación del estado financiero de los procesos que gestionan en el SIGA.

### 5.3 Funcionario Decisor

Acceso autenticado con permisos extendidos. Perfil orientado a la dirección y gerencia: gerente municipal, jefes de oficina de planificación y presupuesto, administración. Interés principal: seguimiento detallado de la ejecución presupuestal (avance por meta, genérica, fuente de financiamiento), indicadores con semáforos, alertas de gestión, reportes comparativos, proyecciones de cierre y cruce de la ejecución financiera con los procesos operativos del SIGA.

---

## 6. Módulos del Sistema

### 6.1 Portal Público — Transparencia Ciudadana

#### 6.1.1 Portal de Obras

Módulo central del sistema. Presenta las obras públicas del distrito como fichas individuales que incluyen: nombre del proyecto o inversión (con código único de inversión), ubicación georreferenciada (barrio, comunidad o sector, con visualización en mapa), presupuesto asignado (PIM), avance de ejecución financiera expresado en porcentaje y desglosado en sus fases (certificado, comprometido, devengado, girado), contratista o proveedor ejecutor, modalidad de ejecución (contrata o administración directa), plazo contractual y fuente de financiamiento.

#### 6.1.2 Consulta General de Ejecución Presupuestal

Dashboard interactivo que permite consultar la ejecución presupuestal de la entidad con filtros por año fiscal, categoría presupuestal, función, genérica de gasto y fuente de financiamiento. Incluye gráficos de avance y tablas de detalle. Cubre todos los tipos de gasto, no solo obras.

#### 6.1.3 Directorio de Proveedores

Listado público de proveedores que han sido adjudicados con órdenes de compra o servicio, con información de montos acumulados y rubros. Orientado a la fiscalización ciudadana.

#### 6.1.4 Comparativo Histórico

Visualización de la ejecución presupuestal comparada entre ejercicios fiscales, identificando tendencias, incrementos o reducciones por genérica de gasto o función.

#### 6.1.5 Buzón de Observaciones Ciudadanas

Canal simple vinculado a la ficha de cada obra, donde el ciudadano puede registrar observaciones o reportes sobre el estado visible de una obra. No constituye un sistema formal de denuncias, sino un mecanismo de retroalimentación para la entidad.

### 6.2 Panel Interno — Gestión para Funcionarios

#### 6.2.1 Ejecución Presupuestal para Gestión Interna

Los funcionarios — especialmente de las oficinas de presupuesto, planificación, administración y gerencia — consultan la ejecución presupuestal de forma constante como parte de su trabajo diario. Este módulo ofrece la misma información del SIAF que se muestra al ciudadano, pero con un nivel de detalle y herramientas orientadas a la gestión: desglose por meta presupuestal, por específica de gasto, por fuente de financiamiento, con capacidad de drill-down hasta el nivel de registro individual. Incluye indicadores de semáforo basados en umbrales configurables (por ejemplo: menos del 50% de devengado al tercer trimestre se marca en rojo), comparativos contra el PIA y PIM, y proyección de ejecución al cierre del ejercicio fiscal. A diferencia del portal público, este módulo permite cruzar directamente cada registro de ejecución con su origen en el SIGA y exportar los datos para análisis interno.

#### 6.2.2 Seguimiento de Pedidos y Órdenes (Pipeline)

Tablero de seguimiento tipo pipeline o kanban que muestra el estado de cada pedido de compra o servicio a lo largo de su ciclo de vida: solicitado → en proceso de cotización → con orden emitida → en conformidad → devengado. Permite filtrar por área usuaria, tipo de pedido, proveedor y rango de fechas.

#### 6.2.3 Consulta de Saldos Presupuestales

Consulta en tiempo real del saldo disponible por clasificador de gasto y meta presupuestal, calculado como la diferencia entre el PIM y el monto certificado o comprometido. Funcionalidad de uso frecuente para las oficinas de presupuesto y logística.

#### 6.2.4 Cruce SIAF–SIGA

Módulo que permite consultar, a partir de un registro de ejecución presupuestal (devengado, compromiso), el detalle operativo asociado: pedido de origen, orden de compra o servicio, proveedor, conformidad. Y viceversa: desde un pedido SIGA, ver su estado financiero en SIAF.

#### 6.2.5 Alertas de Gestión

Sistema de notificaciones configurables: pedidos que superan un tiempo máximo en una etapa, órdenes próximas a vencimiento de plazo, metas con baja ejecución, certificaciones pendientes. Las alertas se muestran en el dashboard y opcionalmente se envían por correo electrónico.

#### 6.2.6 Reportes y Exportación

Generación de reportes por periodo, área, proveedor, meta o genérica de gasto, con exportación a Excel y PDF. Incluye la generación automatizada de los reportes requeridos por el portal de transparencia estándar del Estado peruano.

#### 6.2.7 Directorio de Proveedores con Historial

Versión ampliada del directorio público, con información detallada de historial de contrataciones, montos por periodo, cumplimiento de plazos y rubros frecuentes.

### 6.3 Módulos Transversales

#### 6.3.1 Mapa de Obras

Mapa interactivo del distrito de San Jerónimo con las obras geolocalizadas, permitiendo al usuario explorar visualmente qué se está construyendo y dónde. Aplicable tanto al portal público como al panel interno.

#### 6.3.2 Integración con el Sistema de Seguimiento de Inversiones (SSI)

Consulta de datos públicos del SSI del MEF para complementar la información financiera con el estado de gestión de los proyectos de inversión: fase actual (expediente técnico, ejecución, cierre), avance físico reportado y observaciones.

#### 6.3.3 Notificaciones y Boletín

Resumen periódico (semanal o quincenal) generado automáticamente con las novedades relevantes: nuevas órdenes emitidas, avance de ejecución de obras principales, alertas activas. Distribución por correo electrónico y, en fases posteriores, por WhatsApp.

---

## 7. Arquitectura Técnica Propuesta

- **Backend:** API REST desarrollada en Python (FastAPI) o Node.js. Responsable de conectarse a SQL Server (SIGA), consumir la API del MEF (SIAF), y servir los datos consolidados al frontend.
- **Base de datos intermedia:** PostgreSQL, para almacenar datos sincronizados del MEF (actualización diaria mediante tarea programada), gestión de usuarios y roles, configuración de alertas, observaciones ciudadanas y logs de auditoría.
- **Frontend:** Aplicación web en React o Vue.js, con librería de gráficos (Recharts, Chart.js o equivalente) y librería de mapas (Leaflet o Mapbox) para la geolocalización de obras.
- **Infraestructura:** Servidor desplegado en la red local de la municipalidad para garantizar el acceso directo a SQL Server del SIGA. El portal público puede exponerse a internet mediante configuración de red o, alternativamente, replicar los datos necesarios a un servidor en la nube.
- **Autenticación:** Sistema de usuarios con roles (ciudadano anónimo, funcionario operativo, funcionario decisor, administrador) implementado con JWT o sesiones seguras.

---

## 8. Consideraciones Legales y de Seguridad

- Los datos del MEF son de acceso público bajo la política de datos abiertos del Estado peruano.
- El acceso a la base de datos del SIGA requiere autorización formal de la Municipalidad Distrital de San Jerónimo, mediante acto administrativo que respalde el proyecto.
- La información expuesta en el portal público se limitará a datos de carácter público: montos, proveedores adjudicados, descripción de bienes y servicios, y datos de obras. No se expondrán datos personales de funcionarios ni información clasificada como reservada.
- El módulo interno operará bajo autenticación y control de acceso basado en roles.
- Se implementarán logs de auditoría para registrar las consultas y acciones realizadas en el sistema.

---

## 9. Plan para la Fase de Diseño

La fase de diseño tiene como objetivo producir todos los entregables necesarios para iniciar el desarrollo con claridad técnica y funcional. Se estructura en las siguientes actividades:

### Actividad 1 — Exploración y mapeo de datos

**Objetivo:** Conocer a profundidad la estructura de ambas fuentes de datos y validar las llaves de cruce.

Tareas:

- Realizar consultas de prueba a la API del MEF filtrando por la unidad ejecutora correspondiente a la Municipalidad Distrital de San Jerónimo. Documentar los campos disponibles, formatos y limitaciones de la API.
- Relevar la estructura de la base de datos del SIGA en SQL Server: tablas principales, campos relevantes, relaciones entre tablas y volumen de datos.
- Identificar y validar las llaves de cruce entre SIAF y SIGA (año fiscal, meta, clasificador, número de expediente SIAF).
- Documentar un diccionario de datos unificado que mapee los campos de ambas fuentes.

**Entregable:** Diccionario de datos y documento de mapeo SIAF–SIGA con llaves de cruce validadas.

### Actividad 2 — Definición de requerimientos funcionales

**Objetivo:** Especificar con precisión qué debe hacer cada módulo del sistema.

Tareas:

- Elaborar historias de usuario para cada perfil (ciudadano, funcionario operativo, funcionario decisor) y cada módulo definido.
- Definir reglas de negocio: umbrales para semáforos, criterios de alertas, lógica de cálculo de saldos, periodicidad de sincronización de datos.
- Priorizar funcionalidades en tres niveles: MVP (versión mínima viable), versión 2 y backlog futuro.
- Validar los requerimientos con al menos un representante de cada perfil de usuario dentro de la municipalidad.

**Entregable:** Documento de requerimientos funcionales con historias de usuario priorizadas.

### Actividad 3 — Diseño de arquitectura técnica

**Objetivo:** Definir la arquitectura del sistema a nivel de componentes, integraciones y despliegue.

Tareas:

- Diseñar el modelo de datos de la base intermedia (PostgreSQL): tablas de usuarios, datos cacheados del MEF, observaciones ciudadanas, configuración de alertas, logs.
- Definir la arquitectura de la API: endpoints, métodos, estructura de respuestas, paginación, autenticación.
- Diseñar el flujo de sincronización de datos del MEF (job diario) y la estrategia de consulta al SIGA (tiempo real vs. caché).
- Definir la estrategia de despliegue: servidor local, exposición a internet, consideraciones de backup y disponibilidad.
- Seleccionar el stack tecnológico definitivo (framework backend, framework frontend, librerías de gráficos y mapas).

**Entregable:** Documento de arquitectura técnica con diagramas de componentes, modelo de datos y definición de API.

### Actividad 4 — Diseño de interfaz de usuario

**Objetivo:** Crear los diseños visuales de todas las pantallas del sistema.

Tareas:

- Elaborar wireframes de baja fidelidad para las pantallas principales: portal de obras, dashboard de ejecución, pipeline de pedidos, consulta de saldos, ficha de obra, mapa de obras, login, reportes.
- Definir el sistema de diseño: paleta de colores, tipografía, componentes reutilizables, principios de accesibilidad.
- Desarrollar mockups de alta fidelidad para las pantallas del MVP.
- Diseñar la experiencia responsive para dispositivos móviles, considerando que muchos ciudadanos accederán desde celular.
- Validar los diseños con usuarios representativos y ajustar según retroalimentación.

**Entregable:** Kit de diseño con wireframes, mockups de alta fidelidad y sistema de diseño documentado.

### Actividad 5 — Planificación del desarrollo

**Objetivo:** Establecer el plan de trabajo para la fase de construcción.

Tareas:

- Descomponer el MVP en tareas de desarrollo estimadas (backend, frontend, integraciones, pruebas).
- Definir sprints o iteraciones con entregables parciales funcionales.
- Establecer el entorno de desarrollo: repositorio, ramas, convenciones de código, herramientas de gestión de tareas.
- Definir la estrategia de pruebas: pruebas unitarias, pruebas de integración con las fuentes de datos, pruebas de usabilidad.

**Entregable:** Cronograma de desarrollo con sprints, estimaciones y asignación de responsabilidades.

---

## 10. Priorización del MVP

El producto mínimo viable se compone de las funcionalidades que generan mayor impacto con menor complejidad:

**MVP — Primera versión:**

1. Portal de obras con fichas individuales y datos de ejecución presupuestal del SIAF.
2. Dashboard general de ejecución presupuestal con filtros (portal público).
3. Pipeline de seguimiento de pedidos y órdenes desde el SIGA (panel interno).
4. Cruce básico SIAF–SIGA por meta y clasificador.
5. Consulta de saldos presupuestales (panel interno).
6. Autenticación y roles básicos.

**Versión 2:**

7. Mapa interactivo de obras.
8. Semáforos y alertas de gestión.
9. Directorio de proveedores con historial.
10. Comparativo histórico entre ejercicios fiscales.
11. Reportes exportables a Excel y PDF.

**Backlog futuro:**

12. Buzón de observaciones ciudadanas.
13. Integración con SSI del MEF.
14. Notificaciones por correo y WhatsApp.
15. Generación automática de reportes de transparencia estándar.

---

## 11. Próximos Pasos Inmediatos

1. Obtener la autorización formal de la municipalidad para el acceso y uso de datos del SIGA en el marco de este proyecto.
2. Realizar la primera consulta a la API del MEF para la entidad y documentar la estructura de respuesta.
3. Relevar las tablas y campos principales de la base de datos SIGA.
4. Iniciar la Actividad 1 de la fase de diseño (exploración y mapeo de datos).

---

*Documento elaborado como base para la planificación y desarrollo del proyecto. Sujeto a revisión y actualización conforme avancen las fases.*