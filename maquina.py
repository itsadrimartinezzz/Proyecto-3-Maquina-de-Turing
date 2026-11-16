class TuringMachine:
    def __init__(self, config, text, max_steps=10000):
        # Inicializa una simulacion nueva
        if any(symbol not in config['alphabet'] for symbol in text):
            raise ValueError('La cadena contiene símbolos fuera del alfabeto de entrada.')
        self.config = config
        self.state = config['q_states']['initial']
        self.cache = None
        self.head = 0
        self.steps = 0
        self.max_steps = max_steps
        self.status = 'Lista'
        self.tape = dict(enumerate(text))
        self.transitions = {}
        for rule in config['delta']:
            source = rule['params']
            key = (source['initial_state'], source['mem_cache_value'], source['tape_input'])
            self.transitions[key] = rule['output']
        self.update_status()

    def update_status(self):
        # Determina el resultado del estado actual
        key = (self.state, self.cache, self.tape.get(self.head))
        if self.state in self.config['q_states']['final']:
            self.status = 'Aceptada'
        elif key not in self.transitions:
            self.status = 'Rechazada'
        elif self.steps >= self.max_steps:
            self.status = 'Límite alcanzado'

    def step(self):
        # Aplica una transicion disponible
        if self.status != 'Lista':
            return False
        key = (self.state, self.cache, self.tape.get(self.head))
        output = self.transitions[key]
        symbol = output['tape_output']
        # Conserva solo celdas ocupadas
        if symbol is None:
            self.tape.pop(self.head, None)
        else:
            self.tape[self.head] = symbol
        self.state = output['final_state']
        self.cache = output['mem_cache_value']
        self.head += {'L': -1, 'R': 1, 'S': 0}[output['tape_displacement']]
        self.steps += 1
        self.update_status()
        return True

    def bounds(self):
        # Calcula los limites usados de la cinta
        positions = [self.head, *self.tape]
        return min(positions), max(positions)

    def description(self):
        # Construye una descripcion instantanea
        left, right = self.bounds()
        cells = []
        for position in range(left, right + 1):
            if position == self.head:
                cache = 'B' if self.cache is None else self.cache
                cells.append(f'[{self.state}, {cache}]')
            cells.append(self.tape.get(position, 'B'))
        return f'{self.steps:04d}  ' + ' '.join(cells)

    def tape_text(self):
        # Convierte la cinta en texto visible
        if not self.tape:
            return 'B'
        return ''.join(self.tape.get(i, 'B') for i in range(min(self.tape), max(self.tape) + 1))
