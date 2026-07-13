from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("\n=== COUNT siaf.ejecucion_presupuestal ===")
    res1 = conn.execute(text("SELECT COUNT(*) FROM siaf.ejecucion_presupuestal WHERE sec_ejec = '300687';")).scalar()
    print(res1)
    
    print("\n=== COUNT siaf.inversiones ===")
    res2 = conn.execute(text("SELECT COUNT(*) FROM siaf.inversiones WHERE sec_ejec = '300687';")).scalar()
    print(res2)
    
    print("\n=== logs.sincronizacion ===")
    res3 = conn.execute(text("SELECT * FROM logs.sincronizacion ORDER BY fin DESC LIMIT 5;")).fetchall()
    for row in res3:
        print(row)
