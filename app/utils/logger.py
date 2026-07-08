from rich.console import Console

console = Console()


def info(msg):
    console.print(f"[cyan][INFO][/cyan] {msg}")


def success(msg):
    console.print(f"[green][SUCCESS][/green] {msg}")


def error(msg):
    console.print(f"[red][ERROR][/red] {msg}")