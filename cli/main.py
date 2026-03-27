import argparse
import logging
import os

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import InvalidResponse, Prompt
from rich.syntax import Syntax
from rich.text import Text

from rlm.core.rllm import RLM

logger = logging.getLogger(__name__)


class FilePrompt(Prompt):
    validate_error_message = (
        "[italic red]Error! File doesn't exist or invalid path[/italic red]"
    )

    def process_response(self, value: str) -> str:
        # Limpia comillas si el usuario arrastró el archivo a la terminal
        path = value.strip().replace('"', "").replace("'", "")

        if not os.path.exists(path):
            raise InvalidResponse(self.validate_error_message)
        return path


def parse_args():
    """Parse command line arguments

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description="RLM - Recursive Language Model")
    parser.add_argument(
        "--no-guards", action="store_true", help="Disable depth and iteration guards"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Prompt to pass the ai",
    )
    parser.add_argument("--file", type=str, help="File to analyze")
    parser.add_argument(
        "--max-depth", type=int, default=5, help="Maximum recursion depth"
    )
    parser.add_argument("--max-iter", type=int, default=10, help="Maximum iterations")
    parser.add_argument(
        "--repl-only",
        action="store_true",
        help="Start REPL mode without AI initialization",
    )

    return parser.parse_args()


def load_file_contents(filepath: str) -> str:
    """Load file contents

    Args:
        filepath: Path to the file to load

    Returns:
        str: File contents
    """
    with open(filepath, "r") as f:
        return f.read()


lua_queries = 0


def query_callback(query, res, output):

    console = Console()
    global lua_queries
    lua_queries += 1

    result = "\n".join(output[:10]) + "\n ... truncated" if output else res

    console.print(
        Panel(
            Group(
                Syntax(query, "lua"),
                Text().append("\nOutput:\n", style="bold"),
                Text(result),
            ),
            title=f"Query: {lua_queries}",
        )
    )


def main():
    """Main entry point for RLM"""
    args = parse_args()
    console = Console()
    if args.repl_only:
        contents = ""
        model = RLM(
            initial_prompt=args.prompt,
            initial_context=contents,
            max_depth=args.max_depth,
            disable_guards=args.no_guards,
            quiet=True,
            init_ai=False,
        )
        print("REPL mode - Lua runtime initialized (AI disabled)")
        print("Available: print(), REGEX_FIND, REGEX_FIND_ALL, REGEX_COUNT")
        print("Variables: prompt, context, current_depth, max_depth")
        print("Type 'quit', 'exit', or 'q' to exit, or press Ctrl+D\n")

        while True:
            try:
                code = input("> ")
                if code.strip() in ("quit", "exit", "q"):
                    break

                model.runtime.core.captured_output.clear()
                result = model.runtime.execute_query(code)

                if model.runtime.captured_output:
                    for line in model.runtime.captured_output:
                        print(line)

                if result is not None:
                    print(result)
            except EOFError:
                print("\nExiting REPL...")
                break
            except Exception as e:
                print(f"Error: {type(e).__name__}: {e}")
    else:
        prompt = ""
        context = ""
        if args.prompt == "" or args.prompt is None:
            console.print("Prompt:", style="bold cyan")
            prompt = console.input("[bold green]❯ [/bold green]")
        else:
            prompt = args.prompt

        if args.file == "" or args.file is None:
            console.print("Context File path (Absolute pls)", style="bold deep_pink1")
            context = FilePrompt.ask("[bold green]❯ [/bold green]", console=console)
        else:
            context = args.file
        contents = ""
        with open(context, "r") as f:
            contents = f.read()

        model = RLM(
            initial_prompt=prompt,
            initial_context=contents,
            max_depth=args.max_depth,
            disable_guards=args.no_guards,
            quiet=True,
            query_callback=query_callback,
        )
        model.run(max_iter=args.max_iter)

        markdown = Markdown(model._final_message)
        console.print(markdown)


if __name__ == "__main__":
    main()
