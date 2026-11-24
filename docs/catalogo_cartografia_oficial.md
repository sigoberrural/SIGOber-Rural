# Catálogo de cartografía oficial para SIGOber-Rural

Este catálogo registra fuentes oficiales candidatas para Puerto Rico, Caquetá. La inclusión en el catálogo no significa que la capa ya esté descargada, validada o integrada al mapa: el campo `estado_integracion` diferencia catalogación de integración efectiva.

## Fuentes prioritarias

1. **IGAC — Cartografía básica 1:10.000 de Puerto Rico, Caquetá.** Servicio oficial publicado por IGAC, elaborado en 2025 a partir de fotografías aéreas de 2023. Capas identificadas en el servicio: construcciones puntuales y rurales, nombres geográficos, tapas de servicio público, puntos de distribución, puentes, curvas de nivel, vías, drenajes, bosques, depósitos de agua e islas.  
   Servicio: https://mapas2.igac.gov.co/server3/rest/services/carto/carto10000puertorico18592/MapServer  
   Referencia: https://www.igac.gov.co/datos-abiertos/datos-abiertos-geoespaciales

2. **UPRA — Frontera agrícola nacional.** Capa de contexto productivo publicada a escala 1:100.000.  
   Servicio: https://geoservicios.upra.gov.co/arcgis/rest/services/ordenamiento_productivo/frontera_agricola/MapServer

3. **UPRA — Frontera agrícola y frontera agrícola condicionada.** Capa de contexto para reconocer áreas con condiciones y restricciones normativas/técnicas; requiere revisar metadatos y versión.  
   Servicio: https://geoservicios.upra.gov.co/arcgis/rest/services/ordenamiento_productivo/frontera_agricola_frontera_agricola_condicionada/MapServer

4. **Servicio Geológico Colombiano — amenaza por movimientos en masa.** Servicio nacional de referencia a escala 1:100.000; útil para contexto, no como evaluación de riesgo predial.  
   Servicio: https://geoportal.sgc.gov.co/arcgis/rest/services/Mapa_Nacional_Amenaza_Mov_Masa_100K/Mapa_Nacional_Amenaza_Movimientos_Masa_100K/FeatureServer

5. **Servicio Geológico Colombiano — amenaza sísmica nacional.**  
   Servicio: https://geoportal.sgc.gov.co/arcgis/rest/services/Amenaza_Sismica/Amenaza_Sismica_Nacional/MapServer

6. **IGAC — catálogo de datos abiertos geoespaciales.** Para descubrir cartografía base, ortoimágenes, modelos digitales de terreno y datos catastrales disponibles.  
   Portal: https://www.igac.gov.co/datos-abiertos/datos-abiertos-geoespaciales

## Capas locales ya existentes en el repositorio

El directorio `data/PBOT2015/` contiene capas derivadas del PBOT 2015. Deben mantenerse diferenciadas de cartografía básica reciente: el PBOT representa instrumentos de ordenamiento y no sustituye la cartografía base oficial.

## Protocolo obligatorio antes de integrar una fuente

Para cada capa registrar: entidad productora, título, URL de servicio o descarga, fecha de consulta, fecha de publicación/actualización, escala/resolución, sistema de referencia, cobertura espacial, licencia/condiciones de uso, atributos clave, método de descarga, checksum del archivo local, transformaciones realizadas y estado de validación.

Estados recomendados:
- `POR_EXPLORAR`: fuente candidata, aún no revisada.
- `CATALOGADA`: servicio identificado, pendiente de integración técnica.
- `INTEGRADA_REMOTA`: se visualiza desde servicio externo; depende de conectividad.
- `DESCARGADA`: copia local con metadatos y checksum.
- `VALIDADA`: geometría, cobertura, sistema de referencia y atributos comprobados.
- `PUBLICABLE`: validación y licencia revisadas, con procedencia documentada.

## Criterios de integración

- Priorizar la cartografía IGAC 1:10.000 para detalle topográfico local.
- Usar UPRA y SGC como capas temáticas de contexto respetando su escala.
- No sobrescribir los polígonos de veredas con otras geometrías.
- No derivar índices de aislamiento o superposición a partir de estas capas sin definición metodológica aprobada.
- Mantener fuente y fecha en los metadatos y, cuando proceda, en el tooltip.
- Si el servicio remoto falla, el mapa debe seguir funcionando con las capas locales.

## Pendiente de esta iteración

Este cambio cataloga las fuentes y organiza la prioridad de incorporación. No afirma que todas las fuentes ya se estén dibujando en el mapa ni que sus datos se hayan descargado. La integración visual/descarga debe realizarse por capa y comprobarse con pruebas.
