import os
import sys
import pandas as pd

BASE_DIR = os.path.dirname(__file__)
SRC_CSV = os.path.join(BASE_DIR, "respuestas_ia.csv")
OUT_CSV = os.path.join(BASE_DIR, "eda_ia_consolidado.csv")
ENCODING = "utf-8-sig"

# Campos multi (exportados como "a;b;c" en respuestas_ia.csv)
MULTI_COLS = ["usos", "herramientas", "sectores"]

# Enums simples
SIMPLE_ENUMS = [
    "familiaridad", "definicion", "frecuencia", "confianza",
    "percepcion_social", "regulacion", "emocion",
    "facultad", "carrera"
]

# Orden para Likert (útil para ordenar resultados)
LIKERT_ORDERS = {
    "familiaridad": ["nada", "poco", "algo", "bastante", "muy"],
    "confianza":    ["nada", "poca", "regular", "bastante", "total"],
    "percepcion_social": ["muy_negativo", "negativo", "neutro", "positivo", "muy_positivo"],
    "frecuencia": ["nunca", "mensual", "semanal", "varios_dias_semana", "diaria"],
    "regulacion": ["estricta", "flexible", "libre", "nsnc"],
    "emocion": ["curiosidad", "entusiasmo", "indiferencia", "inquietud", "miedo"],
}

def safe_read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        print("⚠️  respuestas_ia.csv no existe o está vacío. Exporta primero: python exportar_csv.py")
        sys.exit(0)
    try:
        return pd.read_csv(path, encoding=ENCODING)
    except pd.errors.EmptyDataError:
        print("⚠️  El CSV está vacío (sin cabecera/filas). Vuelve a exportar.")
        sys.exit(0)

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # strings: strip
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip().replace({"nan": ""})
    # edad: numérica
    if "edad" in df.columns:
        df["edad"] = pd.to_numeric(df["edad"], errors="coerce").astype("Float64")
    # fechas derivadas
    if "creado_en" in df.columns:
        df["creado_en_ts"] = pd.to_datetime(df["creado_en"], errors="coerce", utc=True)
        df["fecha"] = (
            df["creado_en_ts"]
            .dt.tz_convert("America/Bogota")
            .dt.date
        )
    # id_respuesta para referencia
    df = df.reset_index(drop=True)
    df.insert(0, "id_respuesta", df.index + 1)
    return df

def explode_multi_col(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns:
        return pd.DataFrame(columns=["id_respuesta", col])
    tmp = df[["id_respuesta", col]].copy()
    tmp[col] = tmp[col].fillna("").astype(str).apply(
        lambda s: [x.strip() for x in s.split(";") if x.strip()]
    )
    tmp = tmp.explode(col)
    tmp = tmp[tmp[col].astype(str).str.len() > 0].reset_index(drop=True)
    return tmp

def main():
    df = safe_read_csv(SRC_CSV)
    df = normalize_df(df)

    rows = []  # lista de dicts; luego se convierte en un único DataFrame

    # ===== Resumen =====
    total = len(df)
    facs = df["facultad"].nunique() if "facultad" in df.columns else 0
    cars = df["carrera"].nunique() if "carrera" in df.columns else 0
    edad_min = float(df["edad"].min()) if "edad" in df.columns and df["edad"].notna().any() else None
    edad_max = float(df["edad"].max()) if "edad" in df.columns and df["edad"].notna().any() else None
    edad_mean = float(df["edad"].mean()) if "edad" in df.columns and df["edad"].notna().any() else None

    rows += [
        {"dataset": "resumen", "metric": "total_respuestas", "value": total},
        {"dataset": "resumen", "metric": "facultades_unicas", "value": facs},
        {"dataset": "resumen", "metric": "carreras_unicas", "value": cars},
        {"dataset": "edad_stats", "metric": "edad_min", "value": edad_min},
        {"dataset": "edad_stats", "metric": "edad_max", "value": edad_max},
        {"dataset": "edad_stats", "metric": "edad_promedio", "value": round(edad_mean, 2) if edad_mean is not None else None},
    ]

    # ===== Por fecha =====
    if "fecha" in df.columns:
        fecha_counts = df["fecha"].value_counts().sort_index()
        for fecha, cnt in fecha_counts.items():
            rows.append({"dataset": "por_fecha", "fecha": str(fecha), "conteo": int(cnt)})

    # ===== Por facultad / carrera =====
    if "facultad" in df.columns:
        for val, cnt in df["facultad"].value_counts().items():
            rows.append({"dataset": "por_facultad", "facultad": val, "conteo": int(cnt)})

    if "carrera" in df.columns:
        for val, cnt in df["carrera"].value_counts().items():
            rows.append({"dataset": "por_carrera", "carrera": val, "conteo": int(cnt)})

    # ===== Frecuencias de enums simples =====
    for campo in SIMPLE_ENUMS:
        if campo in df.columns:
            vc = df[campo].value_counts(dropna=True)
            # ordenar si hay orden predefinido
            order = LIKERT_ORDERS.get(campo)
            items = (
                [(k, vc.get(k, 0)) for k in order]
                if order else list(vc.items())
            )
            for val, cnt in items:
                rows.append({
                    "dataset": "freq_simple",
                    "campo": campo,
                    "categoria": val,
                    "conteo": int(cnt),
                })

    # ===== Frecuencias de multi =====
    exploded = {}
    for col in MULTI_COLS:
        exploded[col] = explode_multi_col(df, col)
        if not exploded[col].empty:
            vc = exploded[col][col].value_counts()
            for val, cnt in vc.items():
                rows.append({
                    "dataset": "freq_multi",
                    "campo": col,
                    "categoria": val,
                    "conteo": int(cnt),
                })

    # ===== Cruces: facultad x familiaridad / confianza =====
    if "facultad" in df.columns and "familiaridad" in df.columns:
        pivot = df.groupby(["facultad", "familiaridad"]).size().reset_index(name="conteo")
        # ordenar familiaridad
        if "familiaridad" in LIKERT_ORDERS:
            pivot["familiaridad"] = pd.Categorical(
                pivot["familiaridad"], categories=LIKERT_ORDERS["familiaridad"], ordered=True
            )
            pivot = pivot.sort_values(["facultad", "familiaridad"])
        for _, r in pivot.iterrows():
            rows.append({
                "dataset": "cross_facultad_familiaridad",
                "facultad": r["facultad"],
                "familiaridad": str(r["familiaridad"]),
                "conteo": int(r["conteo"]),
            })

    if "facultad" in df.columns and "confianza" in df.columns:
        pivot = df.groupby(["facultad", "confianza"]).size().reset_index(name="conteo")
        if "confianza" in LIKERT_ORDERS:
            pivot["confianza"] = pd.Categorical(
                pivot["confianza"], categories=LIKERT_ORDERS["confianza"], ordered=True
            )
            pivot = pivot.sort_values(["facultad", "confianza"])
        for _, r in pivot.iterrows():
            rows.append({
                "dataset": "cross_facultad_confianza",
                "facultad": r["facultad"],
                "confianza": str(r["confianza"]),
                "conteo": int(r["conteo"]),
            })

    # ===== Construir y guardar CSV único =====
    eda_df = pd.DataFrame(rows)
    eda_df.to_csv(OUT_CSV, index=False, encoding=ENCODING)

    print(f"✅ EDA consolidado generado: {OUT_CSV}")
    print(f"   Filas totales: {len(eda_df)}")
    print("   Columna clave para segmentar: 'dataset'")

if __name__ == "__main__":
    main()
