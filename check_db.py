from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    ejecucion = conn.execute(text('SELECT count(*) FROM siaf.ejecucion_presupuestal')).scalar()
    inversiones = conn.execute(text('SELECT count(*) FROM siaf.inversiones')).scalar()
    print(f"ejecucion: {ejecucion}")
    print(f"inversiones: {inversiones}")
