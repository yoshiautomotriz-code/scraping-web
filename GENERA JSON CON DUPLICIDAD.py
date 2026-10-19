from bs4 import BeautifulSoup
import pandas as pd
import json

def extraer_datos_universales():
    print("Analizando estructura de 'pagina.html'...")
    datos_limpios = []
    
    try:
        with open('pagina.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Estrategia 1: dfdfdfdddfffBuscar bloques estructurados comunes en portales OCDS (divs o listas)
        bloques = soup.find_all(['div', 'li', 'tr'])
        
        for bloque in bloques:
            # Buscamos sddsdsdssdsdsdsdsdsdstextos relevantes (ej: identificadores de contratación, entidades o montos)
            texto = bloque.get_text(separator=" | ", strip=True)
            
            # Filtramos textos largos o repetitivos para quedarnos solo con filas útiles de información
            if len(texto) > 15 and len(texto) < 600 and ('S/.' in texto or 'Convocatoria' in texto or '2026' in texto):
                # Intentamos extraer un enlace del proceso si existe
                enlace_tag = bloque.find('a', href=True)
                
                if enlace_tag:
                    href = enlace_tag['href']
                    # Si el enlace ya empieza con http, lo dejamos tal cual.
                    enlace = href if href.startswith('http') else f"https://contratacionesabiertas.oece.gob.pe{href if href.startswith('/') else '/' + href}"
                else:
                    enlace = "N/A"
                
                datos_limpios.append({
                    'informacion_detallada': texto,
                    'enlace_directo': enlace
                })
        
        # Eliminar duplicados generados por elementos anidados
        df = pd.DataFrame(datos_limpios).drop_duplicates(subset=['informacion_detallada'])
        
        if not df.empty:
            # 1. Guardar en Excel (como ya lo tenías)
            nombre_excel = "registros_contrataciones_2026.xlsx"
            df.to_excel(nombre_excel, index=False)
            
            # 2. GENERAR CADENA JSON
            # orient='records' genera una lista de diccionarios (ideal para APIs y bases de datos)
            # force_ascii=False mantiene los caracteres en español (tildes, ñ)
            cadena_json = df.to_json(orient='records', force_ascii=False, indent=4)
            
            # 3. Guardar también en un archivo .json por si lo necesitas
            nombre_json = "registros_contrataciones_2026.json"
            with open(nombre_json, 'w', encoding='utf-8') as f_json:
                f_json.write(cadena_json)
                
            print(f"\n¡Éxito total! Se encontraron {len(df)} filas con información.")
            print(f"Los datos se han guardado en: '{nombre_excel}' y '{nombre_json}'")
            print("\n--- MUESTRA DE LA CADENA JSON GENERADA ---")
            print(cadena_json[:500] + "\n... [continúa]") # Muestra solo los primeros 500 caracteres
            
            # Si necesitas retornar la cadena para usarla en otra función:
            return cadena_json

        else:
            # Estrategia alternativa si todo falla
            print("Aplicando estrategia secundaria: Extracción por enlaces activos...")
            enlaces_directos = []
            for a in soup.find_all('a', href=True):
                texto_enlace = a.get_text(strip=True)
                if len(texto_enlace) > 10:
                    enlaces_directos.append({
                        'descripcion': texto_enlace,
                        'url_proceso': f"https://contratacionesabiertas.oece.gob.pe{a['href']}" if a['href'].startswith('/') else a['href']
                    })
            
            df_alt = pd.DataFrame(enlaces_directos).drop_duplicates()
            if not df_alt.empty:
                df_alt.to_excel("enlaces_contrataciones.xlsx", index=False)
                
                # Generar JSON para la estrategia alternativa
                cadena_json_alt = df_alt.to_json(orient='records', force_ascii=False, indent=4)
                with open("enlaces_contrataciones.json", 'w', encoding='utf-8') as f_json:
                    f_json.write(cadena_json_alt)
                    
                print(f"Extracción completada. Se generó 'enlaces_contrataciones.xlsx' y '.json' con {len(df_alt)} registros.")
                return cadena_json_alt
            else:
                print("No se encontraron elementos legibles. Asegúrate de que guardaste el archivo completo con resultados visibles.")
                return None

    except FileNotFoundError:
        print("Error: No se encontró el archivo 'pagina.html'. Súbelo de nuevo a la carpeta raíz.")
        return None
    except Exception as e:
        print(f"Ocurrió un error inesperado durante el análisis: {e}")
        return None

if __name__ == "__main__":
    json_resultante = extraer_datos_universales()