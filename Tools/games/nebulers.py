import sys
import os
import sys, os
import time

playerX = 0
playerY = 0
player_Life = 10
terrain = []
terrain_width = 30   # largeur
terrain_height = 15  # hauteur
Menu_Principale = True
isPlayingGame = False


air = " "  
grass =  "■"
dirt = "□"


terrain = [[air for x in range(terrain_width)] for y in range(terrain_height)]

for x in range(terrain_width):
    terrain[terrain_height-1][x] = dirt  # dirt

for x in range(terrain_width):
    terrain[terrain_height-2][x] = grass  # herbe

def draw_terrain():
    for row in terrain:
        print("".join(row))

# le but est de faire un minecraft en 2d exlique moi comment faire sans me le coder
# Détection de l'OS
if os.name == "nt":
    import msvcrt
else:
    import termios
    import tty

def get_key():
    """Lit une touche, fonctionne sur Windows et Linux/macOS"""
    if os.name == "nt":
        # Windows
        return msvcrt.getch().decode("utf-8")
    else:
        # Linux / macOS
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            key = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return key

def afficher_menu(choice):
    os.system("cls" if os.name == "nt" else "clear")
    options = ["play", "options", "exit"]
    for i, option in enumerate(options, start=1):
        if i == choice:
            print(option.upper())  # Met en majuscule la sélection
        else:
            print(option)




def Play_Game():
    isPlayingGame = True
    os.system("cls" if os.name == "nt" else "clear")
    Player_Name_Question = input("Choose a player name: ")
    print(f"Welcome, {Player_Name_Question}!")
    time.sleep(2)
    os.system("cls" if os.name == "nt" else "clear")
    draw_terrain()





def Menu_Principale():
    
    player_choice = 1
    previous_choice = -1
    

    afficher_menu(player_choice)

    while isPlayingGame == False:
        key = get_key()

        if key.lower() == "q":  # Quitter
            break
        elif key.lower() == "s":  # Descendre
            player_choice = (player_choice % 3) + 1
        elif key.lower() == "w":  # Monter
            player_choice = (player_choice - 2) % 3 + 1
        elif key in ["\n", "\r"]:  # Entrée
            if player_choice == 1:
                Play_Game()
            elif player_choice == 2:
                print("Options coming soon...")
                input("Press Enter...")
            elif player_choice == 3:
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
                from main import terminal_custom
                terminal_custom()
                break
            break
    

        if player_choice != previous_choice:
            afficher_menu(player_choice)
            previous_choice = player_choice


if __name__ == "__main__":
    Menu_Principale()
    