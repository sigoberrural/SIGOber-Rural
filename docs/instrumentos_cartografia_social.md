# Instrumentos de cartografía social — SIGOber-Rural

## Propósito
Estructura técnica de captura para la fase de cartografía social prevista en el proyecto. No define ni presume fórmulas de aislamiento o superposición.

El proyecto aprobado establece cuatro dimensiones: conflictos de tenencia y uso de la tierra; redes institucionales percibidas (presencia/ausencia del Estado); infraestructura crítica; y dinámicas del conflicto armado.

## Regla metodológica
- Registrar fuente para cada observación.
- Separar percepción comunitaria de dato oficial.
- Una ausencia de registro no equivale a ausencia territorial.
- No calcular aislamiento ni superposición hasta contar con definición metodológica validada.
- No asignar pesos, escalas o valores no definidos en un instrumento aprobado.
- Mantener confidencialidad y seudonimización para datos sensibles.

## Unidad de observación
Cada registro representa una observación territorial producida durante un taller, entrevista o ejercicio de cartografía participativa.

Campos comunes: id_registro, taller_id, fecha, vereda, codigo_ver, categoria, subcategoria, descripcion, geometria_tipo, coordenadas, fuente, participante_tipo, confianza, estado_validacion y observaciones.

## Instrumento A — Tenencia y uso de la tierra
Registrar localización y descripción de conflictos de tenencia, conflictos o tensiones de uso y áreas señaladas por la comunidad. La captura no convierte una percepción comunitaria en una afirmación jurídica sobre propiedad, posesión, ocupación o formalización.

## Instrumento B — Presencia/ausencia institucional
Registrar lugares, servicios, recorridos o referencias mediante los cuales la comunidad identifica presencia o ausencia institucional. Distinguir presencia percibida, presencia documentada, ausencia reportada y ausencia no evaluada. La plataforma no interpretará automáticamente una ausencia de registro como inexistencia institucional.

## Instrumento C — Infraestructura crítica
Registrar infraestructura que la comunidad considere relevante para su vida rural y gestión territorial: vías y pasos, puentes, equipamientos, servicios esenciales, infraestructura productiva y puntos cuya interrupción tenga consecuencias territoriales. La clasificación definitiva deberá validarse.

## Instrumento D — Conflicto armado
Registrar dinámicas señaladas durante la cartografía social, separando observación o memoria comunitaria, fuente documental, fuente oficial, evento georreferenciado y referencia territorial de escala mayor. Minimizar información identificable de personas.

## Digitalización
Los mapas físicos deben conservar identificador del taller, categoría/símbolo, geometría, descripción original, fuente, fecha y estado de validación. La digitalización no debe agregar precisión inexistente en el mapa original.

## Integración
Las capas podrán relacionarse con veredas, situaciones territoriales documentadas, PBOT, vías, datos oficiales y registros de conflicto. Una relación espacial es un insumo analítico, no una fórmula de indicador.

## Estado
Implementado: estructura de datos y trazabilidad.
Pendiente: vocabulario definitivo, simbología y protocolo de digitalización.
Bloqueado hasta definición metodológica: cálculo numérico de aislamiento, superposición e índices compuestos.
