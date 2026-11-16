import copy
import itertools
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml

from lector import load_machine, parse_machine
from maquina import TuringMachine


def run(config, text):
    # Ejecuta una maquina hasta detenerse
    machine = TuringMachine(config, text)
    while machine.step():
        pass
    return machine


class MachineTests(unittest.TestCase):
    def setUp(self):
        # Carga las maquinas de prueba
        self.mirror = load_machine(ROOT / 'ejemplos' / 'espejo.yaml')
        self.adder = load_machine(ROOT / 'ejemplos' / 'alteradora.yaml')
        self.copier = load_machine(ROOT / 'ejemplos' / 'duplicador.yaml')
        self.increment = load_machine(ROOT / 'ejemplos' / 'incremento.yaml')

    def test_required_examples(self):
        # Verifica los casos demostrativos
        for text, accepted in [('ab#ba#ab', True), ('abc#cba#abc', True), ('abc#caa#abc', False), ('abc#cba#abb', False)]:
            self.assertEqual(run(self.mirror, text).status == 'Aceptada', accepted)
        for text, output in [('1011+110', '10001'), ('11111+1', '100000'), ('1001+101', '1110'), ('110+1011', '10001')]:
            machine = run(self.adder, text)
            self.assertEqual(machine.status, 'Aceptada')
            self.assertEqual(machine.tape_text(), output)
        self.assertEqual(run(self.adder, '1101+10+1').status, 'Rechazada')

    def test_mirror_language_exhaustively(self):
        # Compara el lenguaje espejo completo
        for length in range(8):
            for symbols in itertools.product('abc#', repeat=length):
                text = ''.join(symbols)
                parts = text.split('#')
                expected = len(parts) == 3 and parts[1] == parts[0][::-1] and parts[2] == parts[0]
                self.assertEqual(run(self.mirror, text).status == 'Aceptada', expected, text)

    def test_binary_sum_exhaustively(self):
        # Suma todos los pares de binarios de hasta cuatro bits
        words = [''.join(bits) for length in range(5) for bits in itertools.product('01', repeat=length)]
        for x in words:
            for y in words:
                machine = run(self.adder, f'{x}+{y}')
                if not x and not y:
                    self.assertEqual(machine.status, 'Rechazada')
                    continue
                self.assertEqual(machine.status, 'Aceptada', f'{x}+{y}')
                self.assertEqual(int(machine.tape_text(), 2), int(x or '0', 2) + int(y or '0', 2), f'{x}+{y}')
        for text in ['101', '1+1+1', '']:
            self.assertEqual(run(self.adder, text).status, 'Rechazada', text)

    def test_copier_exhaustively(self):
        # Duplica toda cadena corta sobre a y b
        for length in range(8):
            for symbols in itertools.product('ab', repeat=length):
                text = ''.join(symbols)
                machine = run(self.copier, text)
                self.assertEqual((machine.status, machine.tape_text()), ('Aceptada', f'{text}#{text}'), text)

    def test_upload_accepts_pdf_style_yaml(self):
        # Acepta el formato flexible del enunciado
        config = parse_machine('''
q_states:
  q_list: [0, 1]
  initial: 0
  final: 1
alphabet: [a, b]
tape_alphabet:
- X
-
delta:
- params: {initial_state: 0, mem_cache_value: , tape_input: a}
  output: {final_state: 1, mem_cache_value: a, tape_output: , tape_displacement: R}
simulation_strings: [aab#aab, 0101, ab]
''')
        self.assertEqual(config['q_states']['initial'], '0')
        self.assertEqual(config['tape_alphabet'], ['X', None, 'a', 'b'])
        self.assertEqual(config['simulation_strings'], ['aab#aab', '0101', 'ab'])
        self.assertEqual(run(config, 'ab').status, 'Aceptada')
        with self.assertRaises(ValueError):
            TuringMachine(config, 'aab#aab')

    def test_binary_increment_range(self):
        # Comprueba incrementos binarios consecutivos
        for value in range(128):
            text = f'{value:07b}'
            self.assertEqual(run(self.increment, text).tape_text(), f'{value + 1:b}'.zfill(7))

    def test_negative_position_and_initial_description(self):
        # Revisa posiciones negativas y descripcion inicial
        machine = TuringMachine(self.increment, '11111')
        self.assertIn('[q0, B] 1', machine.description())
        while machine.step():
            pass
        self.assertEqual(machine.head, -1)
        self.assertEqual(machine.tape[-1], '1')
        self.assertFalse(machine.step())

    def test_empty_input_and_invalid_symbol(self):
        # Valida entradas vacias y simbolos invalidos
        self.assertEqual(run(self.mirror, '').status, 'Rechazada')
        self.assertEqual(run(self.mirror, '#').status, 'Rechazada')
        self.assertEqual(run(self.mirror, '##').status, 'Aceptada')
        self.assertEqual(run(self.increment, '').tape_text(), '1')
        with self.assertRaises(ValueError):
            TuringMachine(self.mirror, 'abd')

    def test_step_limit_is_not_rejection(self):
        # Distingue el limite del rechazo
        machine = TuringMachine(self.increment, '11111', max_steps=2)
        while machine.step():
            pass
        self.assertEqual(machine.status, 'Límite alcanzado')
        self.assertEqual(machine.steps, 2)

    def test_loader_rejects_bad_configurations(self):
        # Rechaza configuraciones YAML incorrectas
        cases = []
        config = copy.deepcopy(self.increment)
        config['delta'].append(config['delta'][0])
        cases.append(config)
        for field, value in [('tape_displacement', 'Z'), ('final_state', 'missing'), ('tape_output', 'z')]:
            config = copy.deepcopy(self.increment)
            config['delta'][0]['output'][field] = value
            cases.append(config)
        for config in cases:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'invalid.yaml'
                path.write_text(yaml.safe_dump(config), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_machine(path)


if __name__ == '__main__':
    unittest.main()
