"""
Módulo de Extracción y Limpieza de Contrataciones Abiertas de Perú (OECE / OSCE)
Portal: https://contratacionesabiertas.oece.gob.pe
"""

import sys
import os
import json
import time
import requests
import pandas as pd
from datetime import datetime

# Garantizar compatibilidad UTF-8 en consola de Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

API_SEARCH_URL = "https://contratacionesabiertas.oece.gob.pe/api/v1/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9"
}

def formatear_monto(monto, moneda="PEN"):
    """Formatea montos en soles o dólares con separador de miles y símbolo."""
    if monto is None:
        return "No especificado"
    simbolo = "S/." if moneda == "PEN" else ("US$" if moneda == "USD" else moneda)
    try:
        return f"{simbolo} {float(monto):,.2f}"
    except (ValueError, TypeError):
        return f"{simbolo} {monto}"

def normalizar_registro(item, palabra_clave):
    """
    Toma un registro OCDS (compiledRelease) del OECE y extrae los campos clave
    de forma limpia, estructurada y sin duplicados ni fragmentos rotos de HTML.
    """
    cr = item.get("compiledRelease", {})
    tender = cr.get("tender", {})
    buyer = cr.get("buyer", {})
    procuring_entity = tender.get("procuringEntity", {})
    sources = cr.get("sources", [{}])
    
    # 1. Identificadores
    ocid = cr.get("ocid") or tender.get("id") or "N/A"
    tender_id = tender.get("id") or tender.get("officialNumber") or "N/A"
    
    # 2. Información del proceso
    titulo = tender.get("title") or "Sin título"
    descripcion = tender.get("description") or tender.get("title") or "Sin descripción"
    
    # 3. Entidad compradora
    entidad_nombre = (buyer.get("name") or procuring_entity.get("name") or "Entidad no especificada").strip()
    entidad_id = (buyer.get("id") or procuring_entity.get("id") or "N/A").strip()
    
    # 4. Monto y Moneda
    val = tender.get("value", {}) or {}
    monto_num = val.get("amount")
    moneda = val.get("currency") or "PEN"
    monto_fmt = formatear_monto(monto_num, moneda)
    
    # 5. Fechas y temporalidad
    fecha_raw = cr.get("date") or tender.get("tenderPeriod", {}).get("startDate") or ""
    anio = None
    mes = None
    fecha_formateada = "N/A"
    if fecha_raw:
        try:
            # Parsear fecha ISO (e.g. 2026-02-15T00:00:00-05:00)
            fecha_dt = datetime.fromisoformat(fecha_raw.replace("Z", "+00:00"))
            anio = fecha_dt.year
            mes = f"{fecha_dt.month:02d}"
            fecha_formateada = fecha_dt.strftime("%d/%m/%Y")
        except Exception:
            if len(fecha_raw) >= 10:
                fecha_formateada = fecha_raw[:10]
                anio = int(fecha_raw[:4]) if fecha_raw[:4].isdigit() else None
    
    # Si no se pudo sacar del date, intentar de dataSegmentation
    if not anio and "dataSegmentation" in cr:
        seg_id = str(cr["dataSegmentation"].get("id", ""))
        if len(seg_id) >= 4 and seg_id[:4].isdigit():
            anio = int(seg_id[:4])
            if len(seg_id) >= 7:
                mes = seg_id[5:7]
    
    # 6. Procedimiento, categoría y sistema
    metodo = tender.get("procurementMethodDetails") or tender.get("procurementMethod") or "No especificado"
    categoria = tender.get("mainProcurementCategory") or "No clasificado"
    sistema_nombre = sources[0].get("name", "SEACE") if sources else "SEACE"
    
    # 7. Enlace web directo a la ficha del proceso en el portal OECE
    enlace_portal = f"https://contratacionesabiertas.oece.gob.pe/proceso/{ocid}"
    
    return {
        "ocid": ocid,
        "id_licitacion": tender_id,
        "titulo": titulo,
        "descripcion": descripcion,
        "entidad": entidad_nombre,
        "entidad_codigo": entidad_id,
        "monto": monto_num,
        "moneda": moneda,
        "monto_formateado": monto_fmt,
        "metodo": metodo,
        "categoria": categoria,
        "fecha_publicacion": fecha_formateada,
        "anio": anio,
        "mes": mes,
        "sistema": sistema_nombre,
        "enlace_proceso": enlace_portal,
        "palabras_clave": [palabra_clave]
    }

def buscar_contrataciones(palabras_clave, anio=None, limite_por_palabra=50, pausa_segundos=0.5):
    """
    Realiza la búsqueda de contrataciones en contratacionesabiertas.oece.gob.pe
    por una lista de palabras clave (ej: ['firewall', 'antispam']).
    
    Retorna una lista de diccionarios estructurados únicos por 'ocid'.
    """
    if isinstance(palabras_clave, str):
        palabras_clave = [palabras_clave]
        
    print(f"\n=======================================================")
    print(f" Iniciando búsqueda OECE - Contrataciones Abiertas")
    print(f" Palabras clave: {', '.join(palabras_clave)}")
    if anio:
        print(f" Filtro de Año: {anio}")
    print(f" Límite por palabra: {limite_por_palabra} registros")
    print(f"=======================================================\n")
    
    mapa_registros = {} # Llave: ocid -> registro estructurado
    
    for kw in palabras_clave:
        kw = kw.strip()
        if not kw:
            continue
            
        print(f"🔍 Consultando palabra clave: '{kw}'...")
        pagina = 1
        tamano_pagina = min(limite_por_palabra, 20)
        obtenidos_kw = 0
        total_disponible = 0
        
        while obtenidos_kw < limite_por_palabra:
            params = {
                "search": kw,
                "page": pagina,
                "paginateBy": tamano_pagina,
                "format": "json"
            }
            if anio:
                params["year"] = anio
                
            try:
                resp = requests.get(API_SEARCH_URL, params=params, headers=HEADERS, timeout=20)
                if resp.status_code != 200:
                    print(f"  [Aviso] La API respondió con código {resp.status_code} en página {pagina}")
                    break
                    
                data = resp.json()
                total_disponible = data.get("pagination", {}).get("total_results", 0)
                results = data.get("results", [])
                
                if not results:
                    break
                    
                for raw_item in results:
                    reg = normalizar_registro(raw_item, kw)
                    ocid = reg["ocid"]
                    
                    if ocid in mapa_registros:
                        # Si ya existe por otra palabra clave, agregamos la etiqueta
                        if kw not in mapa_registros[ocid]["palabras_clave"]:
                            mapa_registros[ocid]["palabras_clave"].append(kw)
                    else:
                        mapa_registros[ocid] = reg
                        
                    obtenidos_kw += 1
                    if obtenidos_kw >= limite_por_palabra:
                        break
                        
                # Si ya leímos todos los resultados disponibles en la BD
                if pagina * tamano_pagina >= total_disponible:
                    break
                    
                pagina += 1
                time.sleep(pausa_segundos)
                
            except Exception as e:
                print(f"  [Error] Fallo al consultar '{kw}' en página {pagina}: {e}")
                break
                
        print(f"  -> Total encontrados en base de datos: {total_disponible}. Extraídos: {obtenidos_kw}")
        
    registros_finales = list(mapa_registros.values())
    
    # Ordenar por año (más reciente primero) y luego por título
    registros_finales.sort(key=lambda x: (x["anio"] or 0, x["titulo"]), reverse=True)
    
    print(f"\n Extracción finalizada: {len(registros_finales)} procesos únicos encontrados.")
    return registros_finales

def exportar_resultados(registros, ruta_base="contrataciones_oece"):
    """
    Exporta la lista de contrataciones a:
    1. Archivo JSON estructurado (.json)
    2. Archivo JavaScript (.js) para visualizador HTML directo sin problemas de CORS
    3. Archivo Excel (.xlsx) para reportes de oficina
    """
    if not registros:
        print("No hay registros para exportar.")
        return None, None
        
    ruta_json = f"{ruta_base}.json"
    ruta_js = "contrataciones_data.js"
    ruta_excel = f"{ruta_base}.xlsx"
    
    # 1. Guardar JSON estructurado
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(registros, f, indent=2, ensure_ascii=False)
    print(f" JSON estructurado guardado en: '{ruta_json}'")
    
    # 2. Guardar JS para visualización directa en HTML (evita problemas de CORS al abrir localmente)
    with open(ruta_js, "w", encoding="utf-8") as f:
        f.write("/** Datos pre-cargados para el visualizador HTML **/\n")
        f.write("window.CONTRATACIONES_DATA = ")
        json.dump(registros, f, indent=2, ensure_ascii=False)
        f.write(";\n")
    print(f" Datos para visor HTML guardados en: '{ruta_js}'")
    
    # 3. Guardar Excel estructurado
    try:
        # Preparamos copia plana para DataFrame (palabras_clave unidas por coma)
        df_list = []
        for r in registros:
            copia = dict(r)
            copia["palabras_clave"] = ", ".join(r["palabras_clave"])
            df_list.append(copia)
            
        df = pd.DataFrame(df_list)
        df.rename(columns={
            "ocid": "OCID",
            "id_licitacion": "ID SEACE",
            "titulo": "Nomenclatura / Título",
            "descripcion": "Descripción del Proceso",
            "entidad": "Entidad Compradora",
            "entidad_codigo": "Código/RUC Entidad",
            "monto": "Monto Numérico",
            "moneda": "Moneda",
            "monto_formateado": "Monto Formateado",
            "metodo": "Procedimiento",
            "categoria": "Categoría",
            "fecha_publicacion": "Fecha Convocatoria",
            "anio": "Año",
            "mes": "Mes",
            "sistema": "Sistema Origen",
            "enlace_proceso": "Enlace Ficha Portal OECE",
            "palabras_clave": "Palabras Clave"
        }, inplace=True)
        
        df.to_excel(ruta_excel, index=False)
        print(f" Archivo Excel guardado en: '{ruta_excel}'")
    except Exception as e:
        print(f" [Aviso] No se pudo generar Excel: {e}")
        
    return ruta_json, ruta_excel

if __name__ == "__main__":
    # Palabras clave solicitadas por el usuario: firewall, antispam, etc.
    palabras = ["firewall", "antispam"]
    
    # Si el usuario pasó argumentos por línea de comandos (ej: python scraper_oece.py firewall switch)
    if len(sys.argv) > 1:
        palabras = sys.argv[1:]
        
    # Realizar búsqueda (puedes ajustar el límite por palabra o el año)
    resultados = buscar_contrataciones(
        palabras_clave=palabras,
        anio=None,  # Puedes poner 2026, 2025 o None para todos los años
        limite_por_palabra=50
    )
    
    exportar_resultados(resultados, "contrataciones_oece")
