# Circle Arrangement Data Generator 🎲

A generator for creating circle arrangement tasks where multiple non-overlapping circles with different radii are sorted by circumference along a horizontal line.

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/arrange-circles-generator.git
cd arrange-circles-generator

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

# 4. Generate tasks
python examples/generate.py --num-samples 100
```

---

## 📁 Structure

```
arrange-circles-generator/
├── core/                    # ✅ KEEP: Standard utilities
│   ├── base_generator.py   # Abstract base class
│   ├── schemas.py          # Pydantic models
│   ├── image_utils.py      # Image helpers
│   ├── video_utils.py      # Video generation
│   └── output_writer.py    # File output
├── src/                     # ⚠️ CUSTOMIZE: Your task logic
│   ├── generator.py        # Circle arrangement generator
│   ├── prompts.py          # Prompt templates
│   └── config.py           # Configuration settings
├── examples/
│   └── generate.py         # Entry point
└── data/questions/         # Generated output
```

---

## 📦 Output Format

Every generator produces:

```
data/questions/arrange_circles_by_circumference_task/{task_id}/
├── first_frame.png          # Initial state (circles in random positions)
├── final_frame.png          # Goal state (circles sorted by circumference)
├── prompt.txt               # Instructions
└── ground_truth.mp4         # Solution video (circles moving to sorted positions)
```

---

## 🎨 Task Description

The generator creates multiple non-overlapping circles with different radii and colors. The task is to animate these circles moving from their random initial positions to a sorted arrangement along a horizontal line, ordered by circumference from largest to smallest.

### Key Features:
- **Non-overlapping circles**: Circles are generated without intersections
- **Variable radii**: Circles have random radii within configurable range
- **Smooth animation**: Circles move smoothly to their sorted positions
- **Horizontal arrangement**: Final state shows circles aligned on a horizontal line
- **Sorted by circumference**: Circles are ordered from largest to smallest circumference

---

## ⚙️ Configuration

Key configuration parameters in `src/config.py`:

- `image_size`: (1024, 1024) - Output image resolution
- `min_circles`: 5 - Minimum number of circles
- `max_circles`: 10 - Maximum number of circles
- `min_radius`: 30 - Minimum circle radius in pixels
- `max_radius`: 80 - Maximum circle radius in pixels
- `video_fps`: 10 - Video frame rate
- `video_duration`: 8.0 - Target video duration in seconds

---

## 📝 Prompts

The generator provides concise prompts (<200 words) instructing the model to animate the circles moving to their sorted positions along the horizontal line, ordered by circumference from largest to smallest.

**Single entry point:** `python examples/generate.py --num-samples 100`
