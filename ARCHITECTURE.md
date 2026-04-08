# Arquitectura y documentación técnica

## Descripción general

`multi-llm-chatbot-platform` es un chatbot conversacional de línea de comandos que permite interactuar con múltiples proveedores de modelos de lenguaje (LLMs) desde una única interfaz. El usuario puede elegir el provider y el modelo al iniciar, y cambiarlos en caliente durante la conversación sin reiniciar el proceso. El historial de cada sesión se persiste automáticamente en un archivo JSON.

---

## Estructura del proyecto

```
multi-llm-chatbot-platform/
├── main.py                      # Entrypoint CLI, loop de chat, comandos
├── providers/
│   ├── __init__.py              # Exporta todas las clases de providers
│   ├── base.py                  # Contrato abstracto que deben cumplir todos los providers
│   ├── anthropic_provider.py    # Provider para la API de Anthropic (Claude)
│   ├── openai_provider.py       # Provider para la API de OpenAI (GPT)
│   ├── ollama_provider.py       # Provider para modelos locales via Ollama
│   └── huggingface_provider.py  # Provider para HuggingFace Inference API
├── utils/
│   ├── config.py                # Carga y expone la configuración desde .env
│   ├── history.py               # Gestión y persistencia del historial de conversación
│   └── registry.py              # Fábrica de providers con caché
├── .env                         # Variables de entorno (API keys, config)
├── .env.example                 # Plantilla de configuración
├── requirements.txt             # Dependencias Python
└── README.md                    # Guía de uso
```

---

## Flujo de ejecución

```
python main.py
       │
       ▼
   main()
       │
       ├─ Config.from_env()          → lee .env, construye Config
       ├─ ProviderRegistry(config)   → fábrica de providers lista para usar
       ├─ HistoryManager(path)       → carga historial previo del archivo JSON
       │
       ├─ [--history]  → lista sesiones y sale
       ├─ [--session]  → carga sesión previa en memoria
       │
       ├─ select_provider_interactive()  → menú numerado por consola
       ├─ ProviderRegistry.get(name)     → instancia el provider con su API key
       ├─ [--pull]     → descarga modelo en Ollama y continúa
       ├─ select_model_interactive()     → menú numerado por consola
       │
       └─ chat_loop(provider, model, config, history, registry)
               │
               └─ bucle while True
                       │
                       ├─ input("Vos: ")
                       │
                       ├─ /comando  → acción local, no se envía al modelo
                       │
                       └─ mensaje normal:
                               ├─ history.add("user", texto)
                               ├─ spinner animado en hilo separado
                               ├─ provider.chat(messages, model, system_prompt)
                               ├─ spinner.stop()
                               ├─ print respuesta
                               └─ history.add("assistant", respuesta)
```

### Ciclo de un mensaje

1. El usuario escribe un mensaje y pulsa Enter.
2. El mensaje se agrega al historial en memoria (`history.add("user", ...)`).
3. Se lanza un hilo de fondo con el spinner animado (`···`).
4. Se llama a `provider.chat()` pasando **todo el historial acumulado** más el system prompt. Esto es lo que da memoria conversacional al modelo.
5. Al recibir la respuesta, el spinner se detiene.
6. Se imprime la respuesta y se guarda en el historial (`history.add("assistant", ...)`).
7. El historial se persiste automáticamente en `history.json` tras cada mensaje.

---

## Archivos y componentes

---

### `main.py`

Entrypoint del programa. Contiene la lógica de presentación (CLI), el loop principal del chat y el manejo de todos los comandos internos.

#### Constantes

| Nombre | Descripción |
|---|---|
| `COLORS` | Diccionario de códigos ANSI para colorear la salida en terminal |
| `COMMANDS` | Diccionario de comandos disponibles en el chat y su descripción |

#### Funciones

**`_spinner(stop_event)`**
Corre en un hilo separado (daemon). Muestra una animación de puntos (`·`, `··`, `···`) en la línea actual mientras el modelo está procesando. Cuando `stop_event` se activa, borra la línea y termina. Usa `\r\033[2K` para sobreescribir en lugar de imprimir nuevas líneas.

**`c(text, *colors)`**
Función de utilidad para envolver texto con códigos de color ANSI. Recibe el texto y uno o más nombres de color definidos en `COLORS`. Retorna el texto con los códigos de apertura y cierre (`reset`) incluidos.

**`print_banner()`**
Imprime el banner de bienvenida con el nombre del proyecto y los providers soportados usando caracteres Unicode de caja.

**`select_provider_interactive(registry)`**
Muestra un menú numerado con los providers disponibles obtenidos de `registry.available()`. Acepta tanto el número como el nombre del provider. Repite hasta recibir una entrada válida. Retorna el nombre del provider elegido.

**`select_model_interactive(provider)`**
Muestra un menú numerado con los modelos del provider actual (llamando a `provider.list_models()`). Acepta número o nombre exacto. Si no hay modelos disponibles (e.g. Ollama no está corriendo), imprime un error y sale del proceso. Retorna el nombre del modelo elegido.

**`print_help()`**
Imprime la lista de comandos disponibles dentro del chat con su descripción, usando el diccionario `COMMANDS`.

**`chat_loop(provider, model, config, history, registry)`**
Bucle principal de conversación. Gestiona el estado mutable de `provider` y `model` (pueden cambiar en caliente) y procesa cada línea de entrada del usuario:

- Si comienza por `/`, se ejecuta el comando correspondiente y se hace `continue` (no se envía al modelo).
- Si es texto normal, se agrega al historial, se lanza el spinner, se llama al provider y se guarda la respuesta.
- Captura `EOFError` y `KeyboardInterrupt` (Ctrl+C / Ctrl+D) para salir limpiamente.

Comandos manejados:

| Comando | Acción |
|---|---|
| `/exit` | Sale del bucle |
| `/help` | Llama a `print_help()` |
| `/clear` | Llama a `history.clear()` |
| `/history` | Lista las últimas 10 sesiones guardadas |
| `/models` | Lista modelos del provider actual, marcando el activo con `*` |
| `/model` | Llama a `select_model_interactive()` para elegir modelo con menú |
| `/model <nombre>` | Cambia el modelo directamente sin menú |
| `/provider` | Llama a `select_provider_interactive()` y luego `select_model_interactive()` |
| `/provider <nombre>` | Cambia el provider directamente y pide modelo con menú |
| `/system` | Muestra el system prompt actual y permite editarlo |
| `/pull <modelo>` | Llama a `provider.pull_model()` si el provider es Ollama |

**`main()`**
Función de entrada. Parsea los argumentos de línea de comandos con `argparse`, inicializa `Config`, `ProviderRegistry` e `HistoryManager`, y orquesta el flujo de inicio antes de entrar al `chat_loop`.

Argumentos CLI:

| Argumento | Descripción |
|---|---|
| `--provider` | Elige provider directamente sin menú |
| `--model` | Elige modelo directamente sin menú |
| `--pull <model>` | Descarga un modelo de Ollama antes de iniciar el chat |
| `--history` | Lista sesiones guardadas y sale |
| `--session <id>` | Carga una sesión previa por su ID (timestamp) |
| `--env <path>` | Ruta alternativa al archivo `.env` (default: `.env`) |

---

### `providers/base.py`

Define el contrato que deben implementar todos los providers.

#### `Message`
Dataclass con dos campos:
- `role: str` — puede ser `"user"` o `"assistant"`
- `content: str` — el texto del mensaje

Es la unidad de intercambio de mensajes entre el historial y los providers.

#### `BaseLLMProvider` (ABC)
Clase base abstracta. Define la interfaz que todos los providers deben respetar.

- `name: str` — identificador del provider (e.g. `"ollama"`)
- `available_models: list[str]` — lista estática de modelos conocidos
- `chat(messages, model, system_prompt, temperature) -> str` — método abstracto que envía la conversación al modelo y retorna la respuesta como string
- `list_models() -> list[str]` — método abstracto que retorna los modelos disponibles
- `__repr__()` — representación legible del objeto

---

### `providers/anthropic_provider.py`

#### `AnthropicProvider`
Implementa `BaseLLMProvider` usando el SDK oficial de Anthropic.

- **`__init__(api_key)`** — instancia `anthropic.Anthropic` con la API key provista o la variable de entorno `ANTHROPIC_API_KEY`.
- **`chat(messages, model, system_prompt, temperature)`** — llama a `client.messages.create()`. El system prompt se pasa como parámetro separado `system=` (parte del protocolo de Anthropic). Retorna el texto de `response.content[0].text`. Límite de tokens de salida: 2048.
- **`list_models()`** — retorna la lista estática `available_models`.

Modelos disponibles: `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`.

---

### `providers/openai_provider.py`

#### `OpenAIProvider`
Implementa `BaseLLMProvider` usando el SDK oficial de OpenAI.

- **`__init__(api_key)`** — instancia `OpenAI` con la API key.
- **`chat(messages, model, system_prompt, temperature)`** — el system prompt se inserta como primer mensaje con `role: "system"` (protocolo de OpenAI). Llama a `client.chat.completions.create()`. Retorna `response.choices[0].message.content`.
- **`list_models()`** — retorna la lista estática `available_models`.

Modelos disponibles: `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`.

---

### `providers/ollama_provider.py`

#### `OllamaProvider`
Implementa `BaseLLMProvider` comunicándose con una instancia local de Ollama via HTTP.

- **`__init__(base_url)`** — guarda la URL base del servidor Ollama (default: `http://localhost:11434`).
- **`chat(messages, model, system_prompt, temperature)`** — hace un POST a `/api/chat` con el historial de mensajes, opciones de temperatura y `stream: false`. El system prompt se pasa como campo `system` en el payload. Retorna `response["message"]["content"]`. Timeout: 120 segundos.
- **`list_models()`** — hace un GET a `/api/tags` para obtener los modelos **realmente instalados** en el Ollama local. Si Ollama no está corriendo (`ConnectError`), retorna lista vacía.
- **`pull_model(model)`** — hace un POST streaming a `/api/pull` e imprime el progreso en tiempo real línea a línea. Permite descargar modelos del registry de Ollama.

---

### `providers/huggingface_provider.py`

#### `HuggingFaceProvider`
Implementa `BaseLLMProvider` usando la HuggingFace Inference API (modelos hospedados, no locales).

- **`__init__(api_key)`** — guarda la API key y la URL base de la API de inferencia.
- **`chat(messages, model, system_prompt, temperature)`** — construye el prompt en formato ChatML (`<|system|>`, `<|user|>`, `<|assistant|>`) concatenando todos los mensajes del historial. Hace un POST HTTP con `httpx` al endpoint del modelo. Retorna el texto generado de `data[0]["generated_text"]`. Parámetros: `max_new_tokens=512`, `return_full_text=False`.
- **`list_models()`** — retorna la lista estática `available_models`.

Modelos disponibles: `mistralai/Mistral-7B-Instruct-v0.3`, `microsoft/Phi-3-mini-4k-instruct`, `HuggingFaceH4/zephyr-7b-beta`, `tiiuae/falcon-7b-instruct`.

---

### `providers/__init__.py`

Re-exporta todas las clases de providers para que puedan importarse directamente desde el paquete `providers`:

```python
from providers import AnthropicProvider, OpenAIProvider, ...
```

---

### `utils/config.py`

#### `_load_env(path)`
Función standalone que parsea un archivo `.env` manualmente (sin dependencia de `python-dotenv`). Lee el archivo línea a línea, ignora comentarios y líneas vacías, y usa `os.environ.setdefault()` para no sobreescribir variables ya definidas en el entorno del sistema.

#### `Config`
Dataclass que centraliza toda la configuración de la aplicación. Cada campo lee su valor desde una variable de entorno con un valor por defecto.

| Campo | Variable de entorno | Default |
|---|---|---|
| `anthropic_api_key` | `ANTHROPIC_API_KEY` | `""` |
| `openai_api_key` | `OPENAI_API_KEY` | `""` |
| `huggingface_api_key` | `HUGGINGFACE_API_KEY` | `""` |
| `ollama_base_url` | `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `default_system_prompt` | `DEFAULT_SYSTEM_PROMPT` | `"Sos un asistente técnico..."` |
| `history_file` | `HISTORY_FILE` | `history.json` |

- **`from_env(env_file)`** — método de clase que primero llama a `_load_env()` para cargar el archivo `.env` al entorno del proceso, y luego instancia `Config` leyendo las variables ya disponibles en `os.environ`.

---

### `utils/history.py`

#### `HistoryManager`
Gestiona el historial de mensajes de la sesión en memoria y lo persiste en un archivo JSON. El archivo puede contener múltiples sesiones identificadas por su timestamp de inicio.

Estructura del archivo `history.json`:
```json
{
  "20240101_120000": {
    "timestamp": "20240101_120000",
    "messages": [
      {"role": "user", "content": "Hola"},
      {"role": "assistant", "content": "Hola, ¿en qué puedo ayudarte?"}
    ]
  }
}
```

- **`__init__(path)`** — asigna un `session_id` con el timestamp actual, inicializa `messages = []` y carga el archivo JSON existente en `_data`.
- **`_load()`** — lee y parsea `history.json`. Si no existe, retorna dict vacío.
- **`_save()`** — serializa `self.messages` y lo guarda bajo `self.session_id` en `_data`, sobreescribiendo el archivo completo.
- **`add(role, content)`** — crea un `Message`, lo agrega a `self.messages` y llama a `_save()`. Se llama automáticamente después de cada turno del usuario y de la IA.
- **`clear()`** — vacía `self.messages`, elimina la sesión actual de `_data`, y actualiza el archivo. Si no quedan otras sesiones, elimina el archivo `history.json`.
- **`list_sessions()`** — retorna la lista de IDs (timestamps) de todas las sesiones guardadas.
- **`load_session(session_id)`** — carga los mensajes de una sesión previa en memoria y adopta ese `session_id` como el actual (los nuevos mensajes se agregarán a esa sesión).
- **`__len__()`** — retorna la cantidad de mensajes en la sesión actual.

---

### `utils/registry.py`

#### `ProviderRegistry`
Fábrica centralizada de providers con caché. Permite obtener instancias de providers por nombre sin que el resto del código conozca los detalles de construcción.

- **`__init__(config)`** — guarda la config y inicializa un dict vacío `_cache`.
- **`get(name)`** — retorna el provider del caché si ya fue instanciado. Si no, llama a `_build()`, lo guarda en caché y lo retorna. Esto garantiza que cada provider se instancia una sola vez (patrón singleton por nombre).
- **`_build(name)`** — usa `match/case` para instanciar el provider correcto pasándole la API key o URL correspondiente de la config. Lanza `ValueError` si el nombre no existe.
- **`available()`** — retorna la lista estática de nombres de providers soportados: `["anthropic", "openai", "ollama", "huggingface"]`.

---

## Diagrama de dependencias

```
main.py
  ├── providers/
  │     ├── __init__.py
  │     ├── base.py          ← Message, BaseLLMProvider
  │     ├── anthropic_provider.py  (usa: anthropic SDK)
  │     ├── openai_provider.py     (usa: openai SDK)
  │     ├── ollama_provider.py     (usa: httpx)
  │     └── huggingface_provider.py (usa: httpx)
  └── utils/
        ├── config.py        ← Config, _load_env
        ├── history.py       ← HistoryManager  (usa: providers/base.Message)
        └── registry.py      ← ProviderRegistry (usa: providers/*, utils/config)
```

---

## Decisiones de diseño

**Sin streaming de respuesta.** Todos los providers usan `stream=False` (o equivalente). La respuesta llega completa y se muestra de una vez. El spinner animado da feedback visual mientras se espera.

**Historial completo en cada llamada.** En cada turno se envía todo `history.messages` al modelo. Esto da memoria conversacional real pero aumenta el costo de tokens con conversaciones largas.

**Providers lazy con caché.** `ProviderRegistry` no instancia nada hasta que se pide por primera vez, y guarda la instancia para reutilizarla. Cambiar de provider durante el chat no destruye las instancias anteriores.

**Sin python-dotenv.** La carga del `.env` está implementada manualmente en `_load_env()` para no agregar dependencias innecesarias para una funcionalidad simple.

**Cambio de provider en caliente.** El `chat_loop` recibe `provider` y `model` como variables locales mutables, lo que permite reasignarlas con `/provider` o `/model` sin reiniciar el proceso ni perder el historial.
