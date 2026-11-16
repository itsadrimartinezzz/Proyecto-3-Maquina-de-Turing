import json
import sys
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lector import load_machine
from servidor import AppHandler


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Levanta un servidor temporal para las pruebas
        cls.server = HTTPServer(('127.0.0.1', 0), AppHandler)
        cls.server.config = load_machine(ROOT / 'ejemplos' / 'espejo.yaml')
        cls.server.machine = None
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        # Cierra el servidor temporal
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def post(self, path, data, origin=None):
        # Envia una solicitud JSON al servidor
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        request = Request(self.url + path, data=json.dumps(data).encode(), headers=headers)
        with urlopen(request) as response:
            return json.load(response)

    def test_all_demonstrations_through_api(self):
        # Simula los ejemplos mediante HTTP
        sums = ['10001', '100000', '1110', '10001', 'Rechazada']
        for name, results in [('reconocedora', ['Aceptada', 'Aceptada', 'Rechazada', 'Rechazada']), ('alteradora', sums)]:
            config = self.post('/api/example', {'name': name})
            for text, expected in zip(config['simulation_strings'], results):
                current = self.post('/api/prepare', {'text': text})
                descriptions = [current['description']]
                while current['status'] == 'Lista':
                    result = self.post('/api/step', {'count': 50})
                    descriptions.extend(frame['description'] for frame in result['frames'])
                    current = result['current']
                self.assertEqual(current['status'] if name == 'reconocedora' or expected == 'Rechazada' else current['output'], expected)
                self.assertEqual(len(descriptions), current['steps'] + 1)

    def test_upload_and_bad_input(self):
        # Prueba carga de archivos y errores
        text = (ROOT / 'ejemplos' / 'incremento.yaml').read_text(encoding='utf-8')
        self.post('/api/load', {'text': text})
        with self.assertRaises(HTTPError) as error:
            self.post('/api/prepare', {'text': 'abc'})
        self.assertEqual(error.exception.code, 400)
        with self.assertRaises(HTTPError):
            self.post('/api/load', {'text': 'invalid: ['})
        self.assertEqual(self.post('/api/prepare', {'text': '11111'})['state'], 'q0')

    def test_static_routes_and_origin(self):
        # Verifica rutas publicas y origen permitido
        for path in ['/', '/estilos.css', '/app.js']:
            with urlopen(self.url + path) as response:
                self.assertEqual(response.status, 200)
        with self.assertRaises(HTTPError) as error:
            self.post('/api/example', {'name': 'reconocedora'}, 'https://example.org')
        self.assertEqual(error.exception.code, 403)
        with self.assertRaises(HTTPError):
            urlopen(self.url + '/maquina.py')

    def test_reload_keeps_the_loaded_example(self):
        # Conserva el ejemplo al recargar configuracion
        self.post('/api/example', {'name': 'alteradora'})
        with urlopen(self.url + '/api/config') as response:
            saved = json.load(response)
        self.assertEqual(saved['example'], 'alteradora')
        self.assertEqual(saved['config']['alphabet'], ['0', '1', '+'])

    def test_invalid_step_group_does_not_change_the_machine(self):
        # Mantiene la maquina ante grupos invalidos
        self.post('/api/example', {'name': 'alteradora'})
        self.post('/api/prepare', {'text': '1011+110'})
        for count in [0, 51, True, '1']:
            with self.assertRaises(HTTPError) as error:
                self.post('/api/step', {'count': count})
            self.assertEqual(error.exception.code, 400)
        self.assertEqual(self.post('/api/step', {'count': 1})['current']['steps'], 1)


if __name__ == '__main__':
    unittest.main()
