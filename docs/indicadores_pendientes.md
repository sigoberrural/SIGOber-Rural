# Indicadores SIGOber-Rural — estado metodológico

## Regla de implementación
El proyecto aprobado compromete matrices de indicadores y análisis de aislamiento geográfico y superposición de conflictos, pero el material recuperado hasta ahora no contiene una ficha metodológica aprobada que defina de forma reproducible los diez indicadores ni sus fórmulas.

El software debe distinguir entre dato disponible, variable disponible, indicador definido, fórmula validada y resultado publicado.

## Arquitectura preparada
Cada indicador futuro deberá declarar: indicador_id, nombre, objetivo, unidad, escala, variables_entrada, fuentes, formula, normalizacion, ponderacion, validacion, version_metodologica y fecha_aprobacion.

## Estados
- NO_DEFINIDO: el proyecto lo menciona pero no existe ficha recuperada.
- EN_CONSTRUCCION: existe propuesta de trabajo, no aprobada.
- VALIDADO: definición y fórmula aprobadas.
- IMPLEMENTADO: fórmula validada e implementada.
- PUBLICABLE: implementado y con trazabilidad y fuente.

## Aislamiento geográfico
Preparar capas y relaciones espaciales, pero no publicar un índice hasta disponer de unidad territorial, variables, fuentes, tratamiento de faltantes, fórmula, normalización, pesos y método de validación.

## Superposición de conflictos
Conservar relaciones espaciales y temporales, pero no convertir coincidencias en un índice. Distinguir coincidencia espacial, coincidencia temporal, coexistencia de categorías, densidad documental y superposición metodológicamente definida.

## Antecedente histórico no normativo
En archivos históricos aparece una implementación anterior de seis DCI para SADCI con fórmulas explícitas. Es un antecedente de desarrollo, no la metodología aprobada de los diez indicadores. No debe reutilizarse como definición oficial sin validación documental.

## Próximo insumo requerido
Recuperar o producir, mediante validación del equipo investigador, la matriz de indicadores y los kits de cartografía participativa. Después se convertirán las definiciones validadas en funciones de cálculo y pruebas reproducibles.
