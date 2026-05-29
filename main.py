"""Entry point. Run with: python main.py"""

import pygame
from constants import SCREEN_WIDTH, SCREEN_HEIGHT
from game import Game


def main():
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('Sentinel Wars')
    Game(screen).run()


if __name__ == '__main__':
    main()
