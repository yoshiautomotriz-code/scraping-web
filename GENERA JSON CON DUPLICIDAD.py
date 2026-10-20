"""
Extractor Limpio de Contrataciones Abiertas (OECE / OSCE Perú)
Reemplazo optimizado para 'GENERA JSON CON DUPLICIDAD.py'

Anteriormente este script intentaba leer bloques de un archivo HTML local ('pagina.html'),
lo que generaba:
1. Cientos de duplicados debido a etiquetas anidadas (div, li, tr).
2. Textos no estructurados unidos con plecas (" | ") sin nombres de campos.
3. Fallos al no encontrar 'pagina.html' o cuando la página Angular cargaba vacío.

Esta versión actualizada se conecta directamente a la API oficial de Contrataciones Abiertas:
https://contratacionesabiertas.oece.gob.pe/api/v1/search?search={termino}
Obtiene datos 100% oficiales, elimina duplicados automáticamente por 'ocid' y genera un JSON
completamente estructurado con montos, fechas, entidades y enlaces directos al portal.
"""

import sys
import os
import json
from scraper_oece import buscar_contrataciones, exportar_resultados

def ejecutar_extraccion(palabras=None, anio=None, limite=50):
    if palabras is None:
        palabras = ["firewall", "antispam"]
        
    print("=" * 65)
    print(" EXTRACCIÓN Y LIMPIEZA DE CONTRATACIONES OECE")
    print("=" * 65)
    
    # Realizar búsqueda limpia y estructurada
    registros = buscar_contrataciones(
        palabras_clave=palabras,
        anio=anio,
        limite_por_palabra=limite
    )
    
    if not registros:
        print("[!] No se encontraron registros para los criterios indicados.")
        return None
        
    # Exportar con nombres estándar y nombres de retrocompatibilidad
    exportar_resultados(registros, "contrataciones_oece")
    
    # Retrocompatibilidad con los nombres que ya usaba tu script
    json_legacy = "registros_contrataciones_2026.json"
    with open(json_legacy, "w", encoding="utf-8") as f:
        json.dump(registros, f, indent=4, ensure_ascii=False)
    print(f" Archivo JSON compatible generado: '{json_legacy}'")
    
    # Generar muestra en consola
    cadena_json = json.dumps(registros[:3], indent=4, ensure_ascii=False)
    print("\n--- MUESTRA DE DATOS ESTRUCTURADOS GENERADOS (PRIMEROS 3) ---")
    print(cadena_json)
    print(f"\n[OK] ¡Éxito! Se procesaron {len(registros)} contrataciones estructuradas.")
    print(" Puedes abrir 'index.html' en tu navegador para ver la información en tarjetas interactivas.")
    
    return registros

if __name__ == "__main__":
    # Puedes pasar términos por consola o usar los predeterminados: firewall, antispam
    terminos = sys.argv[1:] if len(sys.argv) > 1 else ["firewall", "antispam"]
    ejecutar_extraccion(palabras=terminos)