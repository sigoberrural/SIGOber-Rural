# Indicadores SIGOber-Rural — estado metodológico

## Regla de implementación
El proyecto compromete una matriz de diez indicadores y análisis de aislamiento geográfico y superposición de conflictos. En el material recuperado hasta ahora no hay ficha aprobada que defina de forma reproducible los diez indicadores y sus fórmulas.

El software distingue entre dato disponible, variable disponible, indicador definido, fórmula validada, cálculo implementado y resultado publicable.

## Contrato de cada indicador futuro
- indicador_id estable
- nombre y objetivo aprobados
- unidad y escala territorial
- variables de entrada y reglas de calidad
- fuentes y fecha/corte de datos
- fórmula y tratamiento de faltantes
- normalización y ponderación, si corresponde
- método de validación
- versión metodológica, responsable y fecha de aprobación

## Estados
- NO_DEFINIDO: no se ha recuperado una ficha.
- EN_CONSTRUCCION: propuesta no aprobada.
- VALIDADO: definición y fórmula aprobadas.
- IMPLEMENTADO: fórmula validada codificada y probada.
- PUBLICABLE: implementación trazable, datos suficientes y validación documentada.

## Aislamiento geográfico
Preparar y validar capas, metadatos y relaciones espaciales. No publicar un índice hasta disponer de unidad territorial, variables, fuentes, tratamiento de faltantes, fórmula, normalización, ponderaciones y validación.

## Superposición de conflictos
Conservar relaciones espaciales y temporales, sin convertir coincidencias en un índice. Distinguir coincidencia espacial, coincidencia temporal, coexistencia de categorías, densidad documental y superposición definida metodológicamente.

## Antecedente histórico no normativo
En código histórico aparece una implementación de seis DCI para SADCI con fórmulas explícitas. Es un antecedente de desarrollo y no la metodología aprobada de los diez indicadores.

## Próximo insumo
Recuperar o validar la matriz de indicadores y los kits de cartografía participativa. Una vez aprobados, convertirlos en funciones de cálculo con pruebas reproducibles.
