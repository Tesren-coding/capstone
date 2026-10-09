# ============================================================
# visualization.py
# Main visualization loop
# ============================================================

import pygame
import sys

from data import (
    OPERATORS, STATIONS, SPECIAL_BOXES,
    WINDOW_WIDTH, WINDOW_HEIGHT,
    BOX_WIDTH, BOX_HEIGHT
)
from layout  import build_positions
from drawing import (
    draw_banner, draw_boxes, draw_stations,
    draw_operators, draw_legend, draw_part,
    load_box_images, load_part_image, set_part_image
)
from state import build_state

def run_visualization(events, takt_time):

    pygame.init()
    WIDTH, HEIGHT = WINDOW_WIDTH, WINDOW_HEIGHT
    screen        = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("NFPS Repair Line Simulation")
    clock      = pygame.time.Clock()
    font       = pygame.font.SysFont(None, 22)
    font_large = pygame.font.SysFont(None, 38)
    font_small = pygame.font.SysFont(None, 18)

    WHITE      = (255, 255, 255)
    BLACK      = (0,   0,   0  )
    DARK_BLUE  = (30,  60,  120)
    GREEN      = (50,  180, 90 )
    RED        = (200, 50,  50 )
    GRAY       = (200, 200, 200)
    DARK_GRAY  = (150, 150, 150)

    # build layout
    station_positions, box_positions, station_centers, box_centers = \
        build_positions()

    # load images
    box_images = load_box_images(SPECIAL_BOXES, BOX_WIDTH, BOX_HEIGHT)
    part_img   = load_part_image(width=20, height=20)
    set_part_image(part_img)

    # build state
    op_names = list(OPERATORS.keys())
    state    = build_state(events, station_centers, box_centers, op_names)

    op_positions       = state["op_positions"]
    op_targets         = state["op_targets"]
    op_event_index     = state["op_event_index"]
    op_has_part        = state["op_has_part"]
    op_dropoff_target  = state["op_dropoff_target"]
    op_pending_dropoff = state["op_pending_dropoff"]
    op_events          = state["op_events"]
    op_cycle_length    = state["op_cycle_length"]
    part_positions     = state["part_positions"]
    dropped_parts      = state["dropped_parts"]
    counters           = state["counters"]

    speed             = 3
    sim_clock         = 0.0
    last_real_time    = pygame.time.get_ticks()
    ms_per_sim_minute = 1000
    takt_reset_count  = 0

    # --------------------------------------------------------
    # Simulation state
    # starts paused — user must press START
    # --------------------------------------------------------
    is_running = False

    # --------------------------------------------------------
    # Button definitions
    # positioned in the banner on the right side
    # --------------------------------------------------------
    btn_start = pygame.Rect(WIDTH - 220, 20, 90, 40)
    btn_stop  = pygame.Rect(WIDTH - 120, 20, 90, 40)

    # --------------------------------------------------------
    # Helper: draw a button
    # --------------------------------------------------------
    def draw_button(surface, rect, label, active_color, inactive_color,
                    is_active, font):
        color = active_color if is_active else inactive_color
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, WHITE,  rect, 2)
        text = font.render(label, True, WHITE)
        surface.blit(text, (
            rect.x + rect.width  // 2 - text.get_width()  // 2,
            rect.y + rect.height // 2 - text.get_height() // 2
        ))

    # --------------------------------------------------------
    # Helper: get center of any location
    # --------------------------------------------------------
    def get_loc_center(loc):
        if loc is None:
            return None
        if isinstance(loc, int):
            if loc in station_centers:
                return list(station_centers[loc])
        elif isinstance(loc, str):
            if loc in box_centers:
                return list(box_centers[loc])
        return None

    # --------------------------------------------------------
    # Main loop
    # --------------------------------------------------------
    running = True
    while running:
        screen.fill(WHITE)

        # ---- handle events ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # button clicks
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if btn_start.collidepoint(event.pos):
                        is_running = True
                        last_real_time = pygame.time.get_ticks()
                    if btn_stop.collidepoint(event.pos):
                        is_running = False

        # ---- update sim clock only when running ----
        current_real_time = pygame.time.get_ticks()
        if is_running:
            elapsed_ms  = current_real_time - last_real_time
            sim_clock  += elapsed_ms / ms_per_sim_minute

            if sim_clock >= takt_time:
                sim_clock = 0.0
                takt_reset_count += 1

        last_real_time = current_real_time

        # ---- draw banner ----
        draw_banner(screen, sim_clock, takt_time, takt_reset_count,
                    WIDTH, font_large, font)

        # ---- draw START / STOP buttons ----
        draw_button(screen, btn_start, "START",
                    active_color   = GREEN,
                    inactive_color = DARK_GRAY,
                    is_active      = is_running,
                    font           = font)

        draw_button(screen, btn_stop, "STOP",
                    active_color   = RED,
                    inactive_color = DARK_GRAY,
                    is_active      = not is_running,
                    font           = font)

        # ---- draw paused overlay text ----
        if not is_running:
            pause_surf = font_large.render(
                "PAUSED — Press START to begin", True, DARK_BLUE)
            screen.blit(pause_surf, (
                WIDTH  // 2 - pause_surf.get_width()  // 2,
                HEIGHT // 2 - pause_surf.get_height() // 2
            ))

        # ---- draw special boxes ----
        draw_boxes(screen, box_positions, SPECIAL_BOXES,
                   counters, font_large, font_small, box_images)

        # ---- get active stations ----
        active_stations = {}
        for op in op_names:
            idx   = op_event_index[op]
            op_ev = op_events[op]
            if idx < len(op_ev):
                ev = op_ev[idx]
                if ev["status"] == "working" and isinstance(ev["loc"], int):
                    active_stations[ev["loc"]] = op

        # ---- draw stations ----
        draw_stations(screen, station_positions, active_stations,
                      STATIONS, OPERATORS, font_small)

        # ---- update operators only when running ----
        if is_running:
            adjusted_clock = sim_clock + (takt_reset_count * takt_time)

            for op in op_names:
                op_ev = op_events[op]
                idx   = op_event_index[op]

                if idx < len(op_ev):
                    current_ev = op_ev[idx]
                    loc        = current_ev["loc"]

                    # set target only if not mid dropoff
                    if op_pending_dropoff[op] is None:
                        center = get_loc_center(loc)
                        if center:
                            op_targets[op] = center

                    # ---- handle dropoff ----
                    if current_ev["status"] == "dropoff":
                        to_loc      = current_ev.get("to", None)
                        drop_center = get_loc_center(to_loc)

                        if drop_center and op_pending_dropoff[op] is None:
                            op_pending_dropoff[op] = current_ev
                            op_dropoff_target[op]  = drop_center
                            op_targets[op]         = drop_center
                            continue

                        if op_pending_dropoff[op] is not None:
                            px, py = op_positions[op]
                            tx, ty = op_dropoff_target[op]

                            if int(px) == int(tx) and int(py) == int(ty):
                                if to_loc == "Packing":
                                    counters["packing"] += 1
                                elif isinstance(to_loc, int):
                                    dx, dy = station_centers[to_loc]
                                    dropped_parts[to_loc] = (dx, dy)
                                elif isinstance(to_loc, str) and to_loc in box_centers:
                                    dx, dy = box_centers[to_loc]
                                    dropped_parts[to_loc] = (dx, dy)

                                op_has_part[op]        = False
                                part_positions[op]     = None
                                op_pending_dropoff[op] = None
                                op_dropoff_target[op]  = None
                                op_event_index[op]     += 1

                                next_idx = op_event_index[op]
                                if next_idx < len(op_events[op]):
                                    next_ev     = op_events[op][next_idx]
                                    next_center = get_loc_center(
                                        next_ev.get("loc"))
                                    if next_center:
                                        op_targets[op] = next_center
                            continue

                    # ---- handle pickup ----
                    if current_ev["status"] == "pickup":
                        from_loc = current_ev.get("from", None)
                        center   = get_loc_center(loc)

                        if center:
                            px, py = op_positions[op]
                            tx, ty = center

                            if int(px) == int(tx) and int(py) == int(ty):
                                if loc in dropped_parts:
                                    del dropped_parts[loc]
                                if from_loc == "Incoming":
                                    counters["incoming"] = max(
                                        0, counters["incoming"] - 1)
                                op_has_part[op]    = True
                                part_positions[op] = list(op_positions[op])
                                op_event_index[op] += 1
                        continue

                    # ---- handle moving ----
                    if current_ev["status"] == "moving":
                        op_event_index[op] += 1
                        continue

                # advance to next event
                if idx < len(op_ev) - 1:
                    next_ev = op_ev[idx + 1]
                    if adjusted_clock >= next_ev["time"]:
                        px, py = op_positions[op]
                        tx, ty = op_targets[op]
                        if int(px) == int(tx) and int(py) == int(ty):
                            op_event_index[op] += 1

                # loop back when events run out
                elif idx >= len(op_ev) - 1:
                    cycle_len = op_cycle_length[op]
                    op_event_index[op] = max(0, len(op_ev) - cycle_len)

            # ---- move operators smoothly ----
            for op in op_names:
                tx, ty = op_targets[op]
                px, py = op_positions[op]

                if px < tx:
                    px += min(speed, tx - px)
                elif px > tx:
                    px -= min(speed, px - tx)

                if py < ty:
                    py += min(speed, ty - py)
                elif py > ty:
                    py -= min(speed, py - ty)

                op_positions[op] = [px, py]

                if op_has_part[op] and op_pending_dropoff[op] is None:
                    part_positions[op] = [px + 16, py - 16]
                elif op_pending_dropoff[op] is not None:
                    part_positions[op] = [px + 16, py - 16]
                else:
                    part_positions[op] = None

        # ---- draw operators and parts ----
        draw_operators(screen, op_names, op_positions, op_has_part,
                       op_pending_dropoff, part_positions, OPERATORS,
                       dropped_parts, font_small)

        # ---- draw legend ----
        draw_legend(screen, op_names, OPERATORS, font_small, HEIGHT)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()