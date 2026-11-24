# Validación inicial de los indicadores SADCI

**Proyecto:** SIGOber-Rural — Puerto Rico, Caquetá  
**Insumo:** matriz Indicadores SADCI.xlsx facilitada para el proyecto.  
**Estado:** validación estructural y aritmética inicial; aprobación metodológica y verificación documental pendientes.

## 1. Resultados reproducidos

La matriz contiene diez indicadores en siete dimensiones. Los diez utilizan la estructura numerador / denominador × 100. La tabla siguiente reproduce los cálculos con los valores de la hoja; no certifica que esos valores correspondan a evidencia institucional vigente.

| Código | Resultado reproducido | Meta consignada | Evaluación de meta |
|---|---:|---|---|
| TDN | 25,00 % | < 20 % | No cumple |
| IFP | 60,00 % | > 80 % | No cumple |
| GEI | 50,00 % | > 75 % | No cumple |
| NSF | 16,67 % | < 10 % | No cumple |
| IEPI | 84,00 % | > 85 % | No cumple |
| TDCF | 60,00 % | > 85 % | No cumple |
| TRTC | 66,67 % | > 80 % | No cumple |
| IMIA | 33,33 % | > 70 % | No cumple |
| CPCC | 66,67 % | > 85 % | No cumple |
| CCCO | 80,00 % | > 85 % | No cumple |

La evaluación usa los operadores estrictos que aparecen en la matriz. Por ejemplo, 85 % no satisface una meta formulada como > 85 %. Todos los registros mantienen el estado **PENDIENTE_VERIFICACION** hasta que se contrasten las fuentes.

## 2. Hallazgos metodológicos

1. **TDN: contradicción de semáforo.** La hoja indica 25 % y meta < 20 %, pero asigna VERDE. Con los valores de la propia matriz, la meta no se cumple. El módulo señala la inconsistencia y conserva el semáforo original para auditoría.
2. **Bandas de semáforo incompletas.** No hay intervalos ni reglas aprobadas para los colores verde, amarillo y rojo. La aplicación evalúa la meta explícita y muestra el semáforo de origen por separado; no inventa bandas intermedias.
3. **Universo de conteo.** IFP, GEI, NSF, TDCF, IMIA y CPCC necesitan criterios reproducibles para definir qué se cuenta como proceso formalizado, acuerdo en ejecución, duplicidad funcional, activo óptimo, vinculación por mérito o persona capacitada.
4. **Comparabilidad temporal.** Numerador y denominador deben referirse al mismo periodo y universo. Es especialmente importante en IEPI, TRTC y CCCO.
5. **Periodicidad de NSF.** El original dice “Bi-anual”, expresión ambigua (dos veces al año o una vez cada dos años). Se conserva la nota “Bienal, confirmar interpretación” para no convertir una inferencia en decisión metodológica.
6. **Fuentes institucionales.** Las fuentes y responsables se transcriben del archivo. Su mención no significa que se hayan consultado o verificado; se debe confirmar su existencia, aplicabilidad y acceso en Puerto Rico, Caquetá.
7. **Escala territorial.** Los valores actuales son municipales. No se asignan ni prorratean entre veredas. La desagregación requiere registros territorializados con numerador, denominador, periodo, fuente y regla de no duplicación, además de justificar que el indicador admite esa escala.

## 3. Reglas del módulo

- Resultado reproducido = numerador / denominador × 100.
- Denominador ausente, no numérico o menor o igual a cero: resultado no calculable, sin división por cero.
- La meta se evalúa con el operador explícito (>, >=, <, <=).
- Se conserva el semáforo original como procedencia.
- Se marca la contradicción cuando la hoja indica VERDE y la meta explícita no se cumple.
- La aplicación no declara un indicador publicable sin verificación documental.

## 4. Contrato mínimo para observaciones veredales

Cada observación deberá incluir código del indicador, código y nombre de vereda, periodo de referencia, numerador, denominador, unidad, fuente y documento de respaldo, fecha de corte, responsable de captura, estado de validación y regla de no duplicación. Los indicadores institucionales sin interpretación válida por vereda permanecerán en el nivel municipal.

## 5. Próximos pasos de validación

- Confirmar metas y fichas técnicas con la Secretaría Técnica del CMDR y las dependencias responsables.
- Verificar documentos fuente y registrar fecha de corte y responsable que valida.
- Aprobar bandas de semáforo y reglas para datos insuficientes.
- Confirmar la periodicidad del NSF y la aplicabilidad de las fuentes citadas.
- Incorporar series temporales solo si los periodos son comparables.
- Habilitar análisis veredal únicamente con variables territorializadas y trazables.
