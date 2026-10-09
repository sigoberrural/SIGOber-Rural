# Documentación técnica SIGOber-Rural

- `arquitectura_sistema.md`: arquitectura y diccionario espacial existente.
- `instrumentos_cartografia_social.md`: estructura de captura participativa.
- `indicadores_pendientes.md`: contrato metodológico y estados de los indicadores.
- `../app/pages/03_Cartografia_Social.py`: interfaz Streamlit para importar, revisar y exportar registros de cartografía social.
- `../app/cartografia_social.py`: validaciones técnicas puras, reutilizables y testeables.
- `../tests/test_cartografia_social.py`: pruebas unitarias de validación.

## Pruebas

Desde la raíz del repositorio, con las dependencias instaladas:

`python -m unittest discover -s tests -v`

Las pruebas de calidad técnica no certifican la veracidad del dato ni la aprobación metodológica.
