# Guía de uso — Indicadores SADCI (v1.0)

## Acceso local

Desde la raíz del repositorio, activar el entorno virtual e instalar dependencias:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/main.py
```

La página SADCI aparece en la navegación multipágina de Streamlit como **Indicadores SADCI**. También puede abrirse como página independiente:

```bash
streamlit run app/pages/04_Indicadores_SADCI.py
```

## Funciones disponibles

- Resumen de los diez indicadores incluidos en el catálogo.
- Filtro por dimensión, búsqueda por código o nombre y evaluación de meta.
- Resultado calculado a partir del numerador y denominador.
- Comparación con la meta explícita sin inferir bandas de semáforo no aprobadas.
- Fichas técnicas con fórmula, variables, valores de origen, responsable, periodicidad y fuentes declaradas.
- Descarga CSV y JSON de la selección filtrada.
- Vista de disponibilidad veredal con las condiciones para habilitar una desagregación válida.
- Controles metodológicos y señalamiento de contradicciones directas entre semáforo verde y meta incumplida.

## Interpretación responsable

El estado PENDIENTE_VERIFICACION significa que el valor de la matriz no se ha contrastado todavía con el documento institucional fuente. No presentar los valores como mediciones oficiales verificadas hasta que una persona responsable valide la fuente, el periodo, la unidad de conteo y el cálculo.

Los indicadores de capacidad institucional son municipales por defecto. No deben copiarse ni repartirse entre veredas. Para habilitar el análisis veredal se necesitan observaciones por vereda con numerador, denominador, periodo, fuente, fecha de corte, responsable y estado de validación; además, el indicador debe admitir esa escala conceptualmente.

## Estructura del catálogo

El catálogo de trabajo se encuentra en data/indicadores_sadci.json. La lógica de cálculo está aislada en app/sadci.py, la interfaz en app/pages/04_Indicadores_SADCI.py y las pruebas en tests/test_sadci.py.

## Lista de cierre de versión

- [ ] Verificar los valores con documentos fuente.
- [ ] Aprobar las bandas de semáforo por indicador.
- [ ] Confirmar las reglas de conteo y la periodicidad del indicador NSF.
- [ ] Confirmar fuentes y responsables institucionales.
- [ ] Validar ejecución de pruebas y despliegue.
- [ ] Incorporar datos históricos comparables si están disponibles.
- [ ] Activar solo las desagregaciones veredales respaldadas por datos.
