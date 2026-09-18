# ============================================================
# drawing.py
# All drawing functions for the simulation visualization
# ============================================================

import pygame
import os

# --------------------------------------------------------
# Colors
# --------------------------------------------------------
WHITE         = (255, 255, 255)
BLACK         = (0,   0,   0  )
GRAY          = (200, 200, 200)
DARK_BLUE     = (30,  60,  120)
GREEN         = (50,  180, 90 )
YELLOW        = (255, 200, 0  )
ACTIVE_BORDER = (255, 220, 0  )
PART_COLOR    = (20,  20,  20 )
BOX_OUT_COLOR = (220, 50,  50 )
BOX_IN_COLOR  = (50,  180, 50 )

BOX_TYPES = {
    "Incoming":    "in",
    "HT_Out":      "out",
    "HT_In":       "in",
    "Coating_In":  "in",
    "Coating_Out": "out",
    "Packing":     "out",
    "SWIP":        "out",
}

# --------------------------------------------------------
# Part image cache
# --------------------------------------------------------
_part_image = None

def set_part_image(img):
    """Called once at startup to set the part image"""
    global _part_image
    _part_image = img

def load_part_image(width=20, height=20):
    """
    Loads the part image from images/part.png
    Returns scaled pygame.Surface or None if not found
    """
    path = "images/part.png"
    if os.path.exists(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.scale(img, (width, height))
            return img
        except Exception as e:
            print(f"Could not load part image: {e}")
            return None
    else:
        print("Part image not found at images/part.png — using fallback")
        return None

# --------------------------------------------------------
# Load and cache box images
# --------------------------------------------------------
def load_box_images(special_boxes, box_width, box_height):
    """
    Loads and scales images for each special box.
    Returns a dict of key: pygame.Surface
    Falls back to None if image not found.
    """
    images = {}
    for key, box_info in special_boxes.items():
        image_path = box_info.get("image", None)
        if image_path and os.path.exists(image_path):
            try:
                img = pygame.image.load(image_path).convert_alpha()
                img = pygame.transform.scale(img, (box_width, box_height))
                images[key] = img
            except Exception as e:
                print(f"Could not load image for {key}: {e}")
                images[key] = None
        else:
            images[key] = None
    return images

# --------------------------------------------------------
# Draw hatched circle or image (part appearance)
# --------------------------------------------------------
def draw_part(surface, cx, cy, radius=10):
    """
    Draws a part at (cx, cy).
    Uses image if available, otherwise draws hatched circle.
    """
    if _part_image is not None:
        w = _part_image.get_width()
        h = _part_image.get_height()
        surface.blit(_part_image, (int(cx) - w // 2, int(cy) - h // 2))
    else:
        pygame.draw.circle(surface, PART_COLOR, (int(cx), int(cy)), radius)
        for offset in range(-radius, radius + 1, 4):
            x1 = cx - radius
            y1 = cy + offset
            x4 = cx + radius
            y4 = cy + offset
            pygame.draw.line(surface, WHITE,
                             (int(x1), int(y1)), (int(x4), int(y4)), 1)
        pygame.draw.circle(surface, WHITE, (int(cx), int(cy)), radius, 1)

# --------------------------------------------------------
# Draw dotted rectangle
# --------------------------------------------------------
def draw_dotted_rect(surface, color, rect, dash=6):
    x, y, w, h = rect
    for i in range(0, w, dash * 2):
        pygame.draw.line(surface, color,
                         (x+i, y), (min(x+i+dash, x+w), y), 1)
        pygame.draw.line(surface, color,
                         (x+i, y+h), (min(x+i+dash, x+w), y+h), 1)
    for i in range(0, h, dash * 2):
        pygame.draw.line(surface, color,
                         (x, y+i), (x, min(y+i+dash, y+h)), 1)
        pygame.draw.line(surface, color,
                         (x+w, y+i), (x+w, min(y+i+dash, y+h)), 1)

# --------------------------------------------------------
# Draw banner and progress bar
# --------------------------------------------------------
def draw_banner(surface, sim_clock, takt_time, takt_reset_count,
                width, font_large, font):
    pygame.draw.rect(surface, DARK_BLUE, (0, 0, width, 130))

    bar_width = int((sim_clock / takt_time) * (width - 40))
    pygame.draw.rect(surface, GRAY,  (20, 85, width - 40, 25))
    pygame.draw.rect(surface, GREEN, (20, 85, bar_width,  25))
    pygame.draw.rect(surface, WHITE, (20, 85, width - 40, 25), 2)

    clock_text  = f"Cycle Time: {sim_clock:.1f} / {takt_time} min"
    clock_label = font_large.render(clock_text, True, WHITE)
    surface.blit(clock_label, (20, 20))

    takt_text  = f"Takt Cycles Completed: {takt_reset_count}"
    takt_label = font.render(takt_text, True, YELLOW)
    surface.blit(takt_label, (20, 60))

# --------------------------------------------------------
# Draw special boxes
# --------------------------------------------------------
def draw_boxes(surface, box_positions, special_boxes,
               counters, font_large, font_small, box_images=None):
    for key, (x, y, w, h) in box_positions.items():
        label      = special_boxes[key]["label"]
        box_type   = BOX_TYPES.get(key, "in")
        dot_color  = BOX_OUT_COLOR if box_type == "out" else BOX_IN_COLOR
        box_info   = special_boxes[key]
        gray_color = (200, 200, 200)

        # draw image if available otherwise white background
        if box_images and box_images.get(key):
            surface.blit(box_images[key], (x, y))
        else:
            pygame.draw.rect(surface, WHITE, (x, y, w, h))

        # always draw dotted border on top
        draw_dotted_rect(surface, dot_color, (x, y, w, h), dash=5)

        # image only box — no label or counter overlay
        if box_info.get("type") == "image":
            if not (box_images and box_images.get(key)):
                no_img = font_small.render("No Image", True, BLACK)
                surface.blit(no_img, (x + 5, y + 30))
            continue

        # label at top
        box_label = font_small.render(label, True, dot_color)
        surface.blit(box_label, (x + 5, y + 8))

        # counter boxes show number
        if box_info.get("type") == "counter":
            if key == "Incoming":
                count       = counters["incoming"]
                count_color = (220, 50, 50) if count < 10 else BLACK
                count_surf  = font_large.render(str(count), True, count_color)
                surface.blit(count_surf,
                             (x + w//2 - count_surf.get_width()//2, y + 25))
                sub_surf = font_small.render("remaining", True, gray_color)
                surface.blit(sub_surf, (x + 3, y + h - 18))
            elif key == "Packing":
                count      = counters["packing"]
                count_surf = font_large.render(str(count), True, BLACK)
                surface.blit(count_surf,
                             (x + w//2 - count_surf.get_width()//2, y + 25))
                sub_surf = font_small.render("packed", True, gray_color)
                surface.blit(sub_surf, (x + 3, y + h - 18))

        # buffer boxes show part symbol if no image
        else:
            if not (box_images and box_images.get(key)):
                draw_part(surface, x + w // 2, y + h - 20)

# --------------------------------------------------------
# Draw stations
# --------------------------------------------------------
def draw_stations(surface, station_positions, active_stations,
                  stations, operators, font_small):
    for sid, (x, y, w, h) in station_positions.items():
        if sid in active_stations:
            op = active_stations[sid]
            pygame.draw.rect(surface, ACTIVE_BORDER,
                             (x-3, y-3, w+6, h+6))
            pygame.draw.rect(surface, operators[op]["color"],
                             (x, y, w, h))
        else:
            pygame.draw.rect(surface, GRAY, (x, y, w, h))

        num_label = font_small.render(f"S{sid}", True, BLACK)
        surface.blit(num_label, (x + 4, y + 4))

        name  = stations[sid]["name"]
        words = name.split()
        mid_w = len(words) // 2
        line1 = " ".join(words[:mid_w])
        line2 = " ".join(words[mid_w:])
        surface.blit(font_small.render(line1, True, BLACK), (x+4, y+22))
        surface.blit(font_small.render(line2, True, BLACK), (x+4, y+38))

        ct_label = font_small.render(
            f"CT: {stations[sid]['cycle_time']}m", True, BLACK)
        surface.blit(ct_label, (x+4, y+56))

# --------------------------------------------------------
# Draw operators and their parts
# --------------------------------------------------------
def draw_operators(surface, op_names, op_positions, op_has_part,
                   op_pending_dropoff, part_positions, operators,
                   dropped_parts, font_small):

    # draw dropped parts first
    for loc, (px, py) in dropped_parts.items():
        draw_part(surface, px, py)

    for op in op_names:
        px, py = op_positions[op]
        color  = operators[op]["color"]

        # draw part only if carrying and not mid dropoff
        if op_has_part[op] and op_pending_dropoff[op] is None and part_positions[op]:
            ppx, ppy = part_positions[op]
            draw_part(surface, ppx, ppy)

        # draw part while walking to drop location
        elif op_pending_dropoff[op] is not None:
            draw_part(surface, int(px) + 16, int(py) - 16)

        # draw operator circle
        pygame.draw.circle(surface, color, (int(px), int(py)), 14)
        pygame.draw.circle(surface, WHITE, (int(px), int(py)), 14, 2)
        op_label = font_small.render(op, True, WHITE)
        surface.blit(op_label, (int(px) - 12, int(py) - 7))

# --------------------------------------------------------
# Draw legend
# --------------------------------------------------------
def draw_legend(surface, op_names, operators, font_small, height):
    legend_x = 20
    legend_y = height - 30

    for op in op_names:
        pygame.draw.circle(surface, operators[op]["color"],
                           (legend_x, legend_y), 8)
        leg_label = font_small.render(op, True, BLACK)
        surface.blit(leg_label, (legend_x + 12, legend_y - 7))
        legend_x += 80

    draw_part(surface, legend_x, legend_y)
    part_leg = font_small.render("= Part", True, BLACK)
    surface.blit(part_leg, (legend_x + 14, legend_y - 7))