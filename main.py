"""
main.py - Start LUMI - The Cosmic Collector.

Run with:  python main.py

This file only creates the window and runs the main game loop. The rules
live in game.py, the moving objects in entities.py, and the screens in ui.py.
"""

import sys

import pygame

import settings
from game import GameManager


def main():
    pygame.init()                                        # starts Pygame, fonts and sound
    screen = pygame.display.set_mode((settings.WIDTH, settings.HEIGHT))  # created once, reused for restarts
    pygame.display.set_caption(settings.TITLE)
    clock = pygame.time.Clock()
    game = GameManager(screen)

    # THE MAIN LOOP: read input -> update the game -> draw the frame, about 60 times a second.
    while game.running:
        # Delta time is the number of seconds since the last frame. Movement uses it,
        # so the game runs at the same speed on fast and slow computers. The value is
        # capped so that a long pause (for example, dragging the window) cannot make
        # objects jump across the screen.
        dt = min(clock.tick(settings.FPS) / 1000.0, 0.05)

        for event in pygame.event.get():
            game.handle_event(event)

        game.update(dt)
        game.draw()
        pygame.display.flip()                            # show the finished frame

    # Closing the window ends the loop here, so the program exits cleanly.
    game.shutdown()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
