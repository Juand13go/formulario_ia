import os
import importlib
from datetime import datetime
from flask import (
    Flask, request, jsonify, send_from_directory
)
from dotenv import load_dotenv

# Appwrite
from appwrite.client import Client
from appwrite.services.databases import Databases

# Validación de payload
# from utils import validate_payload
from .utils import validate_payload

# -------------------------------------------------------------------
# Configuración base
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
FRONT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

load_dotenv(os.path.join(BASE_DIR, ".env"))

APPWRITE_ENDPOINT       = os.getenv("APPWRITE_ENDPOINT", "https://cloud.appwrite.io/v1")
APPWRITE_PROJECT_ID     = os.getenv("APPWRITE_PROJECT_ID") or os.getenv("APPWRITE_PROJECT")
APPWRITE_API_KEY        = os.getenv("APPWRITE_API_KEY")
APPWRITE_DATABASE_ID    = os.getenv("APPWRITE_DATABASE_ID") or os.getenv("APPWRITE_DATABASE")
APPWRITE_COLLECTION_ID  = os.getenv("APPWRITE_COLLECTION_ID") or os.getenv("APPWRITE_COLLECTION")

# Flask
app = Flask(__name__, static_folder=FRONT_DIR, template_folder=None)
app.config["JSON_SORT_KEYS"] = False


# -------------------------------------------------------------------
# Utilidades
# -------------------------------------------------------------------
def make_appwrite():
    """Crea un cliente Appwrite configurado desde .env."""
    missing = [k for k, v in {
        "APPWRITE_ENDPOINT": APPWRITE_ENDPOINT,
        "APPWRITE_PROJECT_ID": APPWRITE_PROJECT_ID,
        "APPWRITE_API_KEY": APPWRITE_API_KEY,
        "APPWRITE_DATABASE_ID": APPWRITE_DATABASE_ID,
        "APPWRITE_COLLECTION_ID": APPWRITE_COLLECTION_ID,
    }.items() if not v]
    if missing:
        raise RuntimeError(f"Faltan variables en .env: {', '.join(missing)}")

    client = Client()
    client.set_endpoint(APPWRITE_ENDPOINT)
    client.set_project(APPWRITE_PROJECT_ID)
    client.set_key(APPWRITE_API_KEY)
    return client


def run_pipeline_once():
    """
    Ejecuta exportar_csv + analisis_datos una sola vez en arranque
    (y en cada recarga del reloader de Flask).
    """
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        try:
            exportar = importlib.import_module("exportar_csv")
            # Debe existir una función exportar() en exportar_csv.py
            exportar.exportar()
            print("[pipeline] Exportación completada.")
        except Exception as e:
            print(f"[pipeline] Error exportando CSV: {e}")

        try:
            analisis = importlib.import_module("analisis_datos")
            # Debe existir una función main() en analisis_datos.py
            analisis.main()
            print("[pipeline] Análisis (EDA) completado.")
        except Exception as e:
            print(f"[pipeline] Error en análisis: {e}")


# -------------------------------------------------------------------
# Rutas para FRONTEND estático
# -------------------------------------------------------------------
@app.get("/")
def home():
    """Entrega el formulario principal."""
    return send_from_directory(FRONT_DIR, "index.html")

@app.get("/csv.html")
def csv_panel():
    """Entrega la página del panel CSV (con clave simple en el front)."""
    return send_from_directory(FRONT_DIR, "csv.html")

@app.get("/<path:path>")
def assets(path):
    """Entrega cualquier archivo estático del frontend (CSS/JS/imagenes)."""
    return send_from_directory(FRONT_DIR, path)


# -------------------------------------------------------------------
# API - Crear respuesta
# -------------------------------------------------------------------
@app.post("/api/response")
def create_response():
    """
    Recibe el JSON del formulario, valida y guarda en Appwrite.
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"ok": False, "error": "JSON inválido"}), 400

    ok, data_or_errors = validate_payload(payload or {})
    if not ok:
        return jsonify({"ok": False, "errors": data_or_errors}), 422

    # Crear documento en Appwrite
    try:
        client = make_appwrite()
        databases = Databases(client)

        # El SDK moderno suele crear ID automático con ID.unique(); aquí
        # si no lo tienes, Appwrite genera uno si pasas "unique()".
        document = databases.create_document(
            database_id=APPWRITE_DATABASE_ID,
            collection_id=APPWRITE_COLLECTION_ID,
            document_id="unique()",   # ID automático
            data=data_or_errors
        )
        # Devuelve el documento creado y ok True
        return jsonify({"ok": True, "id": document.get("$id"), **data_or_errors}), 201

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# -------------------------------------------------------------------
# CSVs generados (export + EDA)
# -------------------------------------------------------------------
@app.get("/csv-data/<path:filename>")
def csv_data(filename):
    """
    Sirve archivos CSV generados en el backend (p.ej. respuestas_ia.csv, eda_ia_consolidado.csv).
    """
    return send_from_directory(BASE_DIR, filename)


@app.post("/api/recompute")
def recompute():
    """
    Recalcula export + EDA bajo demanda desde el botón del panel CSV.
    """
    try:
        exportar = importlib.import_module("exportar_csv")
        exportar.exportar()
        analisis = importlib.import_module("analisis_datos")
        analisis.main()
        return jsonify({"ok": True, "msg": "Recalculado"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Ejecutar pipeline al iniciar (y en cada recarga del reloader)
    run_pipeline_once()
    # Levantar servidor
    app.run(host="0.0.0.0", port=5000, debug=True)
