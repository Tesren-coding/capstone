import pygame
import sys
from data import (
    TAKT_TIME, STATIONS, OPERATORS, SPECIAL_BOXES, PART_FLOW,
    WINDOW_WIDTH, WINDOW_HEIGHT,
    STATION_WIDTH, STATION_HEIGHT,
    BOTTOM_ROW_Y, TOP_ROW_Y,
    ROW_START_X, ROW_GAP,
    BOX_WIDTH, BOX_HEIGHT
)

def run_visualization(events, takt_time):

    pygame.init()
    WIDTH, HEIGHT = WINDOW_WIDTH, WINDOW_HEIGHT
    screen        = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("NFPS Repair Line Simulation")
    clock      = pygame.time.Clock()
    font       = pygame.font.SysFont(None, 22)
    font_large = pygame.font.SysFont(None, 38)
    font_small = pygame.font.SysFont(None, 18)

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
    }

    # --------------------------------------------------------
    # Row sequences — defines order of stations and boxes
    # --------------------------------------------------------
    bottom_sequence = [
        ("box",     "Incoming"),
        ("station", 1),
        ("station", 2),
        ("station", 3),
        ("box",     "HT_Out"),
        ("box",     "HT_In"),
        ("station", 4),
        ("station", 5),
        ("station", 6),
        ("station", 7),
        ("station", 8),
        ("station", 9),
    ]

    top_sequence = [
        ("box",     "Packing"),
        ("station", 16),
        ("station", 15),
        ("station", 14),
        ("station", 13),
        ("box",     "Coating_Out"),
        ("station", 12),
        ("station", 11),
        ("box",     "Coating_In"),
        ("station", 10),
    ]

    station_positions = {}
    box_positions     = {}

    # place bottom row items with equal spacing
    for i, (item_type, item_id) in enumerate(bottom_sequence):
        x = ROW_START_X + i * ROW_GAP
        if item_type == "station":
            station_positions[item_id] = (
                x, BOTTOM_ROW_Y, STATION_WIDTH, STATION_HEIGHT
            )
        else:
            box_positions[item_id] = (
                x, BOTTOM_ROW_Y, BOX_WIDTH, BOX_HEIGHT
            )

    # place top row items with equal spacing
    for i, (item_type, item_id) in enumerate(top_sequence):
        x = ROW_START_X + i * ROW_GAP
        if item_type == "station":
            station_positions[item_id] = (
                x, TOP_ROW_Y, STATION_WIDTH, STATION_HEIGHT
            )
        else:
            box_positions[item_id] = (
                x, TOP_ROW_Y, BOX_WIDTH, BOX_HEIGHT
            )

    # station centers for operator movement
    station_centers = {
        sid: (x + STATION_WIDTH // 2, y + STATION_HEIGHT // 2)
        for sid, (x, y, w, h) in station_positions.items()
    }

    # box centers
    box_centers = {
        key: (x + BOX_WIDTH // 2, y + BOX_HEIGHT // 2)
        for key, (x, y, w, h) in box_positions.items()
    }

    # --------------------------------------------------------
    # Operator tracking
    # --------------------------------------------------------
    op_names = list(OPERATORS.keys())

    def get_start_center(op):
        first_sid = OPERATORS[op]["stations"][0]
        return list(station_centers[first_sid])

    op_positions       = {op: get_start_center(op) for op in op_names}
    op_targets         = {op: get_start_center(op) for op in op_names}
    op_event_index     = {op: 0 for op in op_names}
    op_has_part        = {op: PART_FLOW[op]["start_part"] for op in op_names}
    op_dropoff_target  = {op: None for op in op_names}
    op_pending_dropoff = {op: None for op in op_names}

    op_events = {
        op: [e for e in events if e["operator"] == op]
        for op in op_names
    }

    # calculate events per takt cycle for looping
    op_cycle_length = {}
    for op in op_names:
        count = 0
        for e in op_events[op]:
            count += 1
            if e["status"] == "idle":
                break
        op_cycle_length[op] = count

    # part positions
    part_positions = {
        op: get_start_center(op) if PART_FLOW[op]["start_part"] else None
        for op in op_names
    }

    dropped_parts = {}
    speed         = 3

    # counters
    counters = {
        "incoming": SPECIAL_BOXES["Incoming"]["start"],
        "packing":  0,
    }

    # --------------------------------------------------------
    # Timing
    # --------------------------------------------------------
    sim_clock         = 0.0
    last_real_time    = pygame.time.get_ticks()
    ms_per_sim_minute = 1000
    takt_reset_count  = 0

    # --------------------------------------------------------
    # Helper: draw hatched circle
    # --------------------------------------------------------
    def draw_part(surface, cx, cy, radius=10):
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
    # Helper: draw dotted rectangle
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
    # Helper: get center of drop location
    # --------------------------------------------------------
    def get_drop_center(to_loc):
        if to_loc is None:
            return None
        if to_loc.startswith("S"):
            drop_sid = int(to_loc[1:])
            if drop_sid in station_centers:
                return list(station_centers[drop_sid])
        elif to_loc in box_centers:
            return list(box_centers[to_loc])
        return None

    # --------------------------------------------------------
    # Main loop
    # --------------------------------------------------------
    running = True
    while running:
        screen.fill(WHITE)

        # handle window close
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # update sim clock
        current_real_time  = pygame.time.get_ticks()
        elapsed_ms         = current_real_time - last_real_time
        last_real_time     = current_real_time
        sim_clock         += elapsed_ms / ms_per_sim_minute

        if sim_clock >= takt_time:
            sim_clock = 0.0
            takt_reset_count += 1

        # ---- draw banner ----
        pygame.draw.rect(screen, DARK_BLUE, (0, 0, WIDTH, 130))

        # progress bar
        bar_width = int((sim_clock / takt_time) * (WIDTH - 40))
        pygame.draw.rect(screen, GRAY,  (20, 85, WIDTH - 40, 25))
        pygame.draw.rect(screen, GREEN, (20, 85, bar_width,  25))
        pygame.draw.rect(screen, WHITE, (20, 85, WIDTH - 40, 25), 2)

        # counter text
        clock_text  = f"Cycle Time: {sim_clock:.1f} / {takt_time} min"
        clock_label = font_large.render(clock_text, True, WHITE)
        screen.blit(clock_label, (20, 20))

        takt_text  = f"Takt Cycles Completed: {takt_reset_count}"
        takt_label = font.render(takt_text, True, YELLOW)
        screen.blit(takt_label, (20, 60))

        # ---- draw special boxes ----
        for key, (x, y, w, h) in box_positions.items():
            label      = SPECIAL_BOXES[key]["label"]
            box_type   = BOX_TYPES.get(key, "in")
            dot_color  = BOX_OUT_COLOR if box_type == "out" else BOX_IN_COLOR
            box_info   = SPECIAL_BOXES[key]
            gray_color = (200, 200, 200)

            pygame.draw.rect(screen, WHITE, (x, y, w, h))
            draw_dotted_rect(screen, dot_color, (x, y, w, h), dash=5)

            box_label = font_small.render(label, True, dot_color)
            screen.blit(box_label, (x + 5, y + 8))

            if box_info.get("type") == "counter":
                if key == "Incoming":
                    count       = counters["incoming"]
                    count_color = (220, 50, 50) if count < 10 else BLACK
                    count_surf  = font_large.render(str(count), True, count_color)
                    screen.blit(count_surf,
                                (x + w//2 - count_surf.get_width()//2, y + 25))
                    sub_surf = font_small.render("remaining", True, gray_color)
                    screen.blit(sub_surf, (x + 3, y + h - 18))
                elif key == "Packing":
                    count      = counters["packing"]
                    count_surf = font_large.render(str(count), True, BLACK)
                    screen.blit(count_surf,
                                (x + w//2 - count_surf.get_width()//2, y + 25))
                    sub_surf = font_small.render("packed", True, gray_color)
                    screen.blit(sub_surf, (x + 3, y + h - 18))
            else:
                draw_part(screen, x + w // 2, y + h - 20)

        # ---- draw stations ----
        active_stations = {}
        for op in op_names:
            idx   = op_event_index[op]
            op_ev = op_events[op]
            if idx < len(op_ev) and op_ev[idx]["status"] == "working":
                active_stations[op_ev[idx]["station"]] = op

        for sid, (x, y, w, h) in station_positions.items():
            if sid in active_stations:
                op = active_stations[sid]
                pygame.draw.rect(screen, ACTIVE_BORDER,
                                 (x-3, y-3, w+6, h+6))
                pygame.draw.rect(screen, OPERATORS[op]["color"],
                                 (x, y, w, h))
            else:
                pygame.draw.rect(screen, GRAY, (x, y, w, h))

            num_label = font_small.render(f"S{sid}", True, BLACK)
            screen.blit(num_label, (x + 4, y + 4))

            name  = STATIONS[sid]["name"]
            words = name.split()
            mid_w = len(words) // 2
            line1 = " ".join(words[:mid_w])
            line2 = " ".join(words[mid_w:])
            screen.blit(font_small.render(line1, True, BLACK), (x+4, y+22))
            screen.blit(font_small.render(line2, True, BLACK), (x+4, y+38))

            ct_label = font_small.render(
                f"CT: {STATIONS[sid]['cycle_time']}m", True, BLACK)
            screen.blit(ct_label, (x+4, y+56))

        # ---- draw dropped parts ----
        for loc, (px, py) in dropped_parts.items():
            draw_part(screen, px, py)

        # ---- update operators and parts ----
        adjusted_clock = sim_clock + (takt_reset_count * takt_time)

        for op in op_names:
            op_ev = op_events[op]
            idx   = op_event_index[op]

            if idx < len(op_ev):
                current_ev = op_ev[idx]
                sid        = current_ev["station"]

                # set operator target only if not mid dropoff
                if op_pending_dropoff[op] is None:
                    if sid is not None and sid in station_centers:
                        tx, ty = station_centers[sid]
                        op_targets[op] = [tx, ty]

                # handle dropoff event
                if current_ev["status"] == "dropoff":
                    to_loc      = current_ev.get("to", None)
                    drop_center = get_drop_center(to_loc)

                    # operator has not started walking to drop yet
                    if drop_center and op_pending_dropoff[op] is None:
                        op_pending_dropoff[op] = current_ev
                        op_dropoff_target[op]  = drop_center
                        op_targets[op]         = drop_center
                        # keep has_part True only during the walk
                        # so part visually travels with operator to drop point
                        continue

                    # operator is walking to drop location
                    if op_pending_dropoff[op] is not None:
                        px, py = op_positions[op]
                        tx, ty = op_dropoff_target[op]

                        # operator arrived at drop location
                        if int(px) == int(tx) and int(py) == int(ty):
                            if to_loc == "Packing":
                                counters["packing"] += 1
                            elif to_loc.startswith("S"):
                                drop_sid = int(to_loc[1:])
                                dx, dy   = station_centers[drop_sid]
                                dropped_parts[to_loc] = (dx, dy)
                            elif to_loc in box_centers:
                                dx, dy = box_centers[to_loc]
                                dropped_parts[to_loc] = (dx, dy)

                            # clear part from operator
                            op_has_part[op]        = False
                            part_positions[op]     = None
                            op_pending_dropoff[op] = None
                            op_dropoff_target[op]  = None
                            op_event_index[op]     += 1

                            # reset target to next station immediately
                            next_idx = op_event_index[op]
                            if next_idx < len(op_events[op]):
                                next_ev  = op_events[op][next_idx]
                                next_sid = next_ev.get("station", None)

                                # if next event is pickup, do not set has_part yet
                                # wait until operator physically arrives
                                if next_ev.get("status") == "pickup":
                                    op_has_part[op] = False

                                if next_sid is not None and next_sid in station_centers:
                                    op_targets[op] = list(station_centers[next_sid])
                        continue

                # handle pickup event
                if current_ev["status"] == "pickup":
                    sid      = current_ev.get("station", None)
                    from_loc = current_ev.get("from", None)

                    # only pick up when operator has arrived at the station
                    if sid is not None and sid in station_centers:
                        tx, ty = station_centers[sid]
                        px, py = op_positions[op]

                        if int(px) == int(tx) and int(py) == int(ty):
                            if from_loc and from_loc in dropped_parts:
                                del dropped_parts[from_loc]
                            if from_loc == "Incoming":
                                counters["incoming"] = max(0, counters["incoming"] - 1)
                            op_has_part[op]    = True
                            part_positions[op] = list(op_positions[op])
                            op_event_index[op] += 1
                    continue

            # advance to next event based on sim clock
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

            # part follows operator if carrying and not mid dropoff
            if op_has_part[op] and op_pending_dropoff[op] is None:
                part_positions[op] = [px + 16, py - 16]
            elif op_pending_dropoff[op] is not None:
                # still show part during dropoff walk
                part_positions[op] = [px + 16, py - 16]
            else:
                part_positions[op] = None

        # ---- draw operators and their parts ----
        for op in op_names:
            px, py = op_positions[op]
            color  = OPERATORS[op]["color"]

            # draw part only if carrying AND not walking to drop
            if op_has_part[op] and op_pending_dropoff[op] is None and part_positions[op]:
                ppx, ppy = part_positions[op]
                draw_part(screen, ppx, ppy)

            # draw part while walking to drop location only
            elif op_pending_dropoff[op] is not None:
                draw_part(screen, int(px) + 16, int(py) - 16)

            # draw operator circle
            pygame.draw.circle(screen, color, (int(px), int(py)), 14)
            pygame.draw.circle(screen, WHITE, (int(px), int(py)), 14, 2)
            op_label = font_small.render(op, True, WHITE)
            screen.blit(op_label, (int(px) - 12, int(py) - 7))

        # ---- draw legend ----
        legend_x = 20
        legend_y = 790
        for op in op_names:
            pygame.draw.circle(screen, OPERATORS[op]["color"],
                               (legend_x, legend_y), 8)
            leg_label = font_small.render(op, True, BLACK)
            screen.blit(leg_label, (legend_x + 12, legend_y - 7))
            legend_x += 80

        draw_part(screen, legend_x, legend_y)
        part_leg = font_small.render("= Part", True, BLACK)
        screen.blit(part_leg, (legend_x + 14, legend_y - 7))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()