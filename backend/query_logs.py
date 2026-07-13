from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    res = conn.execute(text("SELECT id, job, estado, substring(error_mensaje from 1 for 150) as err, inicio, fin FROM logs.sincronizacion ORDER BY id;")).fetchall()
    for row in res:
        print(f"ID={row[0]} JOB={row[1]} ESTADO={row[2]} ERR={row[3]} INICIO={row[4]} FIN={row[5]}")
