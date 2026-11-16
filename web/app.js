// Busca un elemento por identificador
const get = (id) => document.getElementById(id);
let config;
let current;
let currentInput = '';
let running = false;
let busy = false;
let timer;
let history = [];

const examples = {
  reconocedora: { title: 'w#wᴿ#w', description: 'Acepta tres bloques separados por #: el segundo debe ser el inverso del primero y el tercero una copia. Marca cada letra con X, la guarda en memoria y la busca en los otros dos bloques.' },
  alteradora: { title: 'Suma binaria', description: 'Suma dos binarios columna por columna. Borra el último bit de y, lo guarda en memoria y lo suma a x propagando el acarreo. o e i marcan columnas ya sumadas.' },
};

async function request(path, data) {
  // Solicita datos al servidor local
  const options = data === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  };
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'No se pudo completar la solicitud.');
  return result;
}

function updateControls() {
  // Sincroniza los controles con la ejecucion
  document.querySelectorAll('button').forEach((button) => {
    button.disabled = busy || running;
  });
  get('play').disabled = busy && !running;
  get('play').textContent = running ? 'Ⅱ  Pausar' : '▶  Reproducir';
  get('input').disabled = busy || running;
  get('file').disabled = busy || running;
  if (!running && current?.status !== 'Lista') {
    get('play').disabled = true;
    get('step').disabled = true;
  }
}

function pause() {
  // Detiene la reproduccion pendiente
  running = false;
  clearTimeout(timer);
  updateControls();
}

async function perform(action) {
  // Ejecuta una accion mostrando sus errores
  if (busy) return;
  busy = true;
  get('error').hidden = true;
  updateControls();
  try {
    await action();
  } catch (error) {
    pause();
    get('error').textContent = error.message;
    get('error').hidden = false;
  } finally {
    busy = false;
    updateControls();
  }
}

function firstValid() {
  // Escoge la primera cadena que usa solo el alfabeto
  return config.simulation_strings.find((text) => [...text].every((symbol) => config.alphabet.includes(symbol))) ?? '';
}

function blank(symbol) {
  // Representa el blanco de la cinta
  return symbol === null ? 'B' : symbol;
}

function ruleText(rule) {
  // Formatea una regla de transicion
  const source = rule.params;
  const target = rule.output;
  return `δ([${source.initial_state}, ${blank(source.mem_cache_value)}], ${blank(source.tape_input)}) → ([${target.final_state}, ${blank(target.mem_cache_value)}], ${blank(target.tape_output)}, ${target.tape_displacement})`;
}

function showConfig(name, title) {
  // Dibuja la definicion cargada
  const example = examples[name];
  get('machine-title').textContent = example?.title || title || 'Tu máquina';
  get('machine-description').textContent = example?.description || 'Máquina definida en tu archivo YAML. Las decisiones se toman únicamente con sus transiciones.';
  document.querySelectorAll('[data-example]').forEach((button) => {
    button.classList.toggle('selected', button.dataset.example === name);
    button.setAttribute('aria-pressed', String(button.dataset.example === name));
  });
  get('samples').replaceChildren();
  config.simulation_strings.forEach((text) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'sample';
    button.textContent = text || 'vacía';
    button.addEventListener('click', () => perform(() => prepare(text)));
    get('samples').append(button);
  });
  get('state-list').replaceChildren();
  config.q_states.q_list.forEach((state) => {
    const chip = document.createElement('span');
    chip.className = 'state-chip';
    chip.textContent = state;
    get('state-list').append(chip);
  });
  const fields = [
    ['Estados', config.q_states.q_list.length], ['Inicial → final', `${config.q_states.initial} → ${config.q_states.final.join(', ')}`],
    ['Alfabeto de entrada', config.alphabet.join('  ')], ['Transiciones', config.delta.length],
  ];
  get('definition').replaceChildren();
  fields.forEach(([label, value]) => {
    const row = document.createElement('div');
    const term = document.createElement('dt');
    const detail = document.createElement('dd');
    term.textContent = label;
    detail.textContent = value;
    row.append(term, detail);
    get('definition').append(row);
  });
  get('rules').replaceChildren();
  config.delta.forEach((rule) => {
    const line = document.createElement('div');
    line.className = 'rule';
    line.textContent = ruleText(rule);
    get('rules').append(line);
  });
}

function showFrame(frame) {
  // Dibuja la cinta enfocada en el cabezal
  current = frame;
  get('state-node').textContent = frame.state;
  get('state-node').classList.toggle('final', config.q_states.final.includes(frame.state));
  get('memory').textContent = `memoria: ${blank(frame.cache)}`;
  get('steps').textContent = frame.steps;
  get('position').textContent = frame.head;
  get('status').textContent = frame.status === 'Lista' ? (frame.steps ? 'En proceso' : 'Lista para empezar') : frame.status;
  get('status').dataset.status = frame.status;
  document.querySelectorAll('.state-chip').forEach((chip) => chip.classList.toggle('active', chip.textContent === frame.state));
  const fragment = document.createDocumentFragment();
  frame.cells.forEach(({position, symbol}) => {
    const cell = document.createElement('div');
    const active = position === frame.head;
    cell.className = `cell${active ? ' active' : ''}${symbol === null ? ' blank' : ''}`;
    cell.textContent = blank(symbol);
    cell.setAttribute('aria-label', `Posición ${position}: ${blank(symbol)}${active ? ', cabezal' : ''}`);
    const index = document.createElement('span');
    index.className = 'cell-index';
    index.textContent = position;
    cell.append(index);
    if (active) {
      const pointer = document.createElement('span');
      pointer.className = 'head-pointer';
      pointer.textContent = '▼';
      cell.append(pointer);
    }
    fragment.append(cell);
  });
  get('tape').replaceChildren(fragment);
  get('result').hidden = frame.status === 'Lista';
  get('result-title').textContent = frame.status === 'Límite alcanzado' ? 'Límite de 10,000 pasos · resultado no determinado' : `${frame.status} · cinta final`;
  get('result-output').textContent = frame.output;
}

function addHistory(text, note = false) {
  // Agrega una linea al historial
  history.push(text);
  const row = document.createElement('div');
  row.className = `history-row${note ? ' note' : ''}`;
  if (note) {
    row.textContent = text;
  } else {
    const split = text.indexOf('  ');
    const number = document.createElement('span');
    number.className = 'line-number';
    number.textContent = text.slice(0, split);
    const description = document.createElement('span');
    const parts = text.slice(split + 2).split(/(\[[^\]]*\])/g);
    parts.forEach((part, index) => {
      const span = document.createElement('span');
      span.textContent = part;
      if (index % 2) span.className = 'state-text';
      description.append(span);
    });
    row.append(number, description);
  }
  get('history').append(row);
}

function recordResult() {
  // Registra el resultado de la simulacion
  if (current.status !== 'Lista') addHistory(`${current.status} · Cinta final: ${current.output} · ${current.steps} pasos`, true);
}

async function prepare(text, append = false) {
  // Prepara una entrada desde cero
  const frame = await request('/api/prepare', {text});
  currentInput = text;
  get('input').value = text;
  if (!append) {
    history = [];
    get('history').replaceChildren();
  }
  get('transition').textContent = 'Todavía no se ha aplicado ninguna transición.';
  addHistory(`Entrada: ${text || '(vacía)'}`, true);
  addHistory(frame.description);
  showFrame(frame);
  recordResult();
}

async function advance(count = 1) {
  // Avanza uno o varios pasos
  const previous = current;
  const response = await request('/api/step', {count});
  response.frames.forEach((frame) => addHistory(frame.description));
  if (response.frames.length && count === 1) {
    const symbol = previous.cells.find((cell) => cell.position === previous.head).symbol;
    const rule = config.delta.find((rule) => rule.params.initial_state === previous.state && rule.params.mem_cache_value === previous.cache && rule.params.tape_input === symbol);
    get('transition').textContent = ruleText(rule);
  } else if (count > 1) {
    get('transition').textContent = 'Procesamiento de todas las cadenas · historial completo abajo.';
  }
  showFrame(response.current);
  if (response.frames.length) recordResult();
  get('history').scrollTop = get('history').scrollHeight;
}

async function tick() {
  // Programa el siguiente paso animado
  if (!running) return;
  await perform(() => advance());
  if (running && current.status === 'Lista') timer = setTimeout(tick, Number(get('speed').value));
  else pause();
}

get('play').addEventListener('click', () => {
  // Alterna entre reproducir y pausar
  if (running) return pause();
  running = true;
  tick();
});
get('step').addEventListener('click', () => {
  // Aplica una sola transicion manual
  perform(() => advance());
});
get('reset').addEventListener('click', () => {
  // Vuelve a cargar la cadena actual
  perform(() => prepare(currentInput));
});
get('input-form').addEventListener('submit', (event) => {
  // Prepara la cadena escrita por el usuario
  event.preventDefault();
  perform(() => prepare(get('input').value));
});
get('speed').addEventListener('input', () => {
  // Muestra la velocidad elegida en milisegundos
  get('speed-value').textContent = `${get('speed').value} ms`;
});
document.querySelectorAll('[data-example]').forEach((button) => {
  button.addEventListener('click', () => perform(async () => {
    // Cambia a la maquina de ejemplo pulsada
    config = await request('/api/example', {name: button.dataset.example});
    showConfig(button.dataset.example);
    await prepare(firstValid());
  }));
});
get('upload-button').addEventListener('click', () => {
  // Abre el selector de archivos oculto
  get('file').click();
});
get('file').addEventListener('change', () => perform(async () => {
  // Valida y carga el YAML elegido
  const file = get('file').files[0];
  if (!file) return;
  if (file.size > 1_000_000) throw new Error('El archivo debe ser menor a 1 MB.');
  config = await request('/api/load', {text: await file.text()});
  showConfig(null, file.name);
  await prepare(firstValid());
  get('file').value = '';
}));
get('batch').addEventListener('click', () => perform(async () => {
  // Simula en cadena todas las entradas del archivo
  running = true;
  updateControls();
  history = [];
  get('history').replaceChildren();
  if (!config.simulation_strings.length) addHistory('El archivo no contiene cadenas para simular', true);
  for (const text of config.simulation_strings) {
    if (!running) break;
    try {
      await prepare(text, true);
    } catch (error) {
      addHistory(`Entrada: ${text || '(vacía)'} · Rechazada sin simular: ${error.message}`, true);
      continue;
    }
    while (running && current.status === 'Lista') await advance(50);
  }
  pause();
}));
get('export').addEventListener('click', () => {
  // Descarga el historial como archivo de texto
  const url = URL.createObjectURL(new Blob([history.join('\n')], {type: 'text/plain;charset=utf-8'}));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'proyecto3-history.txt';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

perform(async () => {
  // Restaura la maquina activa al abrir la pagina
  const saved = await request('/api/config');
  config = saved.config;
  showConfig(saved.example);
  await prepare(firstValid());
});
