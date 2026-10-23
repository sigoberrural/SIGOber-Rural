# Estado de preparación de la versión 1.0

**Rama de trabajo:** `Develope`  
**Estado:** versión de trabajo en preparación; no etiquetada como lanzamiento estable.  
**Principio de publicación:** no modificar `main` durante esta fase.

## Cambios de interfaz incorporados

- Portada con identidad visual consistente y enlaces directos a PBOT 2015, cartografía social e indicadores SADCI.
- Consulta cartográfica guiada por tarea (territorio, situaciones documentadas o PBOT), sin selector de modo de exploración.
- Métricas contextuales que cambian según la vista elegida, para evitar mezclar conteos de situaciones con la consulta de límites o de ordenamiento.
- Guías de inicio rápido para el tablero SADCI y el flujo de revisión de cartografía social.
- Página PBOT 2015 con inventario de capas, conteo de geometrías y manejo aislado de archivos ausentes o corruptos.
- Página de cartografía social con revisión por filas, filtro de errores, resumen por categoría y descargas separadas de revisión completa y pendientes.
- Flujo de CI ampliado para ejecutar todas las pruebas unitarias del repositorio.
- Contexto territorial visible: Puerto Rico, Caquetá; enfoque de gobernabilidad rural.
- Métricas con ayudas contextuales para distinguir conteos observados de ausencia de datos.
- Diagnóstico de disponibilidad de las hojas institucionales con detalle por fuente y opción de actualización.
- Guía de lectura del mapa, explicación de las capas temáticas y advertencia explícita de que cero registros asociados no equivale a ausencia del fenómeno.
- Tablero SADCI con filtros, fichas metodológicas, visualización, exportación CSV/JSON y separación entre meta y semáforo original.
- Mensajes de procedencia y limitaciones de la cartografía PBOT 2015 y de los servicios remotos IGAC/UPRA.

## Alcance funcional actual

| Componente | Estado de preparación | Condición para cerrar v1.0 |
|---|---|---|
| Mapa territorial principal | Interfaz y filtros disponibles | Verificar visualmente geometrías, selección de vereda y comportamiento con datos reales |
| Situaciones territoriales | Datos locales integrados al mapa | Auditar correspondencia de códigos, cobertura temporal y coordenadas |
| Capas PBOT 2015 | Página separada y capas locales opcionales | Comprobar integridad de cada GeoJSON y documentar campos/cobertura |
| Servicios IGAC/UPRA | Selectores y diagnóstico de servicio | Confirmar que cada capa remota devuelve imagen visible en el entorno de despliegue |
| Cartografía social | Importación CSV, validación técnica y exportación | Confirmar persistencia, protocolo de revisión y protección de datos sensibles |
| Indicadores SADCI | Catálogo, cálculos, fichas y exportación | Validación institucional de valores, metas, fuentes y semáforos |
| Escala veredal SADCI | Control de disponibilidad y plantilla | Activar solo cuando existan observaciones válidas territorializadas |
| Captura offline | Formulario descargable | Verificar sincronización; no anunciar sincronización operativa hasta probarla |
| Pruebas automáticas | Sintaxis y pruebas unitarias del repositorio ejecutadas correctamente en CI para el commit de interfaz actual | Mantener pruebas y añadir cobertura de flujos críticos |

## Reglas de calidad y publicación

1. La falta de datos de una fuente conectada se presenta como **no disponible**, no como cero.
2. Los conteos describen registros de las bases consultadas, no necesariamente el universo real de situaciones ocurridas.
3. Cada capa conserva nombre, escala, año, procedencia y limitaciones conocidas.
4. No se asignan resultados municipales SADCI a las veredas sin datos y justificación metodológica.
5. Las hipótesis espaciales no se presentan como relaciones causales demostradas.
6. No se considera que el mapa esté validado solo porque la página carga: se debe comprobar la geometría y la visibilidad de cada capa.
7. No se publica como versión estable hasta que las pruebas automatizadas terminen satisfactoriamente y se realice una prueba manual del recorrido completo.

## Prueba manual de aceptación

- [ ] La aplicación principal abre sin errores.
- [ ] La cartografía base carga y las veredas muestran nombre y código.
- [ ] La selección de vereda se distingue visualmente.
- [ ] Los filtros de año, tipo y confianza afectan los registros usados en la vista.
- [ ] La capa de situaciones se puede activar y su leyenda coincide con la lógica de conteo.
- [ ] Las capas PBOT locales disponibles se muestran sin bloquear el mapa.
- [ ] Cada servicio remoto IGAC/UPRA se comprueba por separado; los fallos se explican al usuario.
- [ ] Las fuentes Google Sheets distinguen hojas disponibles y no disponibles.
- [ ] Las páginas PBOT, cartografía social y SADCI abren desde la navegación.
- [ ] La importación CSV de cartografía social valida casos correctos e incorrectos.
- [ ] El tablero SADCI permite filtrar y descargar resultados.
- [ ] La aplicación mantiene avisos sobre procedencia, calidad y limitaciones de los datos.
- [x] GitHub Actions finaliza en verde para los cambios actuales de interfaz y las pruebas unitarias.
- [ ] Se confirma que todos los cambios siguen en `Develope` y `main` no fue modificado.

## Siguiente prioridad técnica

Después de la mejora visual, la prioridad es ejecutar y registrar la aceptación funcional: mapa base y capas remotas, filtros territoriales, datos institucionales conectados y recorrido completo de las páginas. Los elementos que dependan de permisos, secretos o disponibilidad de proveedores deberán quedar identificados como requisitos de despliegue, no como fallos silenciosos.
