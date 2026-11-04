

from pathlib import Path


def load_prompt(prompt_path: str) -> str:
    prompt_path = Path(__file__).parents[2] / "prompts" /f"{prompt_path}.prompt"
    return prompt_path.read_text(encoding="utf-8")
