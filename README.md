# SIGOber-Rural

Sistema de Información Geográfica y Gobernanza Rural para el municipio de Puerto Rico, Caquetá. Proyecto de Investigación Aplicada ESAP-2026.

## Propósito

SIGOber-Rural integra exploración cartográfica, situaciones territoriales, referencias de ordenamiento y herramientas de lectura institucional para apoyar el análisis de la gobernanza rural. Los datos deben interpretarse según su procedencia, fecha, cobertura y nivel territorial; la visualización no implica por sí sola validación oficial ni causalidad.

## Espacios principales de trabajo

La interfaz se organiza en solo dos alternativas en el menú izquierdo:

- **Ingesta y gestión de datos:** plantillas Excel descargables para problemáticas por vereda y actualizaciones SADCI; importación CSV/Excel con validación por fila, informe descargable, confirmación y vista temporal de los datos en la sesión. También permite inspeccionar CSV, Excel, JSON y GeoJSON.
- **Exploración de resultados:** mapa territorial guiado y accesos a las consultas especializadas de PBOT 2015 e indicadores SADCI.

Las importaciones de problemáticas y SADCI se mantienen en la sesión de la aplicación; no se escriben automáticamente en Google Sheets, el repositorio ni una base de datos compartida. Los valores SADCI importados se recalculan desde numerador y denominador y quedan pendientes de verificación documental. Retirar datos desde la interfaz no borra fuentes persistentes. Para operación multiusuario se requiere completar y configurar un backend persistente con permisos y auditoría.

## Requisitos y ejecución local

Se recomienda Python 3.11 o compatible con las dependencias del proyecto.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/main.py
```

La aplicación abre una navegación multipágina de Streamlit. Para probar únicamente SADCI:

```bash
streamlit run app/pages/04_Indicadores_SADCI.py
```

## Configuración y datos

Algunas fuentes externas, como las hojas de cálculo conectadas, requieren secretos y permisos configurados en el entorno de ejecución. Si la conexión no está disponible, no debe interpretarse la ausencia de datos como ausencia del fenómeno.

El catálogo SADCI se mantiene en `data/indicadores_sadci.json`; su lógica de cálculo, en `app/sadci.py`; la interfaz de resultados, en `app/pages/04_Indicadores_SADCI.py`; y las plantillas y validaciones de importación, en `app/ingesta.py`. La guía de uso y los criterios pendientes están en `docs/guia_uso_indicadores_sadci_v1.md` y `docs/validacion_indicadores_sadci.md`. El estado de preparación y la lista de aceptación de la versión 1.0 están en `docs/estado_version_1_0.md`.

## Validación y límites

- Los valores SADCI de partida permanecen pendientes de verificación documental hasta contrastarlos con las fuentes institucionales.
- El semáforo de origen se conserva por separado de la evaluación automática de metas; no se inventan bandas no aprobadas.
- No se desagregan valores municipales por vereda sin observaciones territoriales y reglas de asignación válidas.
- Las capas PBOT identificadas como 2015 deben conservar esa fecha y procedencia.
- La interpretación de patrones espaciales no demuestra causalidad.

## Pruebas

Las pruebas SADCI están en `tests/test_sadci.py` y las de plantillas e importación en `tests/test_ingesta.py`. El workflow `.github/workflows/validacion-sadci.yml` comprueba la sintaxis Python y ejecuta las pruebas del módulo cuando se envían cambios a `Develope` o una solicitud de integración dirigida a esa rama.

## Rama de trabajo

Los avances de esta fase se realizan en `Develope`. No modificar `main` durante el desarrollo de esta versión.
