import pygame
import sys

def run_visualization(events, takt_time):

    pygame.init()
    WIDTH, HEIGHT = 900, 500
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Repair Line Simulation")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 28)
    font_large = pygame.font.SysFont(None, 42)

    # Colors
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    BLUE = (70, 130, 180)
    RED = (220, 50, 50)
    GREEN = (50, 180, 90)
    GRAY = (200, 200, 200)
    YELLOW = (255, 200, 0)
    DARK_BLUE = (30, 60, 120)

    # Station positions
    station_positions = {
        "Inspect": (80, 250, 180, 80),
        "Repair": (360, 250, 180, 80),
        "Test": (640, 250, 180, 80),
    }

    station_centers = {
        "Inspect": (170, 210),
        "Repair": (450, 210),
        "Test": (730, 210),
    }

    # Operator starting variables
    op_x, op_y = 170, 210
    op_target_x, op_target_y = 170, 210
    current_event_index = 0
    speed = 3

    # Clock and timing variables
    sim_clock = 0.0
    last_real_time = pygame.time.get_ticks()
    ms_per_sim_minute = 1000
    takt_reset_count = 0

    running = True
    while running:

        # 1. clear screen
        screen.fill(WHITE)

        # 2. handle window close
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 3. update sim clock
        current_real_time = pygame.time.get_ticks()
        elapsed_ms = current_real_time - last_real_time
        last_real_time = current_real_time
        sim_clock += elapsed_ms / ms_per_sim_minute

        if sim_clock >= takt_time:
            sim_clock = 0.0
            takt_reset_count += 1

        # 4. draw dark blue banner
        pygame.draw.rect(screen, DARK_BLUE, (0, 0, WIDTH, 120))

        # 5. draw progress bar
        bar_width = int((sim_clock / takt_time) * (WIDTH - 40))
        pygame.draw.rect(screen, GRAY, (20, 70, WIDTH - 40, 30))
        pygame.draw.rect(screen, GREEN, (20, 70, bar_width, 30))
        pygame.draw.rect(screen, WHITE, (20, 70, WIDTH - 40, 30), 2)

        # 6. draw counter text
        clock_text = f"Cycle Time: {sim_clock:.1f} / {takt_time} min"
        clock_label = font_large.render(clock_text, True, WHITE)
        screen.blit(clock_label, (20, 20))

        takt_text = f"Takt Cycles Completed: {takt_reset_count}"
        takt_label = font.render(takt_text, True, YELLOW)
        screen.blit(takt_label, (WIDTH - 280, 20))

        # 7. get active station
        active_station = ""
        if current_event_index < len(events):
            current_event = events[current_event_index]
            if current_event["status"] == "working":
                active_station = current_event["station"]

        # 8. draw stations
        for name, (x, y, w, h) in station_positions.items():
            if name == active_station:
                pygame.draw.rect(screen, YELLOW, (x - 3, y - 3, w + 6, h + 6))
                pygame.draw.rect(screen, BLUE, (x, y, w, h))
            else:
                pygame.draw.rect(screen, GRAY, (x, y, w, h))
            label = font.render(name, True, BLACK)
            screen.blit(label, (x + 45, y + 25))

        # 9. draw cycle time labels inside stations
        cycle_times_display = {"Inspect": 5, "Repair": 12, "Test": 8}
        for name, (x, y, w, h) in station_positions.items():
            ct_label = font.render(f"{cycle_times_display[name]} min", True, BLACK)
            screen.blit(ct_label, (x + 55, y + 50))

        # 10. set operator target from events
        if current_event_index < len(events):
            next_event = events[current_event_index]
            target_station = next_event["station"]
            if target_station in station_centers:
                op_target_x, op_target_y = station_centers[target_station]

        # 11. advance event based on sim clock
        if current_event_index < len(events) - 1:
            adjusted_clock = sim_clock + (takt_reset_count * takt_time)
            next_event_time = events[current_event_index + 1]["time"]
            if adjusted_clock >= next_event_time:
                if op_x == op_target_x and op_y == op_target_y:
                    current_event_index += 1

        # 12. move operator smoothly
        if op_x < op_target_x:
            op_x += min(speed, op_target_x - op_x)
        elif op_x > op_target_x:
            op_x -= min(speed, op_x - op_target_x)

        if op_y < op_target_y:
            op_y += min(speed, op_target_y - op_y)
        elif op_y > op_target_y:
            op_y -= min(speed, op_y - op_target_y)

        # 13. draw operator
        pygame.draw.circle(screen, RED, (op_x, op_y), 18)
        pygame.draw.circle(screen, WHITE, (op_x, op_y), 18, 2)
        op_label = font.render("Op1", True, WHITE)
        screen.blit(op_label, (op_x - 15, op_y - 10))

        # 14. draw legend
        pygame.draw.rect(screen, YELLOW, (20, 420, 20, 20))
        legend1 = font.render("= Active Station", True, BLACK)
        screen.blit(legend1, (50, 420))

        pygame.draw.rect(screen, GRAY, (250, 420, 20, 20))
        legend2 = font.render("= Idle Station", True, BLACK)
        screen.blit(legend2, (280, 420))

        pygame.draw.circle(screen, RED, (500, 430), 10)
        legend3 = font.render("= Operator", True, BLACK)
        screen.blit(legend3, (520, 420))

        # 15. refresh display
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()