# Proyecto 3 Máquina de Turing

En este proyecto hicimos un simulador de máquinas de Turing deterministas de una sola cinta. La idea es poder cargar una máquina, ingresar una cadena y ver cómo se ejecuta paso a paso hasta que se acepte, se rechace o llegue al límite de pasos.

Usamos **Python** para la simulación y **HTML, CSS y JavaScript** para la parte visual. Todo funciona de forma local desde el navegador. La interfaz tiene un tema oscuro con acentos cian y está hecha para que sea fácil seguir los cambios en la cinta, el estado actual y las transiciones.

En la pantalla se puede seleccionar la máquina, escribir una entrada, ver la cinta, revisar la última transición y consultar el historial completo. También se muestran las reglas y la definición formal. La página se adapta a pantallas pequeñas.

En el código dejamos los nombres en inglés y los mensajes de la interfaz en español. Los comentarios son cortos, de una sola línea y sin tildes ni signos de puntuación. No usamos Tkinter, Node, Flask ni bases de datos. Después de instalar PyYAML, tampoco hace falta Internet para ejecutar la aplicación.

## Cómo ejecutar el proyecto

Se necesita **Python 3.10 o superior** y un navegador actualizado. Desde una terminal abierta en la carpeta del proyecto, ejecutamos:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Si ya está instalado PyYAML, solo hace falta correr `python main.py`.

Esto inicia el servidor en `http://127.0.0.1:8000` y abre el navegador. Hay que dejar la terminal abierta mientras se usa la aplicación; para cerrar el servidor se presiona **Ctrl+C**.

Si el puerto 8000 está ocupado, se puede cambiar:

```powershell
python main.py --port 8001
```

Y si no queremos que se abra una pestaña automáticamente:

```powershell
python main.py --no-browser
```

El servidor solo se utiliza en nuestra computadora. Como mantiene una simulación activa, es mejor trabajar con una pestaña a la vez, porque varias pestañas compartirían el mismo estado. Los archivos YAML se leen en memoria y no se suben a servicios externos.

## Cómo usar el simulador

1. Primero elegimos la máquina reconocedora o la alteradora. También podemos subir nuestro propio archivo YAML.
2. Seleccionamos una cadena de ejemplo o escribimos una y presionamos **Preparar**. Para probar la cadena vacía, dejamos el campo sin texto. También funciona con **Enter**.
3. Con **Un paso** avanzamos una transición. Si queremos ver la ejecución automática, usamos **Reproducir**, y con **Pausar** la detenemos sin perder el avance.
4. Con **Simular todas las cadenas** se ejecutan las entradas que vienen en el YAML y se genera el historial de cada una. Esta opción también se puede pausar.
5. **Descargar .txt** guarda el historial con las entradas, los pasos y los resultados. **Reiniciar** vuelve a preparar la misma cadena desde el principio.

En la visualización usamos estados como `q0`, `q1`, etc. El estado actual aparece junto a la cinta y una flecha indica dónde está el cabezal. Para no llenar toda la pantalla, solo mostramos una parte de la cinta alrededor del cabezal, pero en el historial sí queda registrada la región utilizada. Las posiciones se numeran y también pueden ser negativas cuando la cinta crece hacia la izquierda.

## Organización del código

Separamos los archivos según lo que hace cada uno para que fuera más fácil entender el proyecto y hacer pruebas.

| Archivo | Para qué sirve |
|---|---|
| `main.py` | Inicia la aplicación. |
| `lector.py` | Lee los YAML y valida que la configuración sea correcta. |
| `maquina.py` | Maneja la cinta, los estados y las transiciones de cada paso. |
| `servidor.py` | Conecta el simulador en Python con la página del navegador. |
| `web/index.html` | Contiene los controles y las secciones de la interfaz. |
| `web/estilos.css` | Define los colores, el diseño y los ajustes para diferentes pantallas. |
| `web/app.js` | Controla la reproducción, actualiza la vista y descarga el historial. |
| `ejemplos/` | Contiene `espejo.yaml`, `alteradora.yaml` y otros tres archivos para probar la carga. |
| `tests/test_m.py` | Prueba las máquinas, los resultados y los casos especiales. |
| `tests/test_server.py` | Comprueba las solicitudes al servidor local. |

El motor está implementado como una clase porque necesitamos conservar la configuración de la máquina entre un paso y otro. Para el servidor usamos `HTTPServer`, que ya viene con Python. Desde JavaScript hacemos las solicitudes con `fetch` y actualizamos el HTML sin usar frameworks.

### Cómo representamos la cinta

Para guardar la cinta usamos un **diccionario**: cada posición es una clave numérica y el valor es el símbolo de esa celda. Si una posición no existe en el diccionario, significa que está en blanco. Cuando escribimos un blanco, eliminamos esa posición.

También tenemos una memoria auxiliar que guarda un símbolo a la vez. Esta memoria nos sirve para hacer comparaciones o sumas, pero no funciona como una segunda cinta.

Las transiciones están guardadas en otro diccionario y se buscan con `(state, cache, symbol)`, es decir, el estado, la memoria y el símbolo leído. Así no tenemos que revisar todas las reglas en cada paso.

En promedio, buscar una transición o acceder a una posición de la cinta cuesta **O(1)**. Generar una descripción instantánea cuesta **O(k)**, donde `k` es el tamaño de la parte de la cinta que se muestra. Como guardamos todo el historial, el espacio que utiliza depende de la cantidad de texto generado.

Para la reproducción automática usamos `setTimeout`: se espera la respuesta de un paso antes de pedir el siguiente. Cuando ejecutamos todas las cadenas, las procesamos en bloques de 50 pasos para permitir que se pueda pausar.

Además, dejamos un máximo de **10,000 transiciones por cadena**, configurado con `max_steps`. Si se alcanza ese número, el simulador muestra **Límite alcanzado**. Eso no significa que la cadena haya sido rechazada; simplemente detenemos la ejecución para evitar que se quede corriendo indefinidamente.

## Formato de los archivos YAML

Utilizamos los campos del formato solicitado en el enunciado: `q_states`, `alphabet`, `tape_alphabet`, `delta`, `simulation_strings` y los valores de memoria.

Este es un ejemplo sencillo:

```yaml
q_states:
  q_list: [scan, accept]
  initial: scan
  final: accept
alphabet: ['1']
tape_alphabet: ['1', null]
delta:
  - params:
      initial_state: scan
      mem_cache_value: null
      tape_input: '1'
    output:
      final_state: accept
      mem_cache_value: null
      tape_output: '1'
      tape_displacement: S
simulation_strings: ['1']
```

Cada símbolo debe tener un solo carácter. Los nombres de los estados y las cadenas se manejan como texto, así que los valores numéricos funcionan con o sin comillas.

En este formato, `null` significa una celda en blanco o memoria vacía. En la interfaz lo mostramos como `B`, pero **en el YAML no debemos escribir `B` para representar un blanco**.

Los movimientos del cabezal son:

- `L`: moverse a la izquierda.
- `R`: moverse a la derecha.
- `S`: quedarse en la misma posición.

El campo `final` puede contener un estado o una lista de estados finales. El alfabeto de cinta incluye los símbolos de entrada y `null`; si faltan, el lector los agrega. Si usamos símbolos en memoria, también tienen que estar dentro del alfabeto de cinta.

No permitimos dos transiciones con la misma combinación de estado, memoria y símbolo leído. Si la máquina llega a un estado final, acepta la cadena. Si no encuentra una transición válida y todavía no está en un estado final, la rechaza. Las entradas con caracteres fuera del alfabeto se validan antes de ejecutarlas.

## Descripciones instantáneas

Las descripciones instantáneas nos ayudan a ver cómo va cambiando la máquina después de cada transición. Por ejemplo:

```text
0000  [q0, B] a b # b a # a b
0001  X [q1, a] b # b a # a b
```

El número del inicio indica cuántas transiciones se han realizado. La parte `[estado, memoria]` se coloca justo antes del símbolo que está leyendo el cabezal.

En el ejemplo, la máquina empieza en `q0` con la memoria vacía. Después marca la primera `a` con `X`, guarda `a` en memoria y mueve el cabezal hacia la `b`. También registramos la configuración inicial, antes de hacer cualquier transición.

## Máquina reconocedora: espejo con copia

**Archivo:** `ejemplos/espejo.yaml`

Esta máquina reconoce el lenguaje **L = { w#wᴿ#w | w ∈ {a,b,c}* }**. La cadena está dividida en tres partes por `#`: la segunda tiene que ser el inverso de la primera y la tercera tiene que ser igual a la primera. Es un ejemplo de un lenguaje que no es libre de contexto.

Para implementarla usamos **10 estados, 60 transiciones y la memoria auxiliar**.

| Cadena | Longitud | Resultado | Por qué |
|---|---:|---|---|
| `ab#ba#ab` | 8 | Aceptada | `ba` es el inverso de `ab` y el último bloque es igual al primero. |
| `abc#cba#abc` | 11 | Aceptada | El segundo bloque está invertido y el tercero es una copia. |
| `abc#caa#abc` | 11 | Rechazada | `caa` no es el inverso; falla en la segunda letra. |
| `abc#cba#abb` | 11 | Rechazada | `abb` no coincide con el primer bloque en la última letra. |

### Cómo funciona

1. Tomamos una letra del primer bloque, la marcamos con `X` y la guardamos en memoria.
2. Buscamos la última letra que todavía no se ha marcado en el segundo bloque. Como avanzamos de derecha a izquierda, podemos comprobar que sea el inverso. Si coincide, la marcamos con `X`.
3. Luego buscamos la primera letra disponible del tercer bloque, de izquierda a derecha, y comprobamos que coincida con la que guardamos. Si coincide, también la marcamos.
4. Regresamos al inicio para repetir el proceso con la siguiente letra.

Si una comparación falla, no hay una transición que permita continuar y la cadena se rechaza. Cuando terminamos de revisar el primer bloque, verificamos que los otros dos solo tengan marcas `X`.

| Estado | Función |
|---|---|
| `q0` | Busca la siguiente letra del primer bloque sin marcar. |
| `q1` | Recorre el primer bloque con la letra guardada en memoria. |
| `q2` | Avanza por las letras disponibles del segundo bloque. |
| `q3` | Compara la última letra libre del segundo bloque con la memoria. |
| `q4` | Pasa las marcas hasta llegar al segundo `#`. |
| `q5` | Compara la primera letra libre del tercer bloque y limpia la memoria. |
| `q6` | Comprueba que el segundo bloque ya esté marcado. |
| `q7` | Regresa al inicio de la cinta. |
| `q8` | Revisa que el tercer bloque también esté marcado. |
| `q9` | Estado de aceptación. |

El número de pasos crece en el orden de **O(n²)**.

## Máquina alteradora: suma binaria

**Archivo:** `ejemplos/alteradora.yaml`

La segunda máquina recibe una operación de la forma `x+y` y deja en la cinta su resultado en binario. Los valores `x` y `y` están formados por ceros y unos. Para esta máquina usamos **9 estados y 41 transiciones**, además de la memoria auxiliar para guardar temporalmente el bit que estamos sumando.

| Entrada | Operación | Salida | Pasos |
|---|---|---|---:|
| `1011+110` | 11 + 6 | `10001` | 49 |
| `11111+1` | 31 + 1 | `100000` | 31 |
| `1001+101` | 9 + 5 | `1110` | 44 |
| `110+1011` | 6 + 11 | `10001` | 66 |
| `1101+10+1` | dos `+` | Rechazada | 18 |

### Función de los estados

| Estado | Función |
|---|---|
| `q0` | Se mueve hasta el final del segundo número (`y`). |
| `q1` | Borra el último bit de `y` y lo guarda en memoria. Si encuentra `+`, ya terminó ese número. |
| `q2` | Regresa hasta el signo `+` llevando el bit en memoria. |
| `q3` | Salta las columnas procesadas (`o` e `i`) y suma el bit a la siguiente columna de `x`. Si encuentra un blanco, lo toma como 0. |
| `q4` | Maneja el acarreo, cambiando los `1` necesarios por `0` hasta poder escribir un `1`. |
| `q5` | Regresa al final de `y` para tomar el siguiente bit. |
| `q6` | Comprueba que el resultado tenga al menos un bit, para no aceptar `+` sola. |
| `q7` | Convierte las marcas `o` en `0` y las `i` en `1`. |
| `q8` | Estado de aceptación. |

Usamos `o` e `i` para identificar los bits `0` y `1` que ya fueron procesados. De esa forma la máquina sabe qué columnas faltan por sumar.

También validamos que la entrada tenga el formato correcto: rechazamos cadenas sin `+`, con más de un `+` o que sean únicamente `+`. La cantidad de pasos de esta máquina es del orden de **O(n²)**.

## Otros ejemplos para cargar

Además de las dos máquinas principales, agregamos tres archivos para probar la opción **Subir archivo YAML**:

- `ejemplos/unos_pares.yaml`: reconoce cadenas binarias con una cantidad par de unos.
- `ejemplos/duplicador.yaml`: transforma `w` en `w#w`.
- `ejemplos/incremento.yaml`: suma 1 a un número binario.

El lector también tiene algunas consideraciones para poder cargar el ejemplo que viene en el PDF del enunciado:

- Los valores numéricos sin comillas, como `initial: 0` o `- 0101`, se interpretan como texto.
- Si faltan símbolos del alfabeto de entrada o el blanco en `tape_alphabet`, el lector los agrega automáticamente.
- Si una cadena tiene símbolos que no corresponden al alfabeto, no se invalida todo el archivo. Al simular todas las entradas, esa cadena se marca como rechazada sin ejecutarla y se continúa con las demás.

## Pruebas

Para correr las pruebas usamos este comando:

```powershell
python -m unittest discover -s tests -v
```

Incluimos pruebas para los nueve casos que se muestran en la demostración, además de casos más amplios: **21,845 cadenas** de longitud 0 a 7 sobre `{a,b,c,#}`, **961 sumas** con números de hasta 4 bits, todas las copias de longitud 0 a 7 sobre `{a,b}` y **128 incrementos binarios**.

También probamos la carga del YAML del enunciado, las posiciones negativas de la cinta, la cadena vacía, los símbolos inválidos, los límites de pasos y las configuraciones incorrectas.

Por último, las pruebas HTTP revisan que las rutas del servidor funcionen, que podamos cargar YAML, que el ejemplo se mantenga al recargar la página y que los nueve resultados de demostración también funcionen desde el servidor.

## Video
https://youtu.be/sEJgSD5sgLY
