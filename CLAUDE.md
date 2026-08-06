# Instrucciones del Proyecto: Aplicación de Carnets (Claude Code)

Este es un proyecto centrado en la seguridad y la privacidad de los datos. Eres un asistente de programación estricto operando en un entorno Windows. Tu máxima prioridad es evitar brechas de seguridad, proteger la información personal y mantener la estabilidad del código.

## Pila Tecnológica
- Entorno: Windows (PowerShell/CMD)
- Lenguaje: Python 3
- Pruebas: `pytest`
- Linter de calidad: `ruff`
- Auditoría de Seguridad: `bandit`

## Comandos Críticos de Terminal (Windows)
Ejecuta estos comandos sistemáticamente. NUNCA asumas que el código es seguro o funcional sin comprobar los resultados en la terminal.

- Activar entorno: `.\venv\Scripts\activate` (o `venv\Scripts\activate.bat` en CMD)
- Instalar dependencias: `pip install -r requirements.txt`
- Ejecutar pruebas: `pytest tests/ -v`
- Comprobar sintaxis y calidad: `ruff check .`
- Auditoría de Seguridad: `bandit -r . -c pyproject.toml`

## Reglas Estrictas de Seguridad (Prioridad Máxima)

1. Protección de Datos y Credenciales:
   - NUNCA escribas contraseñas, claves API o tokens directamente en el código. Utiliza siempre variables de entorno y un archivo `.env` (que debe estar en el `.gitignore`).
   - Los datos sensibles de los carnets (nombres, identificaciones, fotos) deben ser tratados con métodos de encriptación estándar si se almacenan en disco o base de datos.

2. Prevención de Inyecciones:
   - Si utilizas bases de datos (ej. SQLite, PostgreSQL), utiliza SIEMPRE consultas parametrizadas o un ORM (como SQLAlchemy). Prohibido concatenar strings para formar consultas SQL.
   - Todo dato introducido por el usuario debe ser validado y saneado antes de ser procesado.

3. Validación del Código:
   - Antes de finalizar cualquier modificación, debes ejecutar `bandit -r .` para buscar vulnerabilidades. Si `bandit` reporta fallos, arréglalos inmediatamente sin preguntar.

## Reglas de Desarrollo

1. Desarrollo Guiado por Pruebas (TDD): 
   - Escribe las pruebas en `tests/` ANTES de implementar la lógica funcional. Confirma que la prueba falla y luego escribe el código para que pase.

2. Tolerancia Cero a Errores:
   - Los comandos de `pytest`, `ruff` y `bandit` deben devolver código de salida 0 (éxito). Si hay un error, lee la consola y soluciónalo.
