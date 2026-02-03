"""
Unified prompt template (REFINE_WORKFLOW compliant).

Must-haves:
- Single stable structure (no random template selection)
- Parameterized via `.format(...)`
- Parameters passed via function args / kwargs
"""

PROMPT_TEMPLATE = (
    "The scene shows {num_circles} circles of different sizes and colors arranged randomly.\n"
    "Keep every circle unchanged in size and color. Only rearrange their positions.\n"
    "Align all circles on a single horizontal line and sort them from left to right by circumference, from largest to smallest."
)


def get_prompt(task_type: str = "default", num_circles: int = 6, **kwargs) -> str:
    _ = task_type
    _ = kwargs
    return PROMPT_TEMPLATE.format(num_circles=int(num_circles))


def get_all_prompts(task_type: str = "default") -> list[str]:
    _ = task_type
    return [get_prompt("default")]
