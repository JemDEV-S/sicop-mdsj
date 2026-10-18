import os
import shutil
import uuid
from pathlib import Path
from sqlalchemy import text
from app.database import SessionLocal

SEEDS = [
    {
        "cui": "2471517",
        "archivo": "704134304_1399008792269741_6168962534236584395_n.jpg",
        "nombre_original": "Av_Huanacauri_Pavimentacion_Manantiales.jpg",
    },
    {
        "cui": "2471517",
        "archivo": "486333777_1056925463144744_7235890130926122124_n.jpg",
        "nombre_original": "Av_Huanacauri_Veredas_y_Muros.jpg",
    },
    {
        "cui": "2653987",
        "archivo": "776578649_1122598267096659_1933952980578275784_n.jpg",
        "nombre_original": "Camino_Vecinal_Llutucalle_Sucso.jpg",
    },
    {
        "cui": "2653987",
        "archivo": "490267201_1070942505076373_7707515389707058820_n.jpg",
        "nombre_original": "Llutucalle_Apertura_Trocha.jpg",
    },
    {
        "cui": "2622068",
        "archivo": "801101905_1395499972005699_8079754551198071440_n.jpg",
        "nombre_original": "Espacios_Publicos_y_Catastro.jpg",
    },
    {
        "cui": "2522883",
        "archivo": "735786531_1040900295136992_1112678435801449893_n.jpg",
        "nombre_original": "Parque_Familiar_La_Familia_Picol.jpg",
    },
    {
        "cui": "2522883",
        "archivo": "799283679_28811691101853258_3705260113283840604_n.jfif",
        "nombre_original": "Parque_La_Familia_Juegos_Infantiles.jpg",
    },
    {
        "cui": "2467397",
        "archivo": "486734698_1056924373144853_3236457455046161517_n.jpg",
        "nombre_original": "Saneamiento_Pallpancay_Agua_Potable.jpg",
    },
    {
        "cui": "2613404",
        "archivo": "489956440_1070942651743025_6810371396394434290_n.jpg",
        "nombre_original": "Movilidad_Urbana_Rinconada_Pistas.jpg",
    },
    {
        "cui": "2613404",
        "archivo": "845684218_2082129092669174_2718253166898853855_n.jfif",
        "nombre_original": "Rinconada_Drenaje_Pluvial.jpg",
    },
    {
        "cui": "2493635",
        "archivo": "549285108_1200268395477116_4037664823477546900_n.jpg",
        "nombre_original": "Complejo_Deportivo_Sucso_Aucaylle.jpg",
    },
]

def seed():
    src_base = Path("/app/uploads_seed")
    dest_base = Path("/var/data/uploads/obras")
    session = SessionLocal()

    # Obtener el usuario responsable
    user = session.execute(
        text("SELECT id FROM auth.usuarios WHERE usuario = 'jmerma' LIMIT 1")
    ).scalar_one_or_none()
    if not user:
        user = session.execute(
            text("SELECT id FROM auth.usuarios LIMIT 1")
        ).scalar_one()

    print(f"Usuario asignador: {user}")

    for s in SEEDS:
        src_file = src_base / s["archivo"]
        if not src_file.exists():
            print(f"Archivo no encontrado en seed: {src_file}")
            continue

        cui_dest = dest_base / s["cui"] / "foto"
        cui_dest.mkdir(parents=True, exist_ok=True)

        # Destino final
        dest_filename = s["archivo"].replace(".jfif", ".jpg")
        dest_file = cui_dest / dest_filename
        shutil.copy2(src_file, dest_file)

        ruta_relativa = f"obras/{s['cui']}/foto/{dest_filename}"
        tamano = dest_file.stat().st_size
        mime = "image/jpeg"

        # Verificar si ya existe en sistema.documentos_obra
        existe = session.execute(
            text("SELECT 1 FROM sistema.documentos_obra WHERE ruta_relativa = :r"),
            {"r": ruta_relativa},
        ).first()

        if not existe:
            doc_id = str(uuid.uuid4())
            session.execute(
                text("""
                    INSERT INTO sistema.documentos_obra (
                        id, codigo_unico_obra, tipo, nombre_original, ruta_relativa,
                        mime_type, tamano_bytes, subido_por, subido_en, publicado
                    ) VALUES (
                        :id, :cui, 'foto'::tipo_documento_obra, :nombre_original, :ruta,
                        :mime, :tamano, :subido_por, now(), true
                    )
                """),
                {
                    "id": doc_id,
                    "cui": s["cui"],
                    "nombre_original": s["nombre_original"],
                    "ruta": ruta_relativa,
                    "mime": mime,
                    "tamano": tamano,
                    "subido_por": user,
                },
            )
            print(f"Registrada foto para CUI {s['cui']}: {ruta_relativa} ({tamano} bytes)")
        else:
            print(f"Foto ya registrada para CUI {s['cui']}: {ruta_relativa}")

    session.commit()
    session.close()
    print("Seed de fotos completado con éxito.")

if __name__ == "__main__":
    seed()
