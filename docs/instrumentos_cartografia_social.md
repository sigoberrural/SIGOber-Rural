# Instrumentos de cartografía social — SIGOber-Rural

## Propósito
Estructura técnica de captura para la fase de cartografía social prevista en el proyecto. No define ni presume fórmulas de aislamiento o superposición.

Dimensiones previstas: (1) tenencia y uso de la tierra; (2) presencia/ausencia institucional; (3) infraestructura crítica; (4) conflicto armado.

## Principios de tratamiento
- Registrar fuente, fecha y sesión para cada observación.
- Separar percepción comunitaria de dato oficial.
- Una ausencia de registro no equivale a ausencia territorial o institucional.
- No asignar pesos, escalas ni categorías específicas que no estén en un instrumento aprobado.
- No calcular aislamiento ni superposición hasta que exista definición metodológica validada.
- Minimizar datos personales y proteger información sensible relacionada con conflicto.

## Esquema de registro
Campos: id_registro, taller_id, fecha, vereda, codigo_ver, categoria, subcategoria, descripcion, geometria_tipo, latitud, longitud, geometria_geojson, fuente, tipo_fuente, participante_tipo, confianza, estado_validacion, observaciones.

No todas las geometrías serán puntos. Para líneas y polígonos se utilizará geometria_geojson; latitud/longitud se reservan para puntos o centroides expresamente documentados. No inferir geometría ni centroides automáticamente.

## Categorías generales
- TENENCIA_USO_TIERRA
- PRESENCIA_AUSENCIA_INSTITUCIONAL
- INFRAESTRUCTURA_CRITICA
- CONFLICTO_ARMADO

Son etiquetas de organización del formulario y no sustituyen las subcategorías del instrumento aprobado, que deben confirmarse con el equipo investigador.

## Instrumento A — Tenencia y uso
Registrar localización y descripción de conflictos de tenencia, tensiones de uso y áreas señaladas por la comunidad. La captura no convierte una percepción en afirmación jurídica sobre propiedad, posesión, ocupación o formalización.

## Instrumento B — Presencia/ausencia institucional
Distinguir presencia percibida, presencia documentada, ausencia reportada y ausencia no evaluada. La plataforma no interpreta automáticamente ausencia de registro como inexistencia institucional.

## Instrumento C — Infraestructura crítica
Admite infraestructura señalada por la comunidad como relevante para su vida rural y gestión territorial. Las subcategorías definitivas deberán validarse; no se impone una lista cerrada.

## Instrumento D — Conflicto armado
Separar memoria/observación comunitaria, fuente documental, fuente oficial, evento georreferenciado y referencia territorial de escala mayor. Minimizar información que identifique a personas.

## Digitalización
Conservar identificador del taller, símbolo original, geometría, descripción, fuente, fecha y estado de validación. La digitalización no debe agregar precisión inexistente en el mapa original.

## Integración
Las capas podrán relacionarse con veredas, situaciones territoriales documentadas, PBOT, vías, fuentes oficiales y registros de conflicto. Una relación espacial es un insumo analítico, no una fórmula de indicador.

## Estado
- Preparado: esquema de datos, plantilla CSV, página de revisión/importación y trazabilidad.
- Pendiente de validación: subcategorías oficiales, simbología, protocolo de digitalización y consentimiento/gestión de datos de cada taller.
- Bloqueado hasta definición metodológica: cálculo numérico de aislamiento, superposición e índices compuestos.
