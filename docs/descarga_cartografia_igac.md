# Descarga manual de cartografía IGAC para SIGOber-Rural

La aplicación admite capas locales IGAC en GeoJSON para no depender exclusivamente del servicio remoto al abrir el mapa.

## Requisitos

- Python 3.10 o superior.
- Conexión a internet durante la descarga.
- Estar en la rama `Develope` del repositorio.

El script usa solo la biblioteca estándar de Python.

## Procedimiento recomendado

Desde la raíz del repositorio, ejecutar primero una sola capa para comprobar acceso al servicio:

```bash
python scripts/descargar_cartografia_igac.py --grupo vias
```

Si finaliza correctamente, repetir para los grupos que se necesiten:

```bash
python scripts/descargar_cartografia_igac.py --grupo drenajes
python scripts/descargar_cartografia_igac.py --grupo construcciones
python scripts/descargar_cartografia_igac.py --grupo curvas_piscinas
python scripts/descargar_cartografia_igac.py --grupo bosque
```

También se pueden solicitar todos los grupos con `--grupo todos`. La descarga puede tardar y dependerá de la disponibilidad del servicio oficial.

Los GeoJSON y el manifiesto se guardan en `data/cartografia_oficial/igac/`. El manifiesto registra la fuente, la envolvente consultada, el recuento de entidades y SHA-256 de cada archivo.

## Cómo incorporarlos al despliegue

1. Revisar el resumen de cada descarga y confirmar que los recuentos no sean cero ni estén truncados.
2. Abrir los GeoJSON y comprobar que las geometrías estén dentro de la zona de estudio.
3. Revisar el tamaño de los archivos. Si son demasiado grandes para GitHub o para el despliegue, no forzar su incorporación: reducir la envolvente o dividir las capas.
4. Incorporar los GeoJSON al repositorio en la rama `Develope`, o configurar un almacenamiento persistente accesible desde el despliegue.
5. En la aplicación, abrir **Explorar territorio** y seleccionar las capas bajo **Cartografía IGAC descargada (local)**.

## Límites y precauciones

- La descarga usa una envolvente geográfica aproximada alrededor de Puerto Rico, Caquetá; no es el límite administrativo oficial. Validar cobertura antes de análisis.
- Las capas de cartografía básica pueden ser pesadas. Comenzar por `vias` y ampliar de forma gradual.
- El sistema conserva el identificador y nombre de la capa IGAC en las propiedades de cada entidad.
- La descarga local no sustituye la validación de metadatos, fecha, licencia ni escala.
- Si el servicio falla, conservar el mensaje de error completo: permite distinguir una caída del proveedor de un problema de consulta.
- Las capas locales son para visualización y exploración; no deben usarse para inferir riesgo, aptitud predial o indicadores nuevos sin una metodología documentada.
