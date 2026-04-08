import argparse
import sys
import threading
import time

from providers.ollama_provider import OllamaProvider
from utils.config import Config
from utils.history import HistoryManager
from utils.registry import ProviderRegistry

COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "cyan": "\033[96m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "magenta": "\033[95m",
}

COMMANDS = {
    "/exit": "salir del chat",
    "/clear": "limpiar historial de la sesión actual",
    "/history": "mostrar sesiones guardadas",
    "/model": "cambiar modelo (ej: /model gpt-4o)",
    "/provider": "cambiar provider (ej: /provider ollama)",
    "/system": "editar system prompt",
    "/models": "listar modelos del provider actual",
    "/pull <model>": "descargar modelo en Ollama",
    "/help": "mostrar esta ayuda",
}


def _spinner(stop_event: threading.Event) -> None:
    frames = ["   ", "·  ", "·· ", "···"]
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r\033[2K  {COLORS['dim']}{frames[i % len(frames)]}{COLORS['reset']}")
        sys.stdout.flush()
        time.sleep(0.35)
        i += 1
    sys.stdout.write("\r\033[2K")
    sys.stdout.flush()


def c(text: str, *colors: str) -> str:
    codes = "".join(COLORS[col] for col in colors)
    return f"{codes}{text}{COLORS['reset']}"


def print_banner():
    print(c("\n╔══════════════════════════════════════╗", "cyan"))
    print(c("║      multi-llm-chatbot-platform      ║", "cyan", "bold"))
    print(c("╚══════════════════════════════════════╝", "cyan"))
    print(c("  providers: anthropic · openai · huggingface · ollama\n", "dim"))


def select_provider_interactive(registry: ProviderRegistry) -> str:
    options = registry.available()
    print(c("Seleccioná un provider:", "bold"))
    for i, p in enumerate(options, 1):
        print(f"  {c(str(i), 'cyan')}. {p}")
    while True:
        choice = input(c("\n> ", "dim")).strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        if choice in options:
            return choice
        print(c("Opción inválida.", "red"))


def select_model_interactive(provider) -> str:
    models = provider.list_models()
    if not models:
        print(c("No hay modelos disponibles. ¿Está corriendo `ollama serve`?", "red"))
        sys.exit(1)
    print(c(f"\nModelos disponibles en {provider.name}:", "bold"))
    for i, m in enumerate(models, 1):
        print(f"  {c(str(i), 'cyan')}. {m}")
    while True:
        choice = input(c("\n> ", "dim")).strip()
        if choice.isdigit() and 1 <= int(choice) <= len(models):
            return models[int(choice) - 1]
        if choice in models:
            return choice
        print(c("Opción inválida.", "red"))


def print_help():
    print(c("\nComandos disponibles:", "bold"))
    for cmd, desc in COMMANDS.items():
        print(f"  {c(cmd, 'cyan'):<25} {desc}")
    print()


def chat_loop(provider, model: str, config: Config, history: HistoryManager, registry: ProviderRegistry):
    system_prompt = config.default_system_prompt
    print(c(f"\n[{provider.name}] modelo: {model}", "dim"))
    print(c(f"System prompt: {system_prompt[:60]}...\n", "dim"))
    print(c("Escribí tu mensaje. /help para comandos.\n", "dim"))

    while True:
        try:
            user_input = input(c("Vos: ", "green", "bold")).strip()
        except (EOFError, KeyboardInterrupt):
            print(c("\n\nSaliendo...", "dim"))
            break

        if not user_input:
            continue

        if user_input == "/exit":
            break

        if user_input == "/help":
            print_help()
            continue

        if user_input == "/clear":
            history.clear()
            print(c("Historial limpiado.\n", "yellow"))
            continue

        if user_input == "/history":
            sessions = history.list_sessions()
            if not sessions:
                print(c("Sin sesiones previas.\n", "dim"))
            else:
                print(c("Sesiones guardadas:", "bold"))
                for s in sessions[-10:]:
                    print(f"  {c(s, 'cyan')}")
            continue

        if user_input == "/models":
            for m in provider.list_models():
                marker = c("*", "green") if m == model else " "
                print(f"  {marker} {m}")
            print()
            continue

        if user_input == "/model":
            model = select_model_interactive(provider)
            print(c(f"Modelo cambiado a: {model}\n", "yellow"))
            continue

        if user_input.startswith("/model "):
            model = user_input.split(" ", 1)[1].strip()
            print(c(f"Modelo cambiado a: {model}\n", "yellow"))
            continue

        if user_input == "/provider":
            new_name = select_provider_interactive(registry)
            provider = registry.get(new_name)
            model = select_model_interactive(provider)
            print(c(f"Provider cambiado a: {provider.name}, modelo: {model}\n", "yellow"))
            continue

        if user_input.startswith("/provider "):
            new_name = user_input.split(" ", 1)[1].strip()
            try:
                provider = registry.get(new_name)
                model = select_model_interactive(provider)
                print(c(f"Provider cambiado a: {provider.name}, modelo: {model}\n", "yellow"))
            except ValueError as e:
                print(c(f"Error: {e}\n", "red"))
            continue

        if user_input == "/system":
            print(c(f"System prompt actual:\n{system_prompt}\n", "dim"))
            print(c("Nuevo system prompt (Enter para conservar):", "bold"))
            new_sys = input("> ").strip()
            if new_sys:
                system_prompt = new_sys
                print(c("System prompt actualizado.\n", "yellow"))
            continue

        if user_input.startswith("/pull "):
            model_to_pull = user_input.split(" ", 1)[1].strip()
            if isinstance(provider, OllamaProvider):
                provider.pull_model(model_to_pull)
            else:
                print(c("/pull solo funciona con el provider ollama.", "red"))
            continue

        history.add("user", user_input)

        print()
        stop_event = threading.Event()
        spinner_thread = threading.Thread(target=_spinner, args=(stop_event,), daemon=True)
        spinner_thread.start()

        try:
            response = provider.chat(
                messages=history.messages[:-1] + [history.messages[-1]],
                model=model,
                system_prompt=system_prompt,
            )
        except Exception as e:
            stop_event.set()
            spinner_thread.join()
            print(c(f"Error: {e}\n", "red"))
            history.messages.pop()
            continue

        stop_event.set()
        spinner_thread.join()
        print(c(f"IA ({model}): ", "magenta", "bold") + response)
        print()
        history.add("assistant", response)


def main():
    parser = argparse.ArgumentParser(description="MultiLLM Chatbot CLI")
    parser.add_argument("--provider", choices=["anthropic", "openai", "ollama", "huggingface"])
    parser.add_argument("--model", help="Modelo a usar")
    parser.add_argument("--pull", metavar="MODEL", help="Descargar modelo de Ollama antes de chatear")
    parser.add_argument("--history", action="store_true", help="Listar sesiones previas")
    parser.add_argument("--session", help="Retomar sesión por ID")
    parser.add_argument("--env", default=".env", help="Ruta al archivo .env")
    args = parser.parse_args()

    config = Config.from_env(args.env)
    registry = ProviderRegistry(config)
    history = HistoryManager(config.history_file)

    print_banner()

    if args.history:
        sessions = history.list_sessions()
        if not sessions:
            print(c("Sin sesiones guardadas.", "dim"))
        else:
            print(c("Sesiones guardadas:", "bold"))
            for s in sessions:
                n = len(history._data[s]["messages"])
                print(f"  {c(s, 'cyan')}  ({n} mensajes)")
        return

    if args.session:
        history.load_session(args.session)
        print(c(f"Sesión {args.session} cargada ({len(history)} mensajes).\n", "yellow"))

    provider_name = args.provider or select_provider_interactive(registry)
    provider = registry.get(provider_name)

    if args.pull:
        if isinstance(provider, OllamaProvider):
            provider.pull_model(args.pull)
        else:
            print(c("--pull solo funciona con --provider ollama", "red"))
            sys.exit(1)

    model = args.model or select_model_interactive(provider)
    chat_loop(provider, model, config, history, registry)


if __name__ == "__main__":
    main()