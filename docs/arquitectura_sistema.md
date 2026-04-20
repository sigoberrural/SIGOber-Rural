# Arquitectura de Datos - SIGOber-Rural

## 1. Sistema de Referencia Espacial
* **Sistema:** WGS 84
* **EPSG:** 4326
* **Formato de Coordenadas:** Grados Decimales (Latitud, Longitud)
* **Nota técnica:** En archivos GeoJSON, el orden DEBE ser `[longitud, latitud]`.

## 2. Diccionario de Datos (Capas Espaciales)

### A. Capa de Conflictos (Puntos)
| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id_caso` | String | Identificador único (ej: PR-2026-001) |
| `categoria` | String | Clasificación: 'Linderos', 'Uso del Suelo', 'Titulación', 'Ambiental' |
| `intensidad` | Integer | Nivel de urgencia: 1 (Baja), 2 (Media), 3 (Alta) |
| `actor_clave` | String | Principal involucrado (Campesino, Estado, Privado) |
| `est_formal` | String | Estado ante la ANT (Sin solicitud, En trámite, Formalizado) |

### B. Capa de Veredas/Predios (Polígonos)
| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `nombre` | String | Nombre de la vereda o sector |
| `area_ha` | Float | Área calculada en hectáreas |
| `fuente` | String | Origen del dato (Cartografía Social Taller X) |

## 3. Diccionario de Datos (Capacidad Institucional - CSV)
* **Archivo:** `data/plantilla_indicadores.csv`
* **Campos clave:**
    * `cap_operativa`: Suma de personal planta + contratistas.
    * `nivel_digital`: Escala 1-5 de infraestructura tecnológica.
    * `existencia_cmdr`: Booleano (Sí/No).
