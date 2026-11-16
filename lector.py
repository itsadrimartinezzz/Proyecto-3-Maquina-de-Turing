from pathlib import Path

import yaml


class TextLoader(yaml.SafeLoader):
    # Lee numeros y booleanos como texto pero respeta null
    pass


TextLoader.yaml_implicit_resolvers = {
    first: [(tag, regex) for tag, regex in resolvers if tag in ('tag:yaml.org,2002:null', 'tag:yaml.org,2002:merge')]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_machine(path):
    # Lee el archivo YAML solicitado
    try:
        text = Path(path).read_text(encoding='utf-8')
    except (OSError, UnicodeError) as error:
        raise ValueError(f'No se pudo leer el YAML: {error}') from error
    return parse_machine(text)


def parse_machine(text):
    # Valida y normaliza la configuracion
    try:
        config = yaml.load(text, Loader=TextLoader)
    except yaml.YAMLError as error:
        raise ValueError(f'No se pudo leer el YAML: {error}') from error
    if not isinstance(config, dict):
        raise ValueError('El YAML debe contener una configuración de máquina.')
    required = ['q_states', 'alphabet', 'tape_alphabet', 'delta', 'simulation_strings']
    if any(field not in config for field in required):
        raise ValueError('Faltan campos: q_states, alphabet, tape_alphabet, delta o simulation_strings.')
    states = config['q_states']
    if not isinstance(states, dict) or any(key not in states for key in ['q_list', 'initial', 'final']):
        raise ValueError('q_states necesita q_list, initial y final.')
    state_list = states['q_list']
    if not isinstance(state_list, list) or not state_list or any(not isinstance(s, str) or not s for s in state_list):
        raise ValueError('Los estados deben ser textos no vacíos.')
    if len(set(state_list)) != len(state_list):
        raise ValueError('Hay estados repetidos.')
    final = states['final'] if isinstance(states['final'], list) else [states['final']]
    if not final or any(state not in state_list for state in [states['initial'], *final]):
        raise ValueError('El estado inicial y los finales deben estar en q_list.')
    states['final'] = final
    alphabet = config['alphabet']
    tape_alphabet = config['tape_alphabet']
    for symbols in [alphabet, tape_alphabet]:
        if not isinstance(symbols, list) or any(s is not None and (not isinstance(s, str) or len(s) != 1) for s in symbols):
            raise ValueError('Los alfabetos deben ser listas de símbolos de un carácter.')
        if len(set(symbols)) != len(symbols):
            raise ValueError('Hay símbolos repetidos en un alfabeto.')
    if None in alphabet:
        raise ValueError('El alfabeto de entrada no admite null.')
    # Completa la cinta con la entrada y el blanco
    tape_alphabet = [*tape_alphabet, *(s for s in [*alphabet, None] if s not in tape_alphabet)]
    config['tape_alphabet'] = tape_alphabet
    strings = config['simulation_strings']
    if not isinstance(strings, list):
        raise ValueError('simulation_strings debe ser una lista de cadenas.')
    config['simulation_strings'] = ['' if text is None else text for text in strings]
    if any(not isinstance(text, str) for text in config['simulation_strings']):
        raise ValueError('simulation_strings debe contener solo cadenas.')
    if not isinstance(config['delta'], list):
        raise ValueError('delta debe ser una lista de transiciones.')
    seen = set()
    for rule in config['delta']:
        if not isinstance(rule, dict) or not isinstance(rule.get('params'), dict) or not isinstance(rule.get('output'), dict):
            raise ValueError('Cada transición necesita params y output.')
        source, target = rule['params'], rule['output']
        if any(k not in source for k in ['initial_state', 'mem_cache_value', 'tape_input']) or any(k not in target for k in ['final_state', 'mem_cache_value', 'tape_output', 'tape_displacement']):
            raise ValueError('Una transición tiene campos incompletos.')
        if source['initial_state'] not in state_list or target['final_state'] not in state_list:
            raise ValueError('Una transición usa un estado que no existe.')
        values = [source['tape_input'], target['tape_output'], source['mem_cache_value'], target['mem_cache_value']]
        if any(value not in tape_alphabet for value in values):
            raise ValueError('Las lecturas, escrituras y valores de memoria deben pertenecer al alfabeto de cinta.')
        if target['tape_displacement'] not in ['L', 'R', 'S']:
            raise ValueError('El movimiento debe ser L, R o S.')
        key = (source['initial_state'], source['mem_cache_value'], source['tape_input'])
        if key in seen:
            raise ValueError('Hay dos transiciones para el mismo estado, memoria y símbolo.')
        seen.add(key)
    return config
