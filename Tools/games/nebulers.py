import os
import time
import keyboard
import random

# -------- CONFIG --------
SCREEN_W = 60
SCREEN_H = 20
WORLD_W = 200
FPS = 25

# -------- GRAPHISMES --------
BLOCK = "█"
BRICK = "▓"
SPIKE = "▲"
PLAYER = "◉"
ENEMY = "◆"
COIN = "●"
EMPTY = " "

RESET = "\033[0m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"

# -------- UTIL --------
def clear():
    os.system("cls" if os.name == "nt" else "clear")

# -------- MONDE --------
world = [[0 for _ in range(WORLD_W)] for _ in range(SCREEN_H)]

# Sol
for x in range(WORLD_W):
    world[SCREEN_H-1][x] = 1

# Génération procédurale de plateformes
for i in range(10):
    start = random.randint(5, WORLD_W-20)
    length = random.randint(6, 14)
    height = random.randint(6, SCREEN_H-5)

    for x in range(start, start + length):
        world[height][x] = 1

# Ajout de pics dangereux
spikes = []
for _ in range(25):
    x = random.randint(10, WORLD_W-10)
    spikes.append((x, SCREEN_H-2))

# Pièces
coins = []
for _ in range(30):
    x = random.randint(5, WORLD_W-5)
    y = random.randint(3, SCREEN_H-5)
    coins.append([x, y])

# Ennemis
enemies = []
for _ in range(10):
    x = random.randint(10, WORLD_W-10)
    enemies.append({
        "x": x,
        "y": SCREEN_H-2,
        "dir": random.choice([-1, 1])
    })

# -------- JOUEUR --------
player = {
    "x": 3,
    "y": SCREEN_H-2,
    "vy": 0,
    "jumps": 0,
    "coins": 0,
    "dead": False
}

GRAVITY = 1
JUMP = -4
MAX_JUMPS = 2

camera_x = 0

# -------- FONCTIONS --------

def collision(x, y):
    if x < 0 or x >= WORLD_W or y < 0 or y >= SCREEN_H:
        return True
    return world[y][x] == 1

def draw():
    global camera_x

    camera_x = max(0, player["x"] - SCREEN_W // 2)
    camera_x = min(camera_x, WORLD_W - SCREEN_W)

    clear()
    print(MAGENTA + "=== NEON RUNNER ===" + RESET)
    print(f"Coins: {player['coins']}")

    for y in range(SCREEN_H):
        line = ""

        for x in range(camera_x, camera_x + SCREEN_W):
            char = EMPTY

            if x == player["x"] and y == player["y"]:
                char = YELLOW + PLAYER + RESET

            elif (x, y) in spikes:
                char = RED + SPIKE + RESET

            elif [x, y] in coins:
                char = CYAN + COIN + RESET

            else:
                for e in enemies:
                    if e["x"] == x and e["y"] == y:
                        char = RED + ENEMY + RESET
                        break
                else:
                    if world[y][x] == 1:
                        char = GREEN + BRICK + RESET

            line += char

        print(line)

    print("\nAWDS pour bouger | Double saut actif | Q pour quitter")

def handle_input():
    if keyboard.is_pressed("a"):
        if not collision(player["x"] - 1, player["y"]):
            player["x"] -= 1

    if keyboard.is_pressed("d"):
        if not collision(player["x"] + 1, player["y"]):
            player["x"] += 1

    if keyboard.is_pressed("w"):
        if player["jumps"] < MAX_JUMPS:
            player["vy"] = JUMP
            player["jumps"] += 1
            time.sleep(0.1)

def physics():
    player["vy"] += GRAVITY

    new_y = player["y"] + player["vy"]

    if player["vy"] > 0:
        for y in range(player["y"], new_y + 1):
            if collision(player["x"], y):
                player["y"] = y - 1
                player["vy"] = 0
                player["jumps"] = 0
                break
        else:
            player["y"] = new_y

    elif player["vy"] < 0:
        for y in range(player["y"], new_y - 1, -1):
            if collision(player["x"], y):
                player["y"] = y + 1
                player["vy"] = 0
                break
        else:
            player["y"] = new_y

def update_gameplay():
    for coin in coins[:]:
        if coin[0] == player["x"] and coin[1] == player["y"]:
            coins.remove(coin)
            player["coins"] += 1

    for sx, sy in spikes:
        if player["x"] == sx and player["y"] == sy:
            player["dead"] = True

    for e in enemies:
        e["x"] += e["dir"]

        if collision(e["x"] + e["dir"], e["y"]):
            e["dir"] *= -1

        if e["x"] == player["x"] and e["y"] == player["y"]:
            player["dead"] = True

def game_loop():
    while True:
        start = time.time()

        if keyboard.is_pressed("q"):
            break

        handle_input()
        physics()
        update_gameplay()
        draw()

        if player["dead"]:
            clear()
            print(RED + "GAME OVER" + RESET)
            print(f"Coins ramassées: {player['coins']}")
            break

        if player["x"] >= WORLD_W - 2:
            clear()
            print(GREEN + "VICTOIRE !" + RESET)
            print(f"Coins: {player['coins']}")
            break

        elapsed = time.time() - start
        time.sleep(max(0, 1/FPS - elapsed))

# -------- LANCEMENT --------
def Menu_Principale():
    clear()
    print("Chargement du monde néon...")
    time.sleep(1)
    game_loop()
