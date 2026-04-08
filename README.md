# multi-llm-chatbot-platform

Chatbot CLI multi-proveedor con soporte para **Anthropic**, **OpenAI**, **HuggingFace** y **Ollama** (modelos locales). Permite cambiar de provider y modelo en caliente, sin reiniciar.

## Providers soportados

| Provider | Requiere API key | Modelos de ejemplo |
|---|---|---|
| `anthropic` | Sí | claude-sonnet-4-6, claude-haiku-4-5 |
| `openai` | Sí | gpt-4o, gpt-4o-mini, o3-mini |
| `huggingface` | Sí | mistralai/Mistral-7B-Instruct-v0.3 |
| `ollama` | No (local) | llama3.2, mistral, phi3, qwen2.5 |

## Instalación

```bash
git clone https://github.com/luisforni/multi-llm-chatbot-platform.git
cd multi-llm-chatbot-platform

# Crear entorno virtual
python -m venv .venv

# Activar (Linux/Mac)
source .venv/bin/activate

# Activar (Windows)
.venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env   # completar con tus API keys
```

## Configuración (.env)

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
HUGGINGFACE_API_KEY=hf_...
OLLAMA_BASE_URL=http://localhost:11434

DEFAULT_SYSTEM_PROMPT=Sos un asistente técnico experto. Respondé en español, de forma concisa y precisa.
HISTORY_FILE=history.json
```

Solo es necesaria la API key del provider que vayas a usar. Ollama no requiere ninguna.

## Uso

```bash
# Modo interactivo: elige provider y modelo con menú
python main.py

# Forzar provider y modelo directamente
python main.py --provider anthropic --model claude-sonnet-4-6
python main.py --provider openai --model gpt-4o-mini
python main.py --provider ollama --model llama3.2

# Descargar un modelo de Ollama antes de iniciar el chat
python main.py --provider ollama --pull llama3.2

# Ver sesiones previas
python main.py --history

# Retomar una sesión guardada
python main.py --session 20240101_120000
```

## Comandos dentro del chat

| Comando | Descripción |
|---|---|
| `/model` | Elegir modelo con menú interactivo |
| `/model gpt-4o` | Cambiar modelo directamente |
| `/provider` | Elegir provider y modelo con menú interactivo |
| `/provider ollama` | Cambiar provider directamente (pide modelo) |
| `/models` | Listar modelos disponibles del provider actual |
| `/system` | Ver y editar el system prompt |
| `/history` | Ver sesiones guardadas |
| `/clear` | Limpiar historial de la sesión actual |
| `/pull llama3.2` | Descargar modelo en Ollama |
| `/help` | Mostrar ayuda |
| `/exit` | Salir |

## Ollama — modelos locales (sin API key)

```bash
# Instalar Ollama en Windows
winget install Ollama.Ollama

# Instalar Ollama en Linux/Mac
curl -fsSL https://ollama.ai/install.sh | sh

# Descargar modelos
ollama pull llama3.2    # 2GB — uso general
ollama pull mistral     # 4GB — muy bueno en código
ollama pull phi3        # 2GB — rápido y liviano
ollama pull qwen2.5     # 4.7GB — multilingüe

# Iniciar el servidor (necesario antes de usar el chatbot)
ollama serve

# Luego iniciar el chatbot
python main.py --provider ollama
```

## Arquitectura

```
multi-llm-chatbot-platform/
├── main.py                      # CLI entrypoint y loop de chat
├── providers/
│   ├── __init__.py
│   ├── base.py                  # Interfaz abstracta BaseLLMProvider
│   ├── anthropic_provider.py
│   ├── openai_provider.py
│   ├── ollama_provider.py       # Local via Ollama
│   └── huggingface_provider.py  # HF Inference API
├── utils/
│   ├── config.py                # Configuración desde .env
│   ├── history.py               # Historial persistente en JSON
│   └── registry.py              # Provider factory
├── .env.example
├── requirements.txt
└── README.md
```

## Agregar un nuevo provider

1. Crear `providers/mi_provider.py`:

```python
from .base import BaseLLMProvider

class MiProvider(BaseLLMProvider):
    name = "mi_provider"

    def chat(self, messages, model, system_prompt="", temperature=0.7) -> str:
        # tu implementación
        ...

    def list_models(self) -> list[str]:
        return ["modelo-1", "modelo-2"]
```

2. Exportarlo en `providers/__init__.py`:

```python
from providers.mi_provider import MiProvider
```

3. Registrarlo en `utils/registry.py` dentro del método `_build` y en `available()`.
