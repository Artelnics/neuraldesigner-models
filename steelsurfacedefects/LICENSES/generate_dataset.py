"""Rebuild the Artelnics synthetic steel-surface image dataset."""

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


root = Path(__file__).resolve().parents[1] / "steel_surface_defects_data"
classes = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]
for class_index, label in enumerate(classes):
    folder = root / label
    folder.mkdir(parents=True, exist_ok=True)
    for index in range(100):
        rng = np.random.default_rng(1000 * class_index + index)
        array = np.clip(rng.normal(145, 12, (200, 200)), 0, 255).astype(np.uint8)
        image = Image.fromarray(array, mode="L")
        draw = ImageDraw.Draw(image)
        if label == "crazing":
            for _ in range(9):
                points = [(int(rng.integers(0, 200)), int(rng.integers(0, 200)))]
                for _ in range(5):
                    x, y = points[-1]
                    points.append((max(0, min(199, x + int(rng.integers(-25, 26)))), max(0, min(199, y + int(rng.integers(-25, 26))))))
                draw.line(points, fill=int(rng.integers(25, 75)), width=1)
        elif label == "inclusion":
            for _ in range(12):
                x, y, radius = int(rng.integers(5, 195)), int(rng.integers(5, 195)), int(rng.integers(3, 11))
                draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=int(rng.integers(30, 90)))
        elif label == "patches":
            for _ in range(6):
                x, y = int(rng.integers(0, 165)), int(rng.integers(0, 165))
                draw.rounded_rectangle((x, y, x+int(rng.integers(15, 40)), y+int(rng.integers(15, 40))), radius=5, fill=int(rng.integers(70, 115)))
        elif label == "pitted_surface":
            for _ in range(70):
                x, y, radius = int(rng.integers(2, 198)), int(rng.integers(2, 198)), int(rng.integers(1, 4))
                draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=int(rng.integers(35, 105)))
        elif label == "rolled-in_scale":
            for y in range(-20, 220, 18):
                points = [(x, int(y + 7 * math.sin((x + index) / 18))) for x in range(200)]
                draw.line(points, fill=int(rng.integers(65, 110)), width=int(rng.integers(3, 7)))
        else:
            for _ in range(8):
                x, y = int(rng.integers(0, 50)), int(rng.integers(0, 200))
                draw.line((x, y, x+int(rng.integers(120, 200)), y+int(rng.integers(-15, 16))), fill=int(rng.integers(20, 75)), width=int(rng.integers(1, 3)))
        image.save(folder / f"{label}_{index:03d}.bmp")
