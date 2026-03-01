from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template


def load_template(template_path: Path) -> Template:
    env = Environment(loader=FileSystemLoader(template_path.parent))
    template = env.get_template(template_path.name)
    return template
