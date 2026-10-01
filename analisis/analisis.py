"""
Análisis de la encuesta "Ausentismo voluntario (capar clase)".

Lee el CSV exportado de Google Forms (ya depurado a mano), lo normaliza,
separa las preguntas de selección múltiple y genera:

  - data/encuesta_limpia.csv  -> una fila por respuesta, variables codificadas
  - data/codebook.csv         -> diccionario de variables
  - js/data.js                -> agregados que consumen las diapositivas
  - graficas/*.png            -> versiones estáticas de las gráficas (para el informe)

Uso (desde la raíz del repositorio):
    py analisis/analisis.py        (Windows)
    python3 analisis/analisis.py   (Mac / Linux)

Requiere: pandas, numpy, matplotlib
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CSV = RAIZ / "Encuesta Recoleccion Datos (Respuestas) - Respuestas de formulario 1.csv"
SALIDA_DATA = RAIZ / "data"
SALIDA_JS = RAIZ / "js" / "data.js"
SALIDA_PNG = RAIZ / "graficas"

# Población objetivo: estudiantes de PREGRADO matriculados en la U. de La Sabana,
# periodo 2026-1. Los 4 248 de posgrado quedan fuera (la encuesta se dirigió solo a pregrado).
# Fuente: Universidad de La Sabana (2026), La Sabana en cifras (unisabana.edu.co/la-sabana-en-cifras)
POBLACION_N = 9665
POSGRADO_EXCLUIDOS = 4248

# --------------------------------------------------------------------------
# Opciones del instrumento (texto exacto del formulario)
# --------------------------------------------------------------------------
NA = "N/A: No Aplica"

FRECUENCIA = [
    "Nunca o casi nunca (menos de 1 vez por semestre)",
    "Ocasionalmente (1 a 2 veces al mes)",
    "Frecuentemente (1 a 2 veces por semana)",
    "Muy frecuentemente (3 o más veces por semana)",
]
FRECUENCIA_CORTA = ["Nunca o casi nunca", "Ocasionalmente", "Frecuentemente", "Muy frecuentemente"]

MOTIVOS = {
    "Carga académica excesiva / Necesidad de estudiar o hacer trabajos para otra materia": "Carga académica / trabajos de otra materia",
    "Desinterés por la asignatura o la metodología del docente": "Desinterés por la asignatura o el docente",
    "Cansancio, necesidad de descanso o salud mental": "Cansancio, descanso o salud mental",
    "Compromisos personales, laborales o de movilidad": "Compromisos personales, laborales o movilidad",
    "Actividades de ocio o sociales": "Ocio o actividades sociales",
}
HORARIOS = {
    "Primeras horas de la mañana (7:00 a. m. - 9:00 a. m.)": "Primeras horas (7–9 a. m.)",
    "Horarios del mediodía o bloques intermedios": "Mediodía / bloques intermedios",
    "Últimas horas de la tarde / noche": "Tarde / noche",
    "Días viernes o adyacentes a fines de semana / festivos": "Viernes o puentes",
    "No depende del horario o día, depende únicamente de la materia": "Depende de la materia",
}
ASIGNATURAS = {
    "Clases teóricas magistrales con muchos estudiantes": "Magistrales con muchos estudiantes",
    "Materias complementarias o electivas fuera de la especialidad de la carrera": "Electivas / fuera de la especialidad",
    "Asignaturas donde el profesor no controla la asistencia": "No se controla la asistencia",
    "Clases cuyo contenido se puede aprender de forma autodidacta con lecturas/diapositivas": "Se puede aprender solo (lecturas/diapositivas)",
    "Me resulta indiferente el tipo de asignatura": "Indiferente",
}
ACTIVIDADES = {
    "Adelantar tareas, proyectos o estudiar para exámenes": "Adelantar tareas o estudiar",
    "Dormir o descansar en casa/campus": "Dormir o descansar",
    "Compartir con amigos o compañeros dentro o fuera de la universidad": "Compartir con amigos",
    "Entretenimiento personal (redes sociales, series, videojuegos, etc.)": "Entretenimiento (redes, series, juegos)",
    "Trámites personales o trabajo": "Trámites personales o trabajo",
}
IMPACTO_REND = {
    "No me afecta en absoluto; mantengo mis calificaciones esperadas": "No me afecta",
    "Me afecta levemente, pero lo logro compensar estudiando por mi cuenta": "Leve, lo compenso",
    "Me afecta negativamente; perjudica mis notas o comprensión de los temas": "Me afecta negativamente",
    "Depende de la exigencia de la materia": "Depende de la materia",
}
IMPACTO_PSICO = {
    "Alivio o tranquilidad por haber aprovechado el tiempo en otra prioridad": "Alivio / tranquilidad",
    "Preocupación o culpa por haberme perdido información importante": "Preocupación o culpa",
    "Indiferencia": "Indiferencia",
    "Satisfacción por el descanso o el espacio personal obtenido": "Satisfacción por el descanso",
    "Presión o estrés por la acumulación posterior de deberes y actividades pendientes": "Estrés por acumulación",
    "Aislamiento o desconexión respecto a las dinámicas y temas discutidos por el grupo de pares": "Desconexión del grupo",
    "Temor o paranoia ante la posibilidad de que las autoridades académicas notifiquen a mis tutores o familiares": "Temor a que avisen a la familia",
    "Incomodidad o tensión al regresar a la siguiente sesión lectiva frente al docente": "Incomodidad frente al docente",
}
FACTORES = {
    "Que la asistencia sea obligatoria y afecte directamente la nota": "Asistencia obligatoria que afecta la nota",
    "Que las clases sean dinámicas, interactivas y aporten valor que no está en los libros": "Clases dinámicas que aportan valor",
    "La realización de evaluaciones continuas, quices o talleres no anunciados": "Quices / talleres no anunciados",
    "El valor económico de la matrícula / costo del crédito académico": "Costo de la matrícula",
    "El sentido de compromiso ético y responsabilidad": "Compromiso ético y responsabilidad",
    "Profesor/a es atractivo/a": "Profesor/a atractivo/a",
    "Profesor/a es amable": "Profesor/a amable",
}
FACULTAD_CORTA = {
    "Facultad de Ingeniería": "Ingeniería",
    "Facultad de Comunicación": "Comunicación",
    "Escuela Internacional de Ciencias Económicas y Administrativas": "EICEA",
    "Facultad de Ciencias del Comportamiento": "Cs. del Comportamiento",
    "Facultad de Medicina": "Medicina",
    "Facultad de Estudios Jurídicos, Políticos e Internacionales": "Jurídicas y Políticas",
    "Facultad de Filosofía y Ciencias Humanas": "Filosofía y Cs. Humanas",
    "Facultad de Ciencias de la Vida y el Bienestar": "Cs. de la Vida",
    "Facultad de Educación": "Educación",
    "Escuela de Gobierno": "Escuela de Gobierno",
    "Instituto Forum": "Instituto Forum",
    "Instituto Latinoamericano de la Familia ILFARUS": "ILFARUS",
}

# Respuestas escritas en "Otros" que se agrupan bajo una misma etiqueta
OTROS_NORMALIZA = {
    "salud fisica": "Otro: salud física",
    "salud física": "Otro: salud física",
}


def separar_multiple(valor: str, opciones: dict[str, str]) -> tuple[list[str], list[str]]:
    """Google Forms une las casillas con ', ' pero varias opciones contienen comas,
    así que se buscan las opciones conocidas como subcadenas y lo que sobra es 'Otros'."""
    if pd.isna(valor):
        return [], []
    resto = str(valor)
    elegidas = []
    for largo in sorted(opciones, key=len, reverse=True):
        if largo in resto:
            elegidas.append(largo)
            resto = resto.replace(largo, "")
    tiene_na = NA in resto
    resto = resto.replace(NA, "")
    otros = [p.strip() for p in resto.split(",") if p.strip()]
    if tiene_na:
        elegidas.append(NA)
    return elegidas, otros


def etiqueta_otro(texto: str) -> str:
    return OTROS_NORMALIZA.get(texto.strip().lower(), f"Otro: {texto.strip()}")


def contar_multiple(serie: pd.Series, opciones: dict[str, str], n: int) -> dict:
    cnt: Counter = Counter()
    otros: Counter = Counter()
    combinaciones = []
    for v in serie:
        sel, ot = separar_multiple(v, opciones)
        for s in sel:
            cnt[opciones.get(s, "N/A")] += 1
        for o in ot:
            otros[etiqueta_otro(o)] += 1
        combinaciones.append(len([s for s in sel if s != NA]) + len(ot))
    filas = [{"label": opciones[k], "n": cnt[opciones[k]]} for k in opciones]
    filas += [{"label": k, "n": v, "otro": True} for k, v in otros.items()]
    filas.sort(key=lambda r: -r["n"])
    for r in filas:
        r["pct"] = round(100 * r["n"] / n, 1)
    return {
        "items": filas,
        "na": cnt["N/A"],
        "promedio_opciones": round(float(np.mean([c for c in combinaciones if c > 0])), 2),
    }


def contar_simple(serie: pd.Series, opciones: dict[str, str] | list[str], n: int, incluir_na=True) -> dict:
    if isinstance(opciones, list):
        opciones = {o: o for o in opciones}
    vc = serie.value_counts()
    filas = [{"label": opciones[k], "n": int(vc.get(k, 0))} for k in opciones]
    na = int(vc.get(NA, 0))
    for r in filas:
        r["pct"] = round(100 * r["n"] / n, 1)
    return {"items": filas, "na": na, "na_pct": round(100 * na / n, 1)}


def spearman_permutacion(x: np.ndarray, y: np.ndarray, reps: int = 20000, semilla: int = 7):
    """Rho de Spearman con valor p por permutación (no requiere scipy)."""
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    rho = float(np.corrcoef(rx, ry)[0, 1])
    rng = np.random.default_rng(semilla)
    sims = np.array([np.corrcoef(rx, rng.permutation(ry))[0, 1] for _ in range(reps)])
    p = float((np.abs(sims) >= abs(rho)).mean())
    return round(rho, 3), round(p, 3)


def main():
    df = pd.read_csv(CSV, dtype=str)
    c = list(df.columns)
    n = len(df)

    # ---------------- Variables codificadas -----------------------------
    programa_cols = [col for col in c if "programa base" in col.lower()]
    programa = df[programa_cols].bfill(axis=1).iloc[:, 0]

    limpio = pd.DataFrame({
        "id": range(1, n + 1),
        "fecha": pd.to_datetime(df[c[0]], format="%d/%m/%Y %H:%M:%S").dt.strftime("%Y-%m-%d %H:%M"),
        "consentimiento": (df[c[11]].notna()).astype(int),
        "semestre": df[c[1]].str.extract(r"(\d+)")[0].astype(int),
        "facultad": df[c[12]].map(FACULTAD_CORTA),
        "programa_base": programa,
        "doble_programa": df[c[14]],
        "promedio": pd.to_numeric(df[c[13]].str.replace(",", "."), errors="coerce"),
        "frecuencia": df[c[2]].map({t: i + 1 for i, t in enumerate(FRECUENCIA)}),
        "horario": df[c[4]].map({**HORARIOS, NA: "N/A"}),
        "impacto_rend": df[c[7]].map({**IMPACTO_REND, NA: "N/A"}),
        "impacto_psico": df[c[8]].map({**IMPACTO_PSICO, NA: "N/A"}),
        "material_virtual": df[c[10]].astype(int),
    })
    # Dummies 0/1 para las preguntas de selección múltiple
    for prefijo, col, ops in [("mot", c[3], MOTIVOS), ("asig", c[5], ASIGNATURAS),
                              ("act", c[6], ACTIVIDADES), ("fac", c[9], FACTORES)]:
        sel = df[col].apply(lambda v: separar_multiple(v, ops))
        for i, op in enumerate(ops, start=1):
            limpio[f"{prefijo}_{i}"] = sel.apply(lambda s: int(op in s[0]))
        limpio[f"{prefijo}_otro"] = sel.apply(lambda s: "; ".join(s[1]) if s[1] else "")

    SALIDA_DATA.mkdir(exist_ok=True)
    limpio.to_csv(SALIDA_DATA / "encuesta_limpia.csv", index=False, encoding="utf-8-sig")

    # ---------------- Agregados para las diapositivas -------------------
    sem = limpio["semestre"].value_counts().sort_index()
    fac = limpio["facultad"].value_counts()
    prom = limpio["promedio"].dropna()

    freq = contar_simple(df[c[2]], dict(zip(FRECUENCIA, FRECUENCIA_CORTA)), n)
    capan = int((limpio["frecuencia"] >= 2).sum())

    # Cruce frecuencia x promedio
    gpa_por_freq = []
    for i, nombre in enumerate(FRECUENCIA_CORTA, start=1):
        vals = limpio.loc[(limpio["frecuencia"] == i) & limpio["promedio"].notna(), "promedio"]
        gpa_por_freq.append({
            "label": nombre,
            "valores": [round(float(v), 2) for v in vals],
            "media": round(float(vals.mean()), 2) if len(vals) else None,
            "n": int(len(vals)),
        })
    sub = limpio.dropna(subset=["promedio"])
    rho, p_rho = spearman_permutacion(sub["frecuencia"].to_numpy(), sub["promedio"].to_numpy())

    # Cruce frecuencia x impacto en rendimiento
    orden_imp = list(IMPACTO_REND.values()) + ["N/A"]
    tabla = pd.crosstab(limpio["frecuencia"], limpio["impacto_rend"]).reindex(
        index=[1, 2, 3, 4], columns=orden_imp, fill_value=0)
    # "Muy frecuentemente" tiene n=1: se agrupa con "Frecuentemente" para que el % tenga sentido
    tabla.loc[3] = tabla.loc[3] + tabla.loc[4]
    tabla = tabla.drop(index=4)
    cruce_imp = {
        "filas": ["Nunca o casi nunca", "Ocasionalmente", "Frecuentemente o más"],
        "columnas": orden_imp,
        "conteos": tabla.to_numpy().tolist(),
    }

    mv = limpio["material_virtual"].value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)

    # Tamaño de muestra para ±5 %: n = N·Z²·p·q / (e²(N−1) + Z²·p·q), con Z=1.96, p=q=0.5.
    # Margen de error con n=56, con corrección por población finita.
    z, p, q, e_obj, N = 1.96, 0.5, 0.5, 0.05, POBLACION_N
    n_0 = z**2 * p * q / e_obj**2
    n_5_exacto = N * z**2 * p * q / (e_obj**2 * (N - 1) + z**2 * p * q)
    n_5 = int(np.ceil(n_5_exacto))
    fpc = np.sqrt((N - n) / (N - 1))
    e = z * np.sqrt(p * q / n) * fpc

    data = {
        "n": n,
        "fechas": {"inicio": limpio["fecha"].min()[:10], "fin": limpio["fecha"].max()[:10]},
        "muestreo": {"z": z, "p": p, "N": N, "N_posgrado_excluido": POSGRADO_EXCLUIDOS,
                     "error_logrado": round(100 * e, 1), "error_logrado_exacto": round(100 * e, 3),
                     "n_infinita": int(np.ceil(n_0)), "n_para_5_exacto": round(n_5_exacto, 2),
                     "n_para_5": n_5},
        "semestre": {"labels": [f"{s}.°" for s in sem.index], "n": sem.tolist()},
        "facultad": {"labels": fac.index.tolist(), "n": fac.tolist(),
                     "pct": [round(100 * v / n, 1) for v in fac]},
        "programas_top": limpio["programa_base"].value_counts().head(6).to_dict(),
        "doble_programa": int(limpio["doble_programa"].notna().sum()),
        "promedio": {"n": int(len(prom)), "media": round(float(prom.mean()), 2),
                     "mediana": round(float(prom.median()), 2),
                     "min": float(prom.min()), "max": float(prom.max()),
                     "faltantes": int(n - len(prom))},
        "frecuencia": freq,
        "capan_alguna_vez": {"n": capan, "pct": round(100 * capan / n, 1)},
        "motivos": contar_multiple(df[c[3]], MOTIVOS, n),
        "horario": contar_simple(df[c[4]], HORARIOS, n),
        "asignaturas": contar_multiple(df[c[5]], ASIGNATURAS, n),
        "actividades": contar_multiple(df[c[6]], ACTIVIDADES, n),
        "impacto_rend": contar_simple(df[c[7]], IMPACTO_REND, n),
        "impacto_psico": contar_simple(df[c[8]], IMPACTO_PSICO, n),
        "factores": contar_multiple(df[c[9]], FACTORES, n),
        "material_virtual": {"labels": ["1", "2", "3", "4", "5"], "n": mv.tolist(),
                             "media": round(float(limpio["material_virtual"].mean()), 2)},
        "gpa_por_freq": gpa_por_freq,
        "spearman": {"rho": rho, "p": p_rho, "n": int(len(sub))},
        "cruce_impacto": cruce_imp,
    }

    SALIDA_JS.parent.mkdir(exist_ok=True)
    SALIDA_JS.write_text(
        "// Archivo generado por analisis/analisis.py — no editar a mano.\n"
        "window.DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )

    codebook = escribir_codebook(c)
    # El codebook debe tener exactamente las mismas variables, y en el mismo orden, que la base limpia
    assert codebook["variable"].tolist() == limpio.columns.tolist(), "codebook y encuesta_limpia no coinciden"
    graficas_png(data)

    print(f"Respuestas: {n}")
    print(f"Capan al menos ocasionalmente: {capan} ({100 * capan / n:.1f} %)")
    print(f"Promedio acumulado: media {prom.mean():.2f} (n={len(prom)})")
    print(f"Spearman frecuencia vs promedio: rho={rho}, p={p_rho}")
    print(f"Población N={N} (pregrado)  |  n para ±5 %: {n_5_exacto:.2f} -> {n_5}")
    print(f"Margen de error con n={n}: ±{100 * e:.3f} % (≈ ±{100 * e:.1f} %)")
    print(f"Codebook: {len(codebook)} variables (= columnas de encuesta_limpia.csv)")
    print(f"Escrito: {SALIDA_JS.relative_to(RAIZ)}, data/, graficas/")


def escribir_codebook(c: list[str]) -> pd.DataFrame:
    """Una fila por columna de data/encuesta_limpia.csv. El texto de las preguntas se toma
    de los encabezados del CSV de Forms y el de las opciones, de las constantes de arriba
    (texto exacto del formulario, que es el que aparece en las celdas del CSV)."""
    def preg(i: int) -> str:
        return " ".join(str(c[i]).split())

    OBLIG = "No admite faltantes (campo obligatorio)"
    NA_COD = "'N/A' = marcó «N/A: No Aplica» (no capa clase); no admite vacíos (campo obligatorio)"

    def opciones_simples(ops: dict[str, str]) -> str:
        return " · ".join(f"'{corta}' = «{larga}»" for larga, corta in ops.items()) + " · 'N/A' = «N/A: No Aplica»"

    filas = [
        ("id", "Identificador de respuesta", "— (generado por el script)", "Numérica", "Nominal", "1…n",
         "No admite faltantes (lo genera el script)", "Único, no vacío"),
        ("fecha", "Marca temporal", preg(0), "Fecha", "Intervalo", "AAAA-MM-DD HH:MM",
         "No admite faltantes (Forms la registra siempre)", "Dentro del periodo de recolección"),
        ("consentimiento", "Acepta aviso de privacidad", preg(11), "Categórica", "Nominal", "1 = Acepta",
         OBLIG, "Obligatoria; si 0 se descarta"),
        ("semestre", "Semestre con mayor carga", preg(1), "Numérica discreta", "Ordinal", "1–10 (10 = 10 o más)",
         OBLIG, "Entero entre 1 y 10"),
        ("facultad", "Facultad", preg(12), "Categórica", "Nominal",
         " · ".join(f"'{corta}' = «{larga}»" for larga, corta in FACULTAD_CORTA.items()),
         OBLIG, "Una de las 12 facultades"),
        ("programa_base", "Programa base", preg(16) + " (12 columnas de Forms, una por facultad, unidas en una)",
         "Categórica", "Nominal", "Lista por facultad (texto del formulario)",
         OBLIG, "Debe pertenecer a la facultad elegida"),
        ("doble_programa", "Segundo programa", preg(14), "Categórica", "Nominal", "Lista de pregrados",
         "NA (vacío) = no hace doble programa", "≠ programa_base"),
        ("promedio", "Promedio acumulado", preg(13), "Numérica continua", "Razón", "0.00–5.00",
         "NA (vacío) = no respondió (pregunta opcional) o valor anulado en la limpieza",
         "Punto decimal; 0 < x < 5; descartar valores no creíbles"),
        ("frecuencia", "Frecuencia de ausentismo", preg(2), "Categórica", "Ordinal",
         " · ".join(f"{i} = «{t}»" for i, t in enumerate(FRECUENCIA, start=1)),
         OBLIG, "Obligatoria, una opción"),
        ("horario", "Horario en que más falta", preg(4), "Categórica", "Nominal", opciones_simples(HORARIOS),
         NA_COD, "Una opción"),
        ("impacto_rend", "Impacto en el rendimiento", preg(7), "Categórica", "Nominal", opciones_simples(IMPACTO_REND),
         NA_COD, "Una opción"),
        ("impacto_psico", "Impacto psicológico", preg(8), "Categórica", "Nominal", opciones_simples(IMPACTO_PSICO),
         NA_COD, "Una opción"),
        ("material_virtual", "Efecto del material virtual", preg(10), "Numérica discreta", "Ordinal (Likert)",
         "1 Disminuye mucho … 3 Sin efecto … 5 Aumenta mucho", OBLIG, "Entero 1–5"),
    ]
    # Selección múltiple: una variable 0/1 por opción + una variable de texto para "Otros"
    for prefijo, i_col, ops, tema, tiene_na in [("mot", 3, MOTIVOS, "Motivo", True),
                                                ("asig", 5, ASIGNATURAS, "Tipo de asignatura", True),
                                                ("act", 6, ACTIVIDADES, "Uso del tiempo", True),
                                                ("fac", 9, FACTORES, "Factor que disminuye el deseo de faltar", False)]:
        faltante = ("0 (N/A): quien marcó «N/A: No Aplica» queda con 0 en todas las opciones" if tiene_na
                    else "No admite faltantes (campo obligatorio); 0 = no marcó la opción")
        for k, (larga, corta) in enumerate(ops.items(), start=1):
            filas.append((f"{prefijo}_{k}", f"{tema}: {corta}", preg(i_col),
                          "Dicotómica (multirrespuesta)", "Nominal", f"1 = marcó «{larga}» · 0 = no la marcó",
                          faltante, "0 o 1" + ("; N/A no debe combinarse con otras opciones" if tiene_na else "")))
        filas.append((f"{prefijo}_otro", f"{tema}: texto de «Otros»", preg(i_col), "Texto abierto", "Nominal",
                      "Texto libre escrito en «Otros» (varias entradas separadas por '; ')",
                      "Vacío = no escribió nada en «Otros»",
                      "No vacío ni solo espacios; recodificar si encaja en una categoría existente"))

    codebook = pd.DataFrame(filas, columns=["variable", "etiqueta", "pregunta_origen", "tipo", "escala",
                                            "valores_codigos", "codigo_faltante", "regla_validacion"])
    codebook.to_csv(SALIDA_DATA / "codebook.csv", index=False, encoding="utf-8-sig")
    return codebook


def graficas_png(data: dict):
    """Versiones estáticas (para pegar en el informe escrito)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    SALIDA_PNG.mkdir(exist_ok=True)
    azul, gris = "#2a78d6", "#b9b8b0"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "axes.spines.top": False, "axes.spines.right": False})

    def barras_h(nombre, bloque, titulo):
        items = [r for r in bloque["items"] if r["n"] > 0][::-1]
        fig, ax = plt.subplots(figsize=(9, 0.5 * len(items) + 1.4))
        colores = [gris if r.get("otro") else azul for r in items]
        ax.barh([r["label"] for r in items], [r["pct"] for r in items], color=colores, height=0.6)
        for i, r in enumerate(items):
            ax.text(r["pct"] + 0.8, i, f'{r["pct"]:.0f} % ({r["n"]})', va="center", fontsize=10)
        ax.set_xlabel(f"% de los {data['n']} encuestados")
        ax.set_title(titulo, loc="left", fontweight="bold")
        ax.set_xlim(0, max(r["pct"] for r in items) * 1.25)
        ax.grid(axis="x", alpha=0.25)
        fig.tight_layout()
        fig.savefig(SALIDA_PNG / f"{nombre}.png", dpi=180)
        plt.close(fig)

    barras_h("frecuencia", data["frecuencia"], "¿Con qué frecuencia capa clase?")
    barras_h("motivos", data["motivos"], "Motivos para no asistir (selección múltiple)")
    barras_h("horario", data["horario"], "Horario en que más falta")
    barras_h("asignaturas", data["asignaturas"], "Tipo de asignatura que más se capa (selección múltiple)")
    barras_h("actividades", data["actividades"], "¿Qué hace con ese tiempo? (selección múltiple)")
    barras_h("impacto_rendimiento", data["impacto_rend"], "Impacto percibido en el rendimiento")
    barras_h("impacto_psicologico", data["impacto_psico"], "Impacto psicológico más frecuente")
    barras_h("factores", data["factores"], "Factores que disminuyen el deseo de faltar (selección múltiple)")

    # Facultad
    fig, ax = plt.subplots(figsize=(9, 4))
    f = data["facultad"]
    ax.barh(f["labels"][::-1], f["n"][::-1], color=azul, height=0.6)
    ax.set_title("Encuestados por facultad", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(SALIDA_PNG / "facultad.png", dpi=180); plt.close(fig)

    # Promedio por frecuencia
    fig, ax = plt.subplots(figsize=(8, 4.5))
    rng = np.random.default_rng(1)
    for i, g in enumerate(data["gpa_por_freq"]):
        if not g["valores"]:
            continue
        x = i + rng.uniform(-0.12, 0.12, len(g["valores"]))
        ax.scatter(x, g["valores"], s=40, color=azul, alpha=0.7, edgecolor="white")
        ax.hlines(g["media"], i - 0.25, i + 0.25, color="#0b0b0b", lw=2)
    ax.set_xticks(range(4), [f'{g["label"]}\n(n={g["n"]})' for g in data["gpa_por_freq"]])
    ax.set_ylabel("Promedio acumulado")
    s = data["spearman"]
    ax.set_title(f"Promedio según frecuencia de ausentismo  (Spearman ρ = {s['rho']}, p = {s['p']})",
                 loc="left", fontweight="bold", fontsize=11)
    fig.tight_layout(); fig.savefig(SALIDA_PNG / "promedio_vs_frecuencia.png", dpi=180); plt.close(fig)

    # Material virtual
    fig, ax = plt.subplots(figsize=(7, 3.8))
    mv = data["material_virtual"]
    ax.bar(mv["labels"], mv["n"], color=["#2a78d6", "#86b6ef", gris, "#f0a3a2", "#e34948"], width=0.6)
    ax.set_xlabel("1 = disminuye mucho la probabilidad de faltar · 5 = la aumenta mucho")
    ax.set_title(f"Efecto del material virtual (media {mv['media']})", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(SALIDA_PNG / "material_virtual.png", dpi=180); plt.close(fig)


if __name__ == "__main__":
    main()
