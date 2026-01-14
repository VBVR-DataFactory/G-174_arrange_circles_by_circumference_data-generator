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
from pathlib import Path
from PIL import Image, ImageDraw

from core import BaseGenerator, TaskPair, ImageRenderer
from core.video_utils import VideoGenerator
from .config import TaskConfig
from .prompts import get_prompt


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
        
        self.video_generator = None
        if config.generate_videos and VideoGenerator.is_available():
            self.video_generator = VideoGenerator(fps=config.video_fps, output_format="mp4")
    
    def generate_task_pair(self, task_id: str) -> TaskPair:
        """Generate one task pair."""
        
        task_data = self._generate_circles_data()
        
        first_image = self._render_initial_state(task_data)
        final_image = self._render_final_state(task_data)
        
        video_path = None
        if self.config.generate_videos and self.video_generator:
            video_path = self._generate_video(first_image, final_image, task_id, task_data)
        
        prompt = get_prompt("default")
        
        return TaskPair(
            task_id=task_id,
            domain=self.config.domain,
            prompt=prompt,
            first_image=first_image,
            final_image=final_image,
            ground_truth_video=video_path
        )
    
    def _generate_circles_data(self) -> dict:
        """Generate non-overlapping circles with random positions and radii."""
        width, height = self.config.image_size
        margin = 100
        spacing = 20
        
        max_attempts_generation = 100
        
        for gen_attempt in range(max_attempts_generation):
            num_circles = random.randint(self.config.min_circles, self.config.max_circles)
            
            circles = []
            max_attempts = 1000
            
            for _ in range(num_circles):
                radius = random.randint(self.config.min_radius, self.config.max_radius)
                
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
    
    def _generate_video(
        self,
        first_image: Image.Image,
        final_image: Image.Image,
        task_id: str,
        task_data: dict
    ) -> str:
        """Generate animation video showing circles moving to sorted positions."""
        temp_dir = Path(tempfile.gettempdir()) / f"{self.config.domain}_videos"
        temp_dir.mkdir(parents=True, exist_ok=True)
        video_path = temp_dir / f"{task_id}_ground_truth.mp4"
        
        frames = self._create_animation_frames(task_data)
        
        result = self.video_generator.create_video_from_frames(
            frames,
            video_path
        )
        
        return str(result) if result else None
    
    def _create_animation_frames(self, task_data: dict) -> list:
        """Create animation frames showing circles moving to sorted positions."""
        width, height = self.config.image_size
        total_frames = int(self.config.video_fps * self.config.video_duration)
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
