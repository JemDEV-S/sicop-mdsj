import pyodbc
conn = pyodbc.connect('DRIVER={FreeTDS};SERVER=127.0.0.1;PORT=1433;DATABASE=SIGA_300687;UID=sa;PWD=Sicop_Dev_2026!;TDS_Version=7.4')
cursor = conn.cursor()
cursor.execute("SELECT 1")
print(cursor.fetchone())
