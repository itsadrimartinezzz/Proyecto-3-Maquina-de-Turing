import argparse
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from lector import load_machine, parse_machine
from maquina import TuringMachine


ROOT = Path(__file__).parent
EXAMPLES = {'reconocedora': 'espejo.yaml', 'alteradora': 'alteradora.yaml'}


def snapshot(machine):
    # Resume el estado actual para la interfaz
    left, right = machine.bounds()
    count = min(11, max(7, right - left + 3))
    start = left - (count - (right - left + 1)) // 2
    if right - left + 3 > count:
        start = machine.head - count // 2
    return {
        'state': machine.state, 'cache': machine.cache, 'head': machine.head,
        'steps': machine.steps, 'status': machine.status,
        'cells': [{'position': i, 'symbol': machine.tape.get(i)} for i in range(start, start + count)],
        'description': machine.description(), 'output': machine.tape_text(),
    }


class AppHandler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        # Envia una respuesta JSON sin cache
        content = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        # Atiende recursos estaticos y configuracion
        routes = {'/': ('index.html', 'text/html'), '/estilos.css': ('estilos.css', 'text/css'),
                  '/app.js': ('app.js', 'text/javascript')}
        path = urlparse(self.path).path
        if path == '/api/config':
            self.send_json({'config': self.server.config, 'example': getattr(self.server, 'example', 'reconocedora')})
            return
        if path not in routes:
            self.send_error(404)
            return
        name, content_type = routes[path]
        content = (ROOT / 'web' / name).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        # Rechaza solicitudes de otros sitios
        origin = self.headers.get('Origin')
        expected = f'http://127.0.0.1:{self.server.server_port}'
        if origin and origin != expected:
            self.send_json({'error': 'Origen no permitido.'}, 403)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 1_000_000:
                raise ValueError('El archivo debe ser menor a 1 MB.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('La solicitud debe ser un objeto.')
            path = urlparse(self.path).path
            if path == '/api/example':
                name = data.get('name')
                if name not in EXAMPLES:
                    raise ValueError('Ejemplo desconocido.')
                self.server.config = load_machine(ROOT / 'ejemplos' / EXAMPLES[name])
                self.server.example = name
                self.server.machine = None
                self.send_json(self.server.config)
            elif path == '/api/load':
                if not isinstance(data.get('text'), str):
                    raise ValueError('Selecciona un archivo YAML válido.')
                config = parse_machine(data['text'])
                self.server.config = config
                self.server.example = None
                self.server.machine = None
                self.send_json(config)
            elif path == '/api/prepare':
                text = data.get('text')
                if not isinstance(text, str):
                    raise ValueError('La cadena debe ser texto.')
                self.server.machine = TuringMachine(self.server.config, text)
                self.send_json(snapshot(self.server.machine))
            elif path == '/api/step':
                if self.server.machine is None:
                    raise ValueError('Prepara una cadena primero.')
                count = data.get('count', 1)
                if type(count) is not int or not 1 <= count <= 50:
                    raise ValueError('El grupo debe contener entre 1 y 50 pasos.')
                frames = []
                for _ in range(count):
                    if not self.server.machine.step():
                        break
                    frames.append(snapshot(self.server.machine))
                self.send_json({'frames': frames, 'current': snapshot(self.server.machine)})
            else:
                self.send_json({'error': 'Ruta desconocida.'}, 404)
        except (ValueError, UnicodeError, RecursionError) as error:
            self.send_json({'error': str(error)}, 400)

    def log_message(self, format, *args):
        # Mantiene silencioso el servidor local
        pass


def start_server():
    # Configura e inicia el servidor local
    parser = argparse.ArgumentParser(description='Proyecto 3: simulador web local de Turing.')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('El puerto debe estar entre 1 y 65535.')
    try:
        server = HTTPServer(('127.0.0.1', args.port), AppHandler)
    except OSError:
        parser.error('No se pudo abrir el puerto. Prueba: python main.py --port 8001')
    server.config = load_machine(ROOT / 'ejemplos' / EXAMPLES['reconocedora'])
    server.machine = None
    server.example = 'reconocedora'
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'Proyecto 3 está en {url}\nPresiona Ctrl+C para detenerlo.')
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor detenido.')
    finally:
        server.server_close()
