import pygame
pygame.mixer.init()
pygame.mixer.music.load("police_s.wav")
pygame.mixer.music.play()
while pygame.mixer.music.get_busy() == True:
    print pygame.mixer.music.get_pos()
    continue

