"""Adaptador de acceso a SIGA (SQL Server).

Todas las queries a SIGA son SOLO LECTURA y deben:
  - Fijar SEC_EJEC = settings.SEC_EJEC en la cláusula WHERE
  - Ejecutarse mediante los helpers de este módulo (no crear engines paralelos)
  - Usar parámetros bind (:ano, :sec_ejec) — nunca interpolación de string
"""
