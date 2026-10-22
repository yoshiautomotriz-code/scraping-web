"""
Servidor Local para el Visualizador y Ejecución del Scraper OECE
Inicia un servidor HTTP ligero en el puerto 8000 que permite:
1. Visualizar la interfaz index.html
2. Ejecutar búsquedas en tiempo real llamando directamente a scraper_oece.py desde el navegador
"""

import sys
import os
import json
import urllib.parse
from http.server import SimpleHTTPRequestHandler, HTTPServer
from datetime import datetime

# Importar funciones del scraper existente
try:
    from scraper_oece import buscar_contrataciones, exportar_resultados
except ImportError:
    print("[Error] No se encontró 'scraper_oece.py' en la carpeta actual.")
    sys.exit(1)

PUERTO = 8000
DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))

class HandlerScraper(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORIO_ACTUAL, **kwargs)

    def end_headers(self):
        # Habilitar CORS y evitar caché en respuestas API
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        url_parseada = urllib.parse.urlparse(self.path)
        ruta = url_parseada.path
        
        # Endpoint para ejecutar el scraper desde el buscador del index.html
        if ruta == "/api/buscar":
            params = urllib.parse.parse_qs(url_parseada.query)
            query = params.get('q', [''])[0].strip()
            anio_param = params.get('anio', [''])[0].strip()
            
            if not query:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Debe proporcionar una palabra clave en 'q'"}).encode('utf-8'))
                return

            anio = None
            if anio_param and anio_param.upper() != 'ALL' and anio_param.isdigit():
                anio = int(anio_param)
            elif not anio_param:
                anio = datetime.now().year

            print(f"\n[API] Petición de búsqueda recibida: '{query}' | Año: {anio or 'Todos'}")
            
            try:
                # Separar palabras clave si ingresó varias separadas por coma o espacio
                palabras = [p.strip() for p in query.replace(',', ' ').split() if p.strip()]
                
                # Ejecutar el scraper con las palabras clave ingresadas desde la web
                resultados = buscar_contrataciones(
                    palabras_clave=palabras,
                    anio=anio,
                    limite_por_palabra=50
                )
                
                # Exportar automáticamente para persistir en disco
                exportar_resultados(resultados, "contrataciones_oece")
                
                # Responder con los datos al frontend
                respuesta_bytes = json.dumps(resultados, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(respuesta_bytes)))
                self.end_headers()
                self.wfile.write(respuesta_bytes)
                print(f"[API] Búsqueda completada y {len(resultados)} registros enviados al navegador.")
            except Exception as e:
                print(f"[API Error] Error al ejecutar búsqueda: {e}")
                err_bytes = json.dumps({"error": str(e)}, ensure_ascii=False).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(err_bytes)))
                self.end_headers()
                self.wfile.write(err_bytes)
            return

        # Redirigir la raíz a index.html
        if ruta == "/" or ruta == "":
            self.path = "/index.html"
            
        return super().do_GET()

def iniciar_servidor():
    os.chdir(DIRECTORIO_ACTUAL)
    server_address = ('', PUERTO)
    httpd = HTTPServer(server_address, HandlerScraper)
    print("=" * 60)
    print(f" Servidor OECE Activo")
    print(f" Abre en tu navegador: http://localhost:{PUERTO}")
    print(f" Presiona Ctrl+C para detener el servidor")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
        httpd.server_close()

if __name__ == "__main__":
    iniciar_servidor()
