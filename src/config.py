"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           YOUR TASK CONFIGURATION                             ║
║                                                                               ║
║  CUSTOMIZE THIS FILE to define your task-specific settings.                   ║
║  Inherits common settings from core.GenerationConfig                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from pydantic import Field
from core import GenerationConfig


class TaskConfig(GenerationConfig):
    """
    Your task-specific configuration.
    
    CUSTOMIZE THIS CLASS to add your task's hyperparameters.
    
    Inherited from GenerationConfig:
        - num_samples: int          # Number of samples to generate
        - domain: str               # Task domain name
        - difficulty: Optional[str] # Difficulty level
        - random_seed: Optional[int] # For reproducibility
        - output_dir: Path          # Where to save outputs
        - image_size: tuple[int, int] # Image dimensions
    """
    
    # ══════════════════════════════════════════════════════════════════════════
    #  OVERRIDE DEFAULTS
    # ══════════════════════════════════════════════════════════════════════════
    
    domain: str = Field(default="arrange_circles_by_circumference")
    image_size: tuple[int, int] = Field(default=(1024, 1024))
    
    # ══════════════════════════════════════════════════════════════════════════
    #  VIDEO SETTINGS
    # ══════════════════════════════════════════════════════════════════════════
    
    generate_videos: bool = Field(
        default=True,
        description=(
            "Whether to generate ground truth videos. "
            "Implemented without cv2/numpy; can be disabled if desired."
        ),
    )
    
    video_fps: int = Field(
        default=16,
        description="Video frame rate"
    )
    
    video_duration: float = Field(
        default=5.0,
        description="Target video duration in seconds (capped at 5s)"
    )
    
    # ══════════════════════════════════════════════════════════════════════════
    #  TASK-SPECIFIC SETTINGS
    # ══════════════════════════════════════════════════════════════════════════
    
    min_circles: int = Field(
        default=5,
        description="Minimum number of circles"
    )
    
    max_circles: int = Field(
        default=10,
        description="Maximum number of circles"
    )
    
    min_radius: int = Field(
        default=30,
        description="Minimum circle radius in pixels"
    )
    
    max_radius: int = Field(
        default=80,
        description="Maximum circle radius in pixels"
    )

    min_radius_gap: int = Field(
        default=4,
        ge=1,
        le=30,
        description="Minimum difference between any two circle radii (ensures unique circumference ordering).",
    )

    min_radius_ratio: float = Field(
        default=1.15,
        ge=1.05,
        le=2.0,
        description="Minimum ratio between adjacent radii after sorting (ensures visually obvious size differences).",
    )

    min_spacing: int = Field(
        default=16,
        ge=8,
        le=80,
        description="Minimum spacing between circles when aligned on the line.",
    )
    
    circle_colors: list = Field(
        default_factory=lambda: [
            (255, 100, 100), (100, 255, 100), (100, 100, 255),
            (255, 255, 100), (255, 100, 255), (100, 255, 255),
            (255, 150, 50), (150, 255, 50), (50, 150, 255),
            (200, 200, 200)
        ],
        description="Available colors for circles"
    )
