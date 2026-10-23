# SIGOber-Rural

Sistema de Información Geográfica y Gobernanza Rural para el municipio de Puerto Rico, Caquetá. Proyecto de Investigación Aplicada ESAP-2026.

## Propósito

SIGOber-Rural integra exploración cartográfica, situaciones territoriales, referencias de ordenamiento y herramientas de lectura institucional para apoyar el análisis de la gobernanza rural. Los datos deben interpretarse según su procedencia, fecha, cobertura y nivel territorial; la visualización no implica por sí sola validación oficial ni causalidad.

## Módulos principales

- **Territorio:** exploración del municipio y sus veredas.
- **Situaciones territoriales:** consulta de registros disponibles y sus atributos.
- **Ordenamiento PBOT 2015:** visualización separada de capas asociadas al instrumento de 2015, sin presentarlo como una actualización del PBOT.
- **Cartografía social:** gestión de registros participativos y estado de validación.
- **Indicadores SADCI:** tablero de diez indicadores, evaluación de metas, fichas metodológicas, exportación CSV/JSON y control de disponibilidad para análisis veredal.

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

El catálogo SADCI se mantiene en `data/indicadores_sadci.json`; su lógica de cálculo, en `app/sadci.py`; su interfaz, en `app/pages/04_Indicadores_SADCI.py`. La guía de uso y los criterios pendientes están en `docs/guia_uso_indicadores_sadci_v1.md` y `docs/validacion_indicadores_sadci.md`.

## Validación y límites

- Los valores SADCI de partida permanecen pendientes de verificación documental hasta contrastarlos con las fuentes institucionales.
- El semáforo de origen se conserva por separado de la evaluación automática de metas; no se inventan bandas no aprobadas.
- No se desagregan valores municipales por vereda sin observaciones territoriales y reglas de asignación válidas.
- Las capas PBOT identificadas como 2015 deben conservar esa fecha y procedencia.
- La interpretación de patrones espaciales no demuestra causalidad.

## Pruebas

Las pruebas SADCI están en `tests/test_sadci.py`. El workflow `.github/workflows/validacion-sadci.yml` comprueba la sintaxis Python y ejecuta las pruebas del módulo cuando se envían cambios a `Develope` o una solicitud de integración dirigida a esa rama.

## Rama de trabajo

Los avances de esta fase se realizan en `Develope`. No modificar `main` durante el desarrollo de esta versión.
