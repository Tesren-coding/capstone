import pygame
import sys 

# initialize pygame
pygame.init()

# Window settings
WIDTH, HEIGHT = 900, 400
screen = pygame.display.set_mode((WIDTH,HEIGHT))
pygame.display.set_caption("Repair Line Operator Movement")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (70, 130, 180)
RED = (220, 50, 50)
GREEN = (50, 180, 90)
GRAY = (220, 220, 220)

# Font
font = pygame.font.SysFont(None,28)

# Clock
clock = pygame.time.Clock()

# Station
stations = [
    {"name": "Inspect", "x": 80, "y": 160, "w": 180, "h": 80},
    {"name": "Repair", "x": 360, "y": 160, "w": 180, "h": 80},
    {"name": "Test", "x": 640, "y": 160, "w": 180, "h": 80},
]

# Operator start position
operator_x = 170
operator_y = 80
operator_radius = 15

# Targets above each station
targets = [
    (170,80), #Inspect
    (450, 80), #Repair
    (730, 80), #Test
]

current_target = 0
speed = 2

running = True
while running:
    screen.fill(WHITE)

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        
    # Draw station boxes
    for i, station in enumerate(stations):
        pygame.draw.rect(screen, BLUE, (station["x"], station["y"], station["w"], station["h"]))
        label = font.render(station["name"], True, WHITE)
        screen.blit(label, (station["x"] + 45, station["y"] + 25))

    # Move operator toward current target
    target_x, target_y = targets[current_target]

    if operator_x < target_x:
        operator_x += min(speed, target_x - operator_x)
    elif operator_x > target_x:
        operator_x -= min(speed, operator_x - target_x)

    if operator_y < target_y:
        operator_y += min(speed, target_y - operator_y)
    elif operator_y > target_y:
        operator_y -= min(speed, operator_y - target_y)

    # If arrived, pause and go to next station
    if operator_x == target_x and operator_y == target_y:
        pygame.time.delay(600)
        current_target = (current_target + 1) % len(targets)

    # Draw operator
    pygame.draw.circle(screen, RED, (operator_x, operator_y), operator_radius)
    op_label = font.render("Operator 1", True, BLACK)
    screen.blit(op_label, (operator_x - 35, operator_y - 35))

    # Update display
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
