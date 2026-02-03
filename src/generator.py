"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           YOUR TASK GENERATOR                                 ║
║                                                                               ║
║  CUSTOMIZE THIS FILE to implement your data generation logic.                 ║
║  Replace the example implementation with your own task.                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import random
import tempfile
import math
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

from core import BaseGenerator, TaskPair, ImageRenderer
from .config import TaskConfig
from .prompts import get_prompt

TARGET_DATASET_SIZE = 10_000


class TaskGenerator(BaseGenerator):
    """
    Circle arrangement task generator.
    
    Generates multiple non-overlapping circles with different radii,
    then animates them sorting by circumference (largest to smallest)
    along a horizontal line.
    """
    
    def __init__(self, config: TaskConfig):
        super().__init__(config)
        self.renderer = ImageRenderer(image_size=config.image_size)

        # Best-effort deduplication within a run
        self.seen_combinations = set()
    
    def generate_task_pair(self, task_id: str) -> TaskPair:
        """Generate one task pair."""
        task_data = None
        sig = None
        for _ in range(200):
            candidate = self._generate_circles_data()
            candidate_sig = self._task_signature(candidate)
            if candidate_sig not in self.seen_combinations:
                task_data = candidate
                sig = candidate_sig
                break
        if task_data is None:
            task_data = self._generate_circles_data()
            sig = self._task_signature(task_data)
        self.seen_combinations.add(sig)
        
        first_image = self._render_initial_state(task_data)
        final_image = self._render_final_state(task_data)
        
        video_path = None
        if self.config.generate_videos:
            task_dir = Path(self.config.output_dir) / f"{self.config.domain}_task" / task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            video_path = self._generate_video(task_data, task_dir)
        
        prompt = get_prompt("default", num_circles=int(task_data.get("num_circles", 0)))
        
        return TaskPair(
            task_id=task_id,
            domain=self.config.domain,
            prompt=prompt,
            first_image=first_image,
            final_image=final_image,
            ground_truth_video=video_path
        )

    def _task_signature(self, task_data: dict) -> tuple:
        # Signature reflects visible content: count + radii + start positions + colors + final order.
        circles = task_data["circles"]
        # Use rounded ints for stability.
        start = tuple(sorted((int(c["id"]), int(c["x"]), int(c["y"]), int(c["radius"]), tuple(c["color"])) for c in circles))
        order = tuple(int(c["id"]) for c in task_data["sorted_circles"])
        return (int(task_data["num_circles"]), start, order, int(task_data["line_y"]))
    
    def _generate_circles_data(self) -> dict:
        """Generate non-overlapping circles with random positions and radii."""
        width, height = self.config.image_size
        margin = 100
        spacing = int(self.config.min_spacing)
        
        max_attempts_generation = 100
        
        for gen_attempt in range(max_attempts_generation):
            requested = random.randint(self.config.min_circles, self.config.max_circles)

            # Enforce visually obvious size gaps; if not feasible with requested count,
            # gradually reduce the count until we can construct a valid radius set.
            radii = None
            num_circles = requested
            while num_circles >= int(self.config.min_circles):
                radii = self._sample_radii_with_obvious_gaps(num_circles, width=width, margin=margin, spacing=spacing)
                if radii is not None:
                    break
                num_circles -= 1
            if radii is None:
                continue
            
            circles = []
            max_attempts = 1000
            
            for radius in radii:
                
                for attempt in range(max_attempts):
                    x = random.randint(margin + radius, width - margin - radius)
                    y = random.randint(margin + radius, height - margin - radius)
                    
                    if not self._check_overlap(x, y, radius, circles):
                        color = random.choice(self.config.circle_colors)
                        circumference = 2 * math.pi * radius
                        circles.append({
                            'x': x,
                            'y': y,
                            'radius': radius,
                            'color': color,
                            'circumference': circumference,
                            'id': len(circles)
                        })
                        break
            
            sorted_circles = sorted(circles, key=lambda c: c['circumference'], reverse=True)
            
            line_y = height // 2
            total_width = sum(c['radius'] * 2 for c in sorted_circles) + spacing * (len(sorted_circles) - 1)
            
            if total_width <= width - 2 * margin:
                start_x = (width - total_width) // 2
                
                current_x = start_x
                for circle in sorted_circles:
                    circle['final_x'] = current_x + circle['radius']
                    circle['final_y'] = line_y
                    current_x += circle['radius'] * 2 + spacing
                
                return {
                    'circles': circles,
                    'sorted_circles': sorted_circles,
                    'line_y': line_y,
                    'num_circles': num_circles
                }
        
        return {
            'circles': circles,
            'sorted_circles': sorted_circles,
            'line_y': line_y,
            'num_circles': num_circles
        }

    def _sample_radii_with_obvious_gaps(self, n: int, *, width: int, margin: int, spacing: int) -> list[int] | None:
        """Sample radii so adjacent sizes are clearly different AND final lineup fits."""
        min_r = int(self.config.min_radius)
        max_r = int(self.config.max_radius)
        gap = int(self.config.min_radius_gap)
        ratio_min = float(self.config.min_radius_ratio)

        # Available width for aligned circles (diameters + spacing)
        avail = width - 2 * margin - spacing * (n - 1)
        if avail <= 0:
            return None

        # Try a geometric progression (ensures visible differences).
        for _ in range(300):
            ratio = random.uniform(ratio_min, min(1.35, ratio_min + 0.18))
            # Geometric sum for radii (smallest -> largest)
            geom_sum = (ratio**n - 1.0) / (ratio - 1.0)
            # From width constraint: 2 * r_min * geom_sum <= avail
            rmin_upper_from_width = avail / (2.0 * geom_sum)
            # From max radius constraint: r_min * ratio^(n-1) <= max_r
            rmin_upper_from_max = max_r / (ratio ** (n - 1))
            rmin_upper = min(rmin_upper_from_width, rmin_upper_from_max)
            if rmin_upper < min_r:
                continue

            r_min = random.uniform(min_r, rmin_upper)
            raw = [r_min * (ratio**i) for i in range(n)]
            # Convert to ints, then enforce strict increasing (unique) with minimum gap.
            radii = [int(round(x)) for x in raw]
            radii.sort()
            fixed: list[int] = []
            for r in radii:
                if not fixed:
                    fixed.append(max(min_r, min(max_r, r)))
                else:
                    next_r = max(fixed[-1] + gap, int(math.ceil(fixed[-1] * ratio_min)))
                    next_r = max(next_r, r)
                    if next_r > max_r:
                        fixed = []
                        break
                    fixed.append(next_r)
            if not fixed:
                continue

            # Now we have increasing radii; convert to list for placement (unsorted ok)
            # and verify adjacent ratio in the final sorted order.
            fixed_sorted = sorted(fixed, reverse=True)
            ok_ratio = True
            for a, b in zip(fixed_sorted, fixed_sorted[1:]):
                if a / b < ratio_min - 1e-6:
                    ok_ratio = False
                    break
            if not ok_ratio:
                continue

            total_width = sum(2 * r for r in fixed_sorted) + spacing * (n - 1)
            if total_width > width - 2 * margin:
                continue
            return fixed_sorted  # return largest->smallest

        return None

    def _sample_unique_radius(self, circles: list) -> int:
        """Sample a radius that keeps circumference ordering unique."""
        min_r = int(self.config.min_radius)
        max_r = int(self.config.max_radius)
        gap = int(self.config.min_radius_gap)
        existing = [int(c["radius"]) for c in circles]
        # Try random draws first
        for _ in range(200):
            r = random.randint(min_r, max_r)
            if all(abs(r - e) >= gap for e in existing):
                return r
        # Fallback: deterministic scan
        for r in range(min_r, max_r + 1):
            if all(abs(r - e) >= gap for e in existing):
                return r
        # If range is too tight, relax slightly (still avoid exact ties)
        for _ in range(200):
            r = random.randint(min_r, max_r)
            if r not in existing:
                return r
        return random.randint(min_r, max_r)
    
    def _check_overlap(self, x: int, y: int, radius: int, existing_circles: list) -> bool:
        """Check if a circle overlaps with existing circles."""
        padding = 10
        for circle in existing_circles:
            distance = math.sqrt((x - circle['x']) ** 2 + (y - circle['y']) ** 2)
            if distance < radius + circle['radius'] + padding:
                return True
        return False
    
    def _render_initial_state(self, task_data: dict) -> Image.Image:
        """Render circles in random positions."""
        width, height = self.config.image_size
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        for circle in task_data['circles']:
            x, y, r = circle['x'], circle['y'], circle['radius']
            draw.ellipse([x - r, y - r, x + r, y + r], fill=circle['color'], outline=(0, 0, 0), width=2)
        
        return img
    
    def _render_final_state(self, task_data: dict) -> Image.Image:
        """Render circles sorted by circumference on horizontal line."""
        width, height = self.config.image_size
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        line_y = task_data['line_y']
        
        for circle in task_data['sorted_circles']:
            x, y, r = circle['final_x'], circle['final_y'], circle['radius']
            draw.ellipse([x - r, y - r, x + r, y + r], fill=circle['color'], outline=(0, 0, 0), width=2)
        
        return img
    
    def _generate_video(self, task_data: dict, task_dir: Path) -> str:
        """Generate animation video without cv2/numpy (ffmpeg preferred)."""
        frames = self._create_animation_frames(task_data)
        mp4_path = task_dir / "ground_truth.mp4"
        if self._try_write_mp4_with_ffmpeg(frames, mp4_path, fps=int(self.config.video_fps), temp_dir=task_dir):
            return str(mp4_path)
        gif_path = task_dir / "ground_truth.gif"
        self._write_gif(frames, gif_path, fps=int(self.config.video_fps))
        return str(gif_path)

    def _try_write_mp4_with_ffmpeg(self, frames: list[Image.Image], out_path: Path, *, fps: int, temp_dir: Path) -> bool:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return False
        with tempfile.TemporaryDirectory(dir=temp_dir, prefix="_frames_") as tmp:
            frames_dir = Path(tmp)
            for i, im in enumerate(frames):
                ImageRenderer.ensure_rgb(im).save(frames_dir / f"frame_{i:04d}.png")
            cmd = [
                ffmpeg,
                "-y",
                "-framerate",
                str(max(1, fps)),
                "-i",
                str(frames_dir / "frame_%04d.png"),
                "-vf",
                "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-pix_fmt",
                "yuv420p",
                str(out_path),
            ]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                return False
        return out_path.exists()

    def _write_gif(self, frames: list[Image.Image], out_path: Path, *, fps: int) -> None:
        duration_ms = int(round(1000.0 / max(1, fps)))
        rgb_frames = [ImageRenderer.ensure_rgb(im) for im in frames]
        rgb_frames[0].save(
            out_path,
            save_all=True,
            append_images=rgb_frames[1:],
            duration=duration_ms,
            loop=0,
            optimize=False,
        )
    
    def _create_animation_frames(self, task_data: dict) -> list:
        """Create animation frames showing circles moving to sorted positions."""
        width, height = self.config.image_size
        # Hard cap: keep video within 5 seconds.
        duration_s = min(float(self.config.video_duration), 5.0)
        total_frames = int(self.config.video_fps * duration_s)
        total_frames = max(3, total_frames)
        hold_frames = int(total_frames * 0.1)
        transition_frames = total_frames - 2 * hold_frames
        
        frames = []
        
        initial_frame = self._render_initial_state(task_data)
        for _ in range(hold_frames):
            frames.append(initial_frame)
        
        circles = task_data['circles']
        sorted_circles = task_data['sorted_circles']
        
        circle_map = {c['id']: c for c in circles}
        for sorted_circle in sorted_circles:
            original_circle = circle_map[sorted_circle['id']]
            original_circle['start_x'] = original_circle['x']
            original_circle['start_y'] = original_circle['y']
            original_circle['end_x'] = sorted_circle['final_x']
            original_circle['end_y'] = sorted_circle['final_y']
        
        for i in range(transition_frames):
            progress = i / (transition_frames - 1) if transition_frames > 1 else 1.0
            ease_progress = self._ease_in_out(progress)
            
            img = Image.new('RGB', (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)
            
            for circle in circles:
                current_x = circle['start_x'] + (circle['end_x'] - circle['start_x']) * ease_progress
                current_y = circle['start_y'] + (circle['end_y'] - circle['start_y']) * ease_progress
                r = circle['radius']
                draw.ellipse([current_x - r, current_y - r, current_x + r, current_y + r], 
                           fill=circle['color'], outline=(0, 0, 0), width=2)
            
            frames.append(img)
        
        final_frame = self._render_final_state(task_data)
        for _ in range(hold_frames):
            frames.append(final_frame)
        
        return frames
    
    def _ease_in_out(self, t: float) -> float:
        """Easing function for smooth animation."""
        return t * t * (3 - 2 * t)
