from datetime import datetime, timezone

# -----------------------------
# Conjuntos permitidos (1:1 con Appwrite)
# -----------------------------

# Facultades ITM
FACULTADES = {
    "artes_humanidades",
    "ingenierias",
    "ciencias_economicas_administrativas",
    "ciencias_exactas_aplicadas",
}

# Carreras de pregrado ITM (profesionales + tecnologías) + 'otra'
CARRERAS = {
    # Artes y Humanidades
    "artes_grabacion_produccion_musical",
    "artes_visuales",
    "cine",
    "ingenieria_diseno_industrial",
    "tecnologia_diseno_industrial",
    "tecnologia_informatica_musical",
    "interpretacion_traduccion_lsc_espanol",

    # Ciencias Económicas y Administrativas
    "administracion_deporte",
    "administracion_tecnologica",
    "contaduria_publica",
    "ingenieria_produccion",
    "ingenieria_financiera_negocios",
    "ingenieria_calidad",
    "tecnologia_sistemas_produccion",
    "tecnologia_analisis_costos_presupuestos",
    "tecnologia_calidad",
    "tecnologia_gestion_administrativa",

    # Ciencias Exactas y Aplicadas
    "ciencias_ambientales",
    "ingenieria_biomedica",
    "quimica_industrial",
    "tecnologia_construccion_acabados_arquitectonicos",
    "tecnologia_mantenimiento_equipo_biomedico",

    # Ingenierías
    "ingenieria_sistemas",
    "ingenieria_ciencias_datos",
    "ingenieria_telecomunicaciones",
    "ingenieria_electromecanica",
    "ingenieria_electronica",
    "ingenieria_mecatronica",
    "tecnologia_automatizacion_electronica",
    "tecnologia_sistemas_informacion",
    "tecnologia_sistemas_electromecanicos",
    "tecnologia_gestion_redes_telecomunicaciones",
    "tecnologia_diseno_programacion_software_saas",
    "tecnologia_desarrollo_apps_moviles",
    "tecnologia_desarrollo_software",

    # Opción libre
    "otra",
}

# Encuesta de IA
ENUMS = {
    "familiaridad": {"nada", "poco", "algo", "bastante", "muy"},
    "definicion": {"reglas", "aprendizaje", "creatividad", "razonamiento", "no_seguro", "otro"},
    "herramientas": {"chatgpt", "gemini", "copilot", "claude", "midjourney", "dalle", "perplexity", "leonardo", "otra"},
    "frecuencia": {"nunca", "mensual", "semanal", "varios_dias_semana", "diaria"},
    "usos": {"estudio", "trabajo", "programacion", "contenido", "entretenimiento", "diseno", "productividad", "otra"},
    "confianza": {"nada", "poca", "regular", "bastante", "total"},
    "percepcion_social": {"muy_negativo", "negativo", "neutro", "positivo", "muy_positivo"},
    "regulacion": {"estricta", "flexible", "libre", "nsnc"},
    "emocion": {"curiosidad", "entusiasmo", "indiferencia", "inquietud", "miedo"},
    "sectores": {"educacion", "salud", "tecnologia", "arte_medios", "finanzas", "transporte", "gobierno", "otro"},
    # Nuevos:
    "facultad": FACULTADES,
    "carrera": CARRERAS,
}

# Campos que son arrays
ARRAY_FIELDS = {"herramientas", "usos", "sectores"}

# Campos opcionales de texto "otro"
OTRO_TEXT_FIELDS = {
    "definicion": "definicion_otro_texto",
    "herramientas": "herramientas_otra_texto",
    "usos": "usos_otra_texto",
    "sectores": "sectores_otro_texto",
    "carrera": "carrera_otro_texto",
}

# -----------------------------
# Utilidades
# -----------------------------
def now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def _is_non_empty_string(value):
    return isinstance(value, str) and value.strip() != ""

def validate_payload(payload: dict):
    """
    Valida y 'limpia' el payload entrante.
    Retorna (ok: bool, data_or_errors: dict)
    """
    errors = {}
    data = {}

    # --- Requeridos NO enum ---
    # nombre_completo (1–120 chars)
    nc = payload.get("nombre_completo")
    if not _is_non_empty_string(nc) or len(nc.strip()) > 120:
        errors["nombre_completo"] = "Requerido (1–120 caracteres)."
    else:
        data["nombre_completo"] = nc.strip()

    # edad (15–99)
    edad = payload.get("edad")
    if not isinstance(edad, int) or not (15 <= edad <= 99):
        errors["edad"] = "Debe ser un entero entre 15 y 99."
    else:
        data["edad"] = edad

    # --- Requeridos enum (una sola opción) ---
    required_enums = [
        "facultad", "carrera",
        "familiaridad", "definicion", "frecuencia", "confianza",
        "percepcion_social", "regulacion", "emocion",
    ]
    for field in required_enums:
        val = payload.get(field)
        if val is None:
            errors[field] = "Campo requerido."
        elif val not in ENUMS[field]:
            errors[field] = f"Valor inválido: {val}"
        else:
            data[field] = val

    # --- Requeridos (array) ---
    for field in ARRAY_FIELDS:
        arr = payload.get(field)
        if not isinstance(arr, list):
            errors[field] = "Debe ser un arreglo (lista)."
            continue
        invalids = [v for v in arr if v not in ENUMS[field]]
        if invalids:
            errors[field] = f"Valores inválidos: {invalids}"
        else:
            # Elimina duplicados conservando orden
            seen = set()
            cleaned = []
            for v in arr:
                if v not in seen:
                    cleaned.append(v)
                    seen.add(v)
            data[field] = cleaned

    # --- Campos opcionales de metadatos (si los envías y existen en tu colección) ---
    for opt in ["respondente_id", "origen", "version_app", "idioma", "consentimiento"]:
        if opt in payload:
            data[opt] = payload.get(opt)

    # --- Campos "otro_texto" (solo si corresponde) ---
    for base_field, text_field in OTRO_TEXT_FIELDS.items():
        text_val = payload.get(text_field)

        # enum simple
        if base_field in required_enums:
            if data.get(base_field) in {"otro", "otra"}:
                if not _is_non_empty_string(text_val):
                    errors[text_field] = "Requerido cuando se elige 'otro/otra'."
                else:
                    data[text_field] = text_val.strip()[:120]
            else:
                if _is_non_empty_string(text_val):
                    data[text_field] = text_val.strip()[:120]

        # arrays
        elif base_field in ARRAY_FIELDS:
            chosen = data.get(base_field, [])
            if "otra" in chosen or "otro" in chosen:
                if not _is_non_empty_string(text_val):
                    errors[text_field] = "Requerido cuando se elige 'otra/otro'."
                else:
                    data[text_field] = text_val.strip()[:120]
            else:
                if _is_non_empty_string(text_val):
                    data[text_field] = text_val.strip()[:120]

    # --- Timestamp controlado por backend ---
    data["creado_en"] = now_iso_utc()

    ok = len(errors) == 0
    return (ok, data if ok else errors)
