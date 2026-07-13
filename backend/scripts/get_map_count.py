import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from sqlalchemy import text

def main():
    db = SessionLocal()
    try:
        total = db.execute(text("SELECT count(*) FROM siaf.inversiones")).scalar()
        con_coords = db.execute(text("SELECT count(*) FROM siaf.inversiones WHERE latitud IS NOT NULL")).scalar()
        print("Total en BD:", total)
        print("Con Coords:", con_coords)
    finally:
        db.close()

if __name__ == "__main__":
    main()
