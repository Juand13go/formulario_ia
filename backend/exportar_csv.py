import os, sys
import pandas as pd
from dotenv import load_dotenv
from appwrite.client import Client
from appwrite.services.databases import Databases

try:
    from appwrite.query import Query
    HAS_QUERY = True
except Exception:
    HAS_QUERY = False

BASE_DIR = os.path.dirname(__file__)
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

APPWRITE_ENDPOINT      = os.getenv("APPWRITE_ENDPOINT", "https://cloud.appwrite.io/v1")
APPWRITE_PROJECT_ID    = os.getenv("APPWRITE_PROJECT_ID") or os.getenv("APPWRITE_PROJECT")
APPWRITE_API_KEY       = os.getenv("APPWRITE_API_KEY")
APPWRITE_DATABASE_ID   = os.getenv("APPWRITE_DATABASE_ID") or os.getenv("APPWRITE_DATABASE")
APPWRITE_COLLECTION_ID = os.getenv("APPWRITE_COLLECTION_ID") or os.getenv("APPWRITE_COLLECTION")

CSV_PATH = os.path.join(BASE_DIR, "respuestas_ia.csv")

ORDERED_HEADER = [
    "creado_en","nombre_completo","edad","facultad","carrera","carrera_otro_texto",
    "familiaridad","definicion","definicion_otro_texto",
    "herramientas","herramientas_otra_texto",
    "frecuencia","usos","usos_otra_texto",
    "confianza","percepcion_social","regulacion","emocion",
    "sectores","sectores_otro_texto",
]

def assert_env():
    missing = [k for k,v in {
        "APPWRITE_ENDPOINT": APPWRITE_ENDPOINT,
        "APPWRITE_PROJECT_ID": APPWRITE_PROJECT_ID,
        "APPWRITE_API_KEY": APPWRITE_API_KEY,
        "APPWRITE_DATABASE_ID": APPWRITE_DATABASE_ID,
        "APPWRITE_COLLECTION_ID": APPWRITE_COLLECTION_ID,
    }.items() if not v]
    if missing:
        raise RuntimeError(f"Faltan variables en .env: {', '.join(missing)}")

def make_client():
    assert_env()
    client = Client()
    client.set_endpoint(APPWRITE_ENDPOINT)
    client.set_project(APPWRITE_PROJECT_ID)
    client.set_key(APPWRITE_API_KEY)
    return client

def fetch_all(databases, db_id, col_id, page_size=100):
    docs, offset = [], 0
    while True:
        if HAS_QUERY:
            resp = databases.list_documents(
                db_id, col_id, queries=[Query.limit(page_size), Query.offset(offset)]
            )
        else:
            resp = databases.list_documents(
                db_id, col_id, queries=[f"limit({page_size})", f"offset({offset})"]
            )
        batch = resp.get("documents", [])
        docs.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return docs

def normalize_documents(docs):
    """Convierte la lista de documentos de Appwrite a registros planos (dicts)."""
    rows = []
    for d in docs:
        # algunos SDK devuelven los campos en d["data"], otros plano
        payload = d.get("data") if isinstance(d.get("data"), dict) else d
        # filtramos metadatos de Appwrite para no ensuciar el CSV
        filtered = {k: v for k, v in payload.items() if not k.startswith("$")}
        # arrays -> "a;b;c"
        for k, v in list(filtered.items()):
            if isinstance(v, list):
                filtered[k] = ";".join(map(str, v))
        rows.append(filtered)
    return rows

def reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
    present = [c for c in ORDERED_HEADER if c in df.columns]
    rest = [c for c in df.columns if c not in present]
    return df[present + rest]

def exportar():
    client = make_client()
    db = Databases(client)
    docs = fetch_all(db, APPWRITE_DATABASE_ID, APPWRITE_COLLECTION_ID)

    print(f"📦 Documentos recibidos: {len(docs)}")
    if docs:
        # muestra un documento crudo
        sample = docs[0]
        print("🔎 Ejemplo crudo (truncado):", {k: sample.get(k) for k in list(sample)[:10]})

    rows = normalize_documents(docs)

    # muestra fila normalizada
    if rows:
        print("🧪 Ejemplo normalizado:", {k: rows[0].get(k) for k in list(rows[0])[:10]})

    # si no hay filas, igual generamos CSV con encabezado base
    if not rows:
        print("⚠️ No hay datos para escribir. Generando CSV con encabezado base.")
        df = pd.DataFrame(columns=ORDERED_HEADER)
    else:
        df = pd.DataFrame.from_records(rows)
        df = reorder_columns(df)

    # write
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    size = os.path.getsize(CSV_PATH) if os.path.exists(CSV_PATH) else 0
    print(f"✅ CSV escrito en: {CSV_PATH} (tamaño: {size} bytes)")
    if size == 0:
        print("⚠️ El archivo quedó en 0 bytes. Cierra Excel/Notepad si lo tienes abierto e inténtalo de nuevo.")

if __name__ == "__main__":
    try:
        exportar()
    except Exception as e:
        print(f"❌ Error exportando: {e}", file=sys.stderr)
        sys.exit(1)
