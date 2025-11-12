
while True:
    try:

            import os
            import math
            import random
            from colorama import init, Fore, Style
            import socket
            import time
            import keyboard
            import folium
            import Tools.shadowviper
            import pyfiglet
            import unicodedata
            from ToolsFunction import netstorm
            import tkinter as tk
            from tkinter import messagebox
            import traceback
            import sys
            import requests
            from Tools.dirb import dirb
            import platform
            import psutil
            import shutil
            import getpass
            import subprocess
            import NebulaGui.Gui
            from Tools.games.nebulers import Menu_Principale
            import json
            from Tools.ping.ping import run_ping_command
            from Tools.nexariescan import run_scan
            from Tools.blacknova import blacknova
            from Tools.browser.Nebula_browser import browse
            










            init()
            init(autoreset=True)



            history = []
            browser_history = []
            mots_dirb_base = [
                "login", "dashboard", "config", "backup", "admin", "test", "uploads", "images",
                "js", "css", "includes", "api", "server-status", "data", "private", "tmp", "db",
                "old", "dev", "phpmyadmin", "console", "hidden", "auth", "cgi-bin", "panel",
                "webadmin", "setup", "install", "users", "register", "logout", "home", "index",
                "status", "bin", "core", "access", "files", "assets", "secure", "secret", "mail",
                "robots.txt", ".htaccess", ".htpasswd", "sitemap.xml", "logs", "downloads",
                "config.bak", "admin_old", "wordpress", "wp-login", "wp-admin", "site", "beta",
                "staging", "v1", "v2", "debug", "error", "signin", "signup", "rest", "json",
                "xml", "account", "contact", "form", "pay", "payment", "invoice", "api-docs",
                "monitor", "shell", "node_modules", "vendor", "lib", "static", "public", "portal",
                "client", "server", "manager", "sys", "env", "token", "session", "login.php",
                "index.php", "main", "core_old", "vulnerable", "exposed"
            ]


            # Système de fichiers virtuel (Nebula)
            structure = {'/': {'Nebula': {}}}  # racine virtuelle avec dossier Nebula
            current_path = ['/', 'Nebula']  # chemin courant dans le FS virtuel

                    



            def get_ip_info(ip):
                try:
                    res = requests.get(f"http://ip-api.com/json/{ip}").json()
                    if res["status"] == "success":
                        return res
                    else:
                        print(Fore.RED + f"Erreur avec l'IP {ip} : {res.get('message', 'Inconnue')}")
                        return None
                except Exception as e:
                    print(Fore.RED + f"Erreur de requête : {e}")
                    return None
                

            
                





           

            def show_map_with_positions(my_ip, target_ip):
                my_info = get_ip_info(my_ip)
                target_info = get_ip_info(target_ip)
                
                if not my_info or not target_info:
                    print(Fore.RED + "Impossible de récupérer les infos pour une ou plusieurs IP.")
                    return
                
                def print_info(label, info):
                    print(Style.BRIGHT + Fore.GREEN + f"\n=== Infos {label} ===")
                    print(Fore.CYAN + f"IP : {info['query']}")
                    print(Fore.CYAN + f"Pays : {info['country']} ({info['countryCode']})")
                    print(Fore.CYAN + f"Région : {info['regionName']} ({info['region']})")
                    print(Fore.CYAN + f"Ville : {info['city']}")
                    print(Fore.CYAN + f"Code postal : {info['zip']}")
                    print(Fore.CYAN + f"Fournisseur ISP : {info['isp']}")
                    print(Fore.CYAN + f"Organisation : {info.get('org', 'N/A')}")
                    print(Fore.CYAN + f"AS : {info.get('as', 'N/A')}")
                    print(Fore.CYAN + f"Latitude : {info['lat']}")
                    print(Fore.CYAN + f"Longitude : {info['lon']}")
                    print(Fore.CYAN + f"Fuseau horaire : {info.get('timezone', 'N/A')}")
                
                print_info("Utilisateur (Moi)", my_info)
                print_info("Cible", target_info)
                
                avg_lat = (my_info['lat'] + target_info['lat']) / 2
                avg_lon = (my_info['lon'] + target_info['lon']) / 2
                map_world = folium.Map(location=[avg_lat, avg_lon], zoom_start=2)
                
                folium.Marker(
                    location=[my_info['lat'], my_info['lon']],
                    popup=f"Moi : {my_info['query']}\n{my_info['city']}, {my_info['country']}",
                    icon=folium.Icon(color="blue", icon="user")
                ).add_to(map_world)
                
                folium.Marker(
                    location=[target_info['lat'], target_info['lon']],
                    popup=f"Cible : {target_info['query']}\n{target_info['city']}, {target_info['country']}",
                    icon=folium.Icon(color="red", icon="flag")
                ).add_to(map_world)
                
                folium.PolyLine(
                    locations=[[my_info['lat'], my_info['lon']], [target_info['lat'], target_info['lon']]],
                    color="green", weight=2.5, opacity=0.8
                ).add_to(map_world)
                
                map_world.save("ip_positions_map.html")
                print(Fore.YELLOW + "\nCarte interactive sauvegardée sous 'ip_positions_map.html'. Ouvre ce fichier dans un navigateur pour voir la carte.")

            def handle_command(command):
                parts = command.split()
                if len(parts) < 3:
                    print(Fore.RED + "Usage : iptracker -m <IP_cible>")
                    return
                
                if parts[1] == "-m":
                    target_ip = parts[2]
                    try:
                        my_ip = requests.get("https://api.ipify.org").text
                    except Exception as e:
                        print(Fore.RED + f"Erreur en récupérant l'IP publique : {e}")
                        return
                    show_map_with_positions(my_ip, target_ip)
                else:
                    print(Fore.RED + "Option inconnue.")

            # Exemple d'utilisation :
            # handle_command("iptracker -m 8.8.8.8")


            def live_ip_tracker(ip, refresh_delay=None):
                while True:
                    try:
                        data = requests.get(f"http://ip-api.com/json/{ip}").json()
                        if data["status"] == "fail":
                            print(Fore.RED + "IP introuvable.")
                            break
                        
                        print(Style.BRIGHT + Fore.GREEN + f"\n=== Trace IP {ip} ===")
                        print(Fore.CYAN + f"Pays : {data['country']}")
                        print(Fore.CYAN + f"Région : {data['regionName']}")
                        print(Fore.CYAN + f"Ville : {data['city']}")
                        print(Fore.CYAN + f"Fournisseur : {data['isp']}")
                        print(Fore.CYAN + f"Latitude : {data['lat']}, Longitude : {data['lon']}")
                        
                        if refresh_delay is None:
                            # Pas de refresh, on sort de la boucle après la première requête
                            break
                        else:
                            print(Fore.YELLOW + f"(Actualisation dans {refresh_delay}s...)")
                            time.sleep(refresh_delay)

                            if keyboard.is_pressed("q"):
                                print(Fore.RED + "\nTraceur interrompu par l'utilisateur (touche Q).")
                                break
                            
                    except KeyboardInterrupt:
                        print(Fore.RED + "\nTraceur interrompu.")
                        break


            # ----- knano : mini-éditeur pour Nebula terminal -----
            def knano_editor(cmd_parts):
                """
                Usage:
                knano <filename>    -> ouvre/crée filename dans le répertoire courant (virtual FS)
                knano               -> demande un nom de fichier
                Édition:
                Tape du texte : chaque ligne est ajoutée.
                Les commandes commencent par ':' (ex: :w, :q, :wq, :p, :i 3, :d 2, :h)
                """
                # determine filename
                if len(cmd_parts) > 1 and cmd_parts[1].strip():
                    filename = cmd_parts[1].strip()
                else:
                    filename = input("Nom du fichier (relative to current dir): ").strip()
                    if not filename:
                        print("Annulé.")
                        return

                # référence au dossier courant dans le FS virtuel
                dir_ref = get_current_dir()

                # charge contenu existant si présent
                if filename in dir_ref and isinstance(dir_ref[filename], str):
                    lines = dir_ref[filename].splitlines()
                else:
                    lines = []

                modified = False

                def show_help():
                    print("""knano - commandes :
            : w        -> sauvegarder dans le FS virtuel
            : q        -> quitter (refuse si modifs non sauvegardées)
            : wq       -> sauvegarder puis quitter
            : p        -> afficher le fichier avec numéros de lignes
            : i N      -> insérer avant la ligne N (N est un entier, 1-based). Si N>len+1, ajoute à la fin.
            : d N      -> supprimer la ligne N
            : h        -> afficher cette aide
            : r        -> renommer le fichier (demande nouveau nom)
            : esc      -> taper exactement ":q" pour quitter (pas d'autre raccourci)
            """)

                print(f"--- knano: édition de '{filename}' (tape ':h' pour aide) ---")
                # print current content initially (compact)
                if lines:
                    print("[Contenu initial]")
                    for i, l in enumerate(lines, 1):
                        print(f"{i:3}: {l}")
                else:
                    print("[Nouveau fichier vide]")

                while True:
                    try:
                        raw = input()  # lecture ligne par ligne
                    except KeyboardInterrupt:
                        print("\nInterrompu (Ctrl-C). Tape ':q' pour quitter ou ':wq' pour sauvegarder et quitter.")
                        continue

                    if raw.startswith(":"):  # commande spéciale
                        parts = raw[1:].strip().split(" ", 1)
                        cmd = parts[0].lower()

                        if cmd == "w":  # sauvegarder
                            try:
                                dir_ref[filename] = "\n".join(lines)
                                modified = False
                                print(f" -> '{filename}' sauvegardé.")
                            except Exception as e:
                                print("Erreur sauvegarde :", e)

                        elif cmd == "q":
                            if modified:
                                confirm = input("Modifications non sauvegardées, quitter quand même ? (y/N): ").strip().lower()
                                if confirm == "y":
                                    print("Quitte sans sauvegarder.")
                                    return
                                else:
                                    print("Annulé.")
                                    continue
                            else:
                                print("Quitte knano.")
                                return

                        elif cmd == "wq":
                            try:
                                dir_ref[filename] = "\n".join(lines)
                                print(f" -> '{filename}' sauvegardé. Quitte knano.")
                                return
                            except Exception as e:
                                print("Erreur sauvegarde :", e)

                        elif cmd == "p":  # print with numbers
                            print("--- Contenu ---")
                            if lines:
                                for i, l in enumerate(lines, 1):
                                    print(f"{i:3}: {l}")
                            else:
                                print("[fichier vide]")
                            print("---------------")

                        elif cmd == "i":  # insert before N
                            if len(parts) < 2:
                                print("Usage : :i N   (insérer avant la ligne N)")
                                continue
                            try:
                                n = int(parts[1].strip())
                                if n < 1:
                                    n = 1
                                # ask for the line(s) to insert; allow multiple lines ended by a single '.' on a line
                                print("Entrez les lignes à insérer (une par ligne). Tapez une ligne contenant uniquement '.' pour finir.")
                                ins_lines = []
                                while True:
                                    l = input()
                                    if l == ".":
                                        break
                                    ins_lines.append(l)
                                idx = min(n-1, len(lines))
                                for offset, il in enumerate(ins_lines):
                                    lines.insert(idx + offset, il)
                                modified = True
                                print(f"{len(ins_lines)} ligne(s) insérée(s) avant la ligne {n}.")
                            except ValueError:
                                print("N doit être un entier.")

                        elif cmd == "d":  # delete line N
                            if len(parts) < 2:
                                print("Usage : :d N   (supprimer la ligne N)")
                                continue
                            try:
                                n = int(parts[1].strip())
                                if 1 <= n <= len(lines):
                                    removed = lines.pop(n-1)
                                    modified = True
                                    print(f"Ligne {n} supprimée : {removed}")
                                else:
                                    print("Numéro de ligne invalide.")
                            except ValueError:
                                print("N doit être un entier.")

                        elif cmd == "r":  # rename
                            new_name = input("Nouveau nom de fichier : ").strip()
                            if not new_name:
                                print("Nom invalide.")
                                continue
                            # move within current dir_ref
                            if new_name in dir_ref:
                                print("Un fichier ou dossier existe déjà avec ce nom.")
                                continue
                            # write current content to new key and delete old one if existed
                            dir_ref[new_name] = "\n".join(lines)
                            if filename in dir_ref:
                                try:
                                    del dir_ref[filename]
                                except Exception:
                                    pass
                            filename = new_name
                            print(f"Fichier renommé en '{filename}'. (En mémoire, n'oublie pas :w pour sauvegarder definitivement)")

                        elif cmd == "h":
                            show_help()

                        else:
                            print("Commande inconnue. Tape ':h' pour l'aide.")

                    else:
                        # insertion d'une ligne normale à la fin
                        lines.append(raw)
                        modified = True



            os.makedirs("saves", exist_ok=True)

            def cmd_save():
                """Sauvegarde le FS virtuel dans le dossier 'saves'."""
                filename = input("Nom du fichier pour sauvegarde (sans extension): ").strip()
                if not filename:
                    filename = "filesystem_save"
                filepath = os.path.join("saves", filename + ".txt")
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(structure, f, indent=4)
                    print(f"FS sauvegardé dans '{filepath}' !")
                except Exception as e:
                    print("Erreur lors de la sauvegarde :", e)

            def cmd_load():
                """Recharge le FS virtuel depuis le dossier 'saves'."""
                files = [f for f in os.listdir("saves") if f.endswith(".txt")]
                if not files:
                    print("Aucun fichier disponible dans 'saves'.")
                    return

                print("Fichiers disponibles :")
                for i, f in enumerate(files, 1):
                    print(f"{i}. {f}")

                choix = input("Numéro du fichier à charger : ").strip()
                try:
                    index = int(choix) - 1
                    if 0 <= index < len(files):
                        filepath = os.path.join("saves", files[index])
                        global structure, current_path
                        with open(filepath, "r", encoding="utf-8") as f:
                            structure = json.load(f)
                        current_path = ['/', 'Nebula']  # réinitialise le chemin courant
                        print(f"FS rechargé depuis '{filepath}' !")
                    else:
                        print("Choix invalide.")
                except ValueError:
                    print("Veuillez entrer un numéro valide.")
                except Exception as e:
                    print("Erreur lors du chargement :", e)




            def get_current_dir():
                """Retourne le dictionnaire du répertoire actuel."""
                dir_ref = structure['/']
                for folder in current_path[1:]:
                    dir_ref = dir_ref[folder]
                return dir_ref

            def cmd_cd(arg):
                """Change de dossier."""
                global current_path
                if arg == "..":
                    if len(current_path) > 1:
                        current_path.pop()
                elif arg in get_current_dir():
                    if isinstance(get_current_dir()[arg], dict):
                        current_path.append(arg)
                    else:
                        print(f"{arg} n'est pas un dossier.")
                else:
                    print(f"Dossier '{arg}' introuvable.")

            def cmd_mkdir(arg):
                """Crée un nouveau dossier."""
                dir_ref = get_current_dir()
                if arg in dir_ref:
                    print(f"Le dossier '{arg}' existe déjà.")
                else:
                    dir_ref[arg] = {}

            def cmd_ls():
                """Affiche le contenu du dossier actuel."""
                dir_ref = get_current_dir()
                if dir_ref:
                    for item in dir_ref:
                        print(item)
                else:
                    print("Dossier vide.")
            RESET = "\033[0m"
            RED = "\033[91m"
            GREEN = "\033[92m"
            YELLOW = "\033[93m"
            BLUE = "\033[94m"
            zCYAN = "\033[96m"



            def get_prompt():
                """
                Retourne le prompt style Kali Linux colorisé
                - Crochets et parenthèses en vert
                - Texte (host) en bleu
                - Path en vert
                """
                host = "nebula"
                # Reconstruit le chemin virtuel en string
                path_display = "/".join(current_path[1:]) if len(current_path) > 1 else "/"
                if not path_display.startswith("/"):
                    path_display = "/" + path_display

                # Construire le prompt colorisé
                line1 = f"{GREEN}┌──[{RESET}{BLUE}{host}{RESET}{GREEN}]─[{path_display}{GREEN}]{RESET}"
                line2 = f"{GREEN}└──╼{RESET} $ "
                return f"{line1}\n{line2}"


            def get_uptime():
                if platform.system() == "Windows":
                    try:
                        import ctypes
                        import time
                        lib = ctypes.windll.kernel32
                        millis = lib.GetTickCount64()
                        seconds = millis // 1000
                        hours = seconds // 3600
                        minutes = (seconds % 3600) // 60
                        return f"{hours} hours, {minutes} minutes"
                    except:
                        return "Unknown"
                else:
                    try:
                        uptime_seconds = float(os.popen("cat /proc/uptime").read().split()[0])
                        hours = int(uptime_seconds // 3600)
                        minutes = int((uptime_seconds % 3600) // 60)
                        return f"{hours} hours, {minutes} minutes"
                    except:
                        return "Unknown"

            def get_packages():
                if platform.system() == "Linux":
                    try:
                        if shutil.which("dpkg"):
                            return subprocess.check_output("dpkg -l | wc -l", shell=True).decode().strip()
                        elif shutil.which("rpm"):
                            return subprocess.check_output("rpm -qa | wc -l", shell=True).decode().strip()
                        else:
                            return "Unknown"
                    except:
                        return "Unknown"
                else:
                    return "N/A"

            def get_resolution():
                try:
                    if platform.system() == "Windows":
                        import ctypes
                        user32 = ctypes.windll.user32
                        user32.SetProcessDPIAware()
                        width = user32.GetSystemMetrics(0)
                        height = user32.GetSystemMetrics(1)
                        return f"{width}x{height}"
                    else:
                        res = subprocess.check_output("xdpyinfo | grep dimensions", shell=True).decode()
                        return res.split()[1]
                except:
                    return "Unknown"

            def get_gpu():
                try:
                    if platform.system() == "Windows":
                        # Simple detection via wmic
                        gpu = subprocess.check_output("wmic path win32_VideoController get name", shell=True).decode().strip().split("\n")[1]
                        return gpu
                    else:
                        gpu = subprocess.check_output("lspci | grep -i 'vga'", shell=True).decode().strip()
                        return gpu
                except:
                    return "Unknown"

            def show_nebula():
                # Couleurs ANSI
                
                # Logo ASCII "N"
                nebula_logo = [
                    f"",
                    f"",
                    f"{GREEN} /$$   /$${RESET}          ",
                    f"{GREEN}| $$$ | $${RESET}          ",
                    f"{GREEN}| $$$$| $${RESET}          ",
                    f"{GREEN}| $$ $$ $${RESET}          ",
                    f"{GREEN}| $$  $$$${RESET}          ",
                    f"{GREEN}| $$\\  $$${RESET}          ",
                    f"{GREEN}| $$ \\  $${RESET}          ",
                    f"{GREEN}|__/  \\__/ebula{RESET}     ",
                    f"",
                    "",
                    ""
                ]

                # Infos système
                user = getpass.getuser()
                host = socket.gethostname()
                os_info = f"{platform.system()} {platform.release()}"
                kernel = platform.version()
                uptime = get_uptime()
                packages = get_packages()
                shell = os.environ.get("SHELL") if platform.system() != "Windows" else os.environ.get("COMSPEC", "cmd.exe")
                resolution = get_resolution()
                terminal = os.environ.get("TERM", "Unknown") if platform.system() != "Windows" else "cmd.exe/PowerShell"
                cpu = platform.processor()
                gpu = get_gpu()
                memory = f"{round(psutil.virtual_memory().total / (1024**3))}GB"

                info_labels = [
                    "User:", "OS:", "Kernel:", "Uptime:", "Packages:",
                    "Shell:", "Resolution:", "Terminal:", "CPU:", "GPU:", "Memory:"
                ]

                info_values = [
                    f"{user}@{host}", os_info, kernel, uptime, packages,
                    shell, resolution, terminal, cpu, gpu, memory
                ]

                # Alignement
                max_lines = max(len(nebula_logo), len(info_labels))
                while len(nebula_logo) < max_lines:
                    nebula_logo.append("")
                while len(info_labels) < max_lines:
                    info_labels.append("")
                while len(info_values) < max_lines:
                    info_values.append("")

                # Affichage
                for i in range(max_lines):
                    logo_part = nebula_logo[i]
                    label = info_labels[i]
                    value = info_values[i]
                    print(f"{logo_part:<20} {BLUE}{label:<12}{RESET} {GREEN}{value}{RESET}")



            def affichage_nebula():
                nebula_ascii = r"""
            
                        _____                    _____                    _____                    _____                    _____            _____          
                    /\    \                  /\    \                  /\    \                  /\    \                  /\    \          /\    \         
                    /::\____\                /::\    \                /::\    \                /::\____\                /::\____\        /::\    \        
                    /::::|   |               /::::\    \              /::::\    \              /:::/    /               /:::/    /       /::::\    \       
                    /:::::|   |              /::::::\    \            /::::::\    \            /:::/    /               /:::/    /       /::::::\    \      
                /::::::|   |             /:::/\:::\    \          /:::/\:::\    \          /:::/    /               /:::/    /       /:::/\:::\    \     
                /:::/|::|   |            /:::/__\:::\    \        /:::/__\:::\    \        /:::/    /               /:::/    /       /:::/__\:::\    \    
                /:::/ |::|   |           /::::\   \:::\    \      /::::\   \:::\    \      /:::/    /               /:::/    /       /::::\   \:::\    \   
                /:::/  |::|   | _____    /::::::\   \:::\    \    /::::::\   \:::\    \    /:::/    /      _____    /:::/    /       /::::::\   \:::\    \  
            /:::/   |::|   |/\    \  /:::/\:::\   \:::\    \  /:::/\:::\   \:::\ ___\  /:::/____/      /\    \  /:::/    /       /:::/\:::\   \:::\    \ 
            /:: /    |::|   /::\____\/:::/__\:::\   \:::\____\/:::/__\:::\   \:::|    ||:::|    /      /::\____\/:::/____/       /:::/  \:::\   \:::\____\
            \::/    /|::|  /:::/    /\:::\   \:::\   \::/    /\:::\   \:::\  /:::|____||:::|____\     /:::/    /\:::\    \       \::/    \:::\  /:::/    /
            \/____/ |::| /:::/    /  \:::\   \:::\   \/____/  \:::\   \:::\/:::/    /  \:::\    \   /:::/    /  \:::\    \       \/____/ \:::\/:::/    / 
                    |::|/:::/    /    \:::\   \:::\    \       \:::\   \::::::/    /    \:::\    \ /:::/    /    \:::\    \               \::::::/    /  
                    |::::::/    /      \:::\   \:::\____\       \:::\   \::::/    /      \:::\    /:::/    /      \:::\    \               \::::/    /   
                    |:::::/    /        \:::\   \::/    /        \:::\  /:::/    /        \:::\__/:::/    /        \:::\    \              /:::/    /    
                    |::::/    /          \:::\   \/____/          \:::\/:::/    /          \::::::::/    /          \:::\    \            /:::/    /     
                    /:::/    /            \:::\    \               \::::::/    /            \::::::/    /            \:::\    \          /:::/    /      
                    /:::/    /              \:::\____\               \::::/    /              \::::/    /              \:::\____\        /:::/    /       
                    \::/    /                \::/    /                \::/____/                \::/____/                \::/    /        \::/    /        
                    \/____/                  \/____/                  ~~                       ~~                       \/____/          \/____/         
                                                                                                                                                                                                                                                    
                """
                print(Fore.LIGHTRED_EX + nebula_ascii)



            def affichage_scan():
                scan_ascii = r"""                                                  
                    ______        _____         _____  _____   ______   
                ___|\     \   ___|\    \    ___|\    \|\    \ |\     \  
                |    |\     \ /    /\    \  /    /\    \\\    \| \     \ 
                |    |/____/||    |  |    ||    |  |    |\|    \  \     |
            ___|    \|   | ||    |  |____||    |__|    | |     \  |    |
            |    \    \___|/ |    |   ____ |    .--.    | |      \ |    |
            |    |\     \    |    |  |    ||    |  |    | |    |\ \|    |
            |\ ___\|_____|   |\ ___\/    /||____|  |____| |____||\_____/|
            | |    |     |   | |   /____/ ||    |  |    | |    |/ \|   ||
            \|____|_____|    \|___|    | /|____|  |____| |____|   |___|/
                \(    )/        \( |____|/   \(      )/     \(       )/  
                '    '          '   )/       '      '       '       '   
                                    '                                                                                                                                                                                                                                                           
                """
                print(Fore.WHITE + scan_ascii)

            def execute_command_real(cmd):
                try:
                    # Exécute la commande et récupère la sortie
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    # Affiche la sortie
                    if result.stdout:
                        print(result.stdout)
                    if result.stderr:
                        print(result.stderr)
                except Exception as e:
                    print("Erreur :", e)

            def calculatrice():
                print("Mode Calculatrice : tapez une expression mathématique ou 'exit' pour revenir.")
                while True:
                    expr = input("calc> ").strip()
                    if expr.lower() == "exit":
                        print("Sortie du mode calculatrice.")
                        break
                    try:
                        expr = expr.replace("sqrt", "math.sqrt")
                        resultat = eval(expr, {"__builtins__": None, "math": math})
                        print("Résultat :", resultat)
                    except Exception as e:
                        print("Erreur :", e)

            def enlever_accents(texte):
                # Supprime uniquement les accents
                texte = unicodedata.normalize('NFD', texte)
                return ''.join(c for c in texte if unicodedata.category(c) != 'Mn')

            def terminal_custom():
                show_nebula()
                while True:

                    
                    cmd = input(get_prompt()).strip()
                    
                
                    commande = cmd
                    parts = commande.split()
                    commande = parts[0]
                    
                    if cmd == "exit": # Exit the terminal
                        history.append(cmd)
                        print("Fermeture du terminal.")
                        exit()
                        quit()
                    elif cmd == "clear":
                        history.append(cmd)
                        os.system("cls" if os.name == "nt" else "clear")
                    elif cmd == "nebulers":
                        history.append(cmd)
                        Menu_Principale()
                    elif cmd =="nebulaGui":
                        history.append(cmd)
                        NebulaGui.Gui.launch_nebula_gui()
                    elif cmd == "help":  # liste les commandes
                        history.append(cmd)
                        print("Commandes disponibles :\n")
                        print("  calc             - Lancer la calculatrice")
                        print("  ls               - Lister le contenu du dossier actuel")
                        print("  mkdir <nom>      - Créer un dossier")
                        print("  cd ..            - Revenir au dossier précédent")
                        print("  cd <nom>         - Entrer dans un dossier")
                        print("  color 2          - Changer la couleur en vert (Windows)")
                        print("  color 3          - Changer la couleur en cyan (Windows)")
                        print("  color 4          - Changer la couleur en rouge (Windows)")
                        print("  color 0          - Réinitialiser la couleur (Windows)")
                        print("  exit             - Quitter le terminal")
                        print("  rand <a> <b>     - Générer un nombre aléatoire entre a et b")
                        print("  history          - Afficher l'historique des commandes")
                        print("  scan <ip>        - Analyse des ports ouverts d’une IP")
                        print("  time             - Afficher l'heure actuelle en ASCII")
                        print("  weather          - Afficher la météo d'une ville")
                        print("  tools            - Liste des outils disponibles")
                        print("  save             - Sauvegarder le système de fichiers virtuel")
                        print("  load             - Charger un système de fichiers sauvegardé")
                        print("  knano <fichier>  - Mini éditeur de texte (voir knano.help)")
                        print("  nebulers         - Lancer le jeu Nebulers")
                        print("  nebulaGui        - Lancer l'interface graphique Nebula")
                        print("  kcat <fichier>   - Afficher le contenu d'un fichier du FS virtuel")
                        print("  k3d              - Fonction 3D en développement")
                        print("  nexariscan       - Lancer le scan Nexari (XSS & liens)")
                        print("  ping <ip/url>    - Ping d'une IP ou URL")
                        print("  nebula_ascii     - Afficher l'ASCII art Nebula")
                        print("  iptracker <opt> <ip> - Tracker IP avec options")
                        print("  rm               - Passe un mode réel sur la machine")
                        print("  [tool].help      - Affiche l'utilisation de l'outil ")
                        print("  blackledger      - Créateur de wordslist grace a ia")
                        print("  browser          - navigateur web nebula sécurisé (run as non root)")

                    elif cmd == "scan.help":
                        history.append(cmd)
                        print(" -- Scan v1.0 --\n")
                        print("Syntaxe :")
                        print("   -f [IP]  : analyse rapide des ports")
                        print("   -a [IP]  : analyse de tous les ports")
                        print("   -s [IP]  : analyse discrète des ports\n")
                        print("Hotkeys :")
                        print("   q        - Stop scan")
                        print("   r        - Statistiques restantes")

                    elif cmd == "dirb.help":
                        history.append(cmd)
                        print(" -- Dirb v1.0 --\n")
                        print("Hotkeys :")
                        print("   q        - Stop scan")
                        print("   r        - Stats restantes\n")
                        print("Options :")
                        print("   -w [wordlist] : fichier de mots")
                        print("   -m [minimal]  : mode minimal (10 mots testés)\n")
                        print("Exemple :")
                        print("   dirb -w wordlist.txt https://example.com")

                    elif cmd == "iptracker.help":
                        history.append(cmd)
                        print(" -- IPTracker v1.0 --\n")
                        print("Hotkeys :")
                        print("   q        - Stop track\n")
                        print("Options :")
                        print("   -c [IP]  : scan continu")
                        print("   -m [IP]  : affiche une carte avec infos IP cible et utilisateur")

                    elif cmd == "shadowviper.help":
                        history.append(cmd)
                        print("ShadowViper v1.0")
                        print("By Ma4g\n")
                        print("Usage :")
                        print("   shadowviper [paramètre] <cible>\n")
                        print("Notes :")
                        print("   ShadowViper est un outil avancé de collecte d'informations et d'analyse de vulnérabilités.")
                        print("   Utilisation responsable recommandée.\n")
                        print("Hotkeys :")
                        print("   q        - Quitter")
                        print("   h        - Help")
                        print("   r        - Stats restantes")
                        print("   s        - Sauvegarder les stats\n")
                        print("Options :")
                        print("   (à remplir selon les fonctionnalités ajoutées)\n")
                        print("Exemples :")
                        print("   shadowviper -scan 192.168.0.1")

                    elif cmd == "knano.help":
                        history.append(cmd)
                        print("knano - Mini éditeur pour FS virtuel\n")
                        print("Commandes :")
                        print("   :w       - Sauvegarder")
                        print("   :q       - Quitter (refuse si non sauvegardé)")
                        print("   :wq      - Sauvegarder puis quitter")
                        print("   :p       - Afficher contenu avec numéros de lignes")
                        print("   :i N     - Insérer avant la ligne N")
                        print("   :d N     - Supprimer la ligne N")
                        print("   :h       - Afficher cette aide")
                        print("   :r       - Renommer le fichier")
                    elif cmd == "blacknova.help":
                        history.append(cmd)
                        print(" -- BlackNova v1.0 --")
                        print("")
                        print("Moteur multi-attaque simulé pour analyse de vulnérabilités (éducatif).")
                        print("")
                        print("Usage : blacknova <IP / Domaine>")
                        print("")
                        print("======================= HOTKEYS ======================")
                        print("")
                        print("  'q' -> Quitter l'analyse")
                        print("  'r' -> Rafraîchir le rapport")
                        print("  's' -> Sauvegarder le rapport")
                        print("")
                        print("======================= OPTIONS ======================")
                        print("")
                        print("  -f [IP]    : scan rapide")
                        print("  -a [IP]    : scan complet")
                        print("  -e [exploit] : tentative d'exploitation simulée")
                        print("")
                        print("====================== EXEMPLES =====================")
                        print("")
                        print("blacknova 192.168.0.10")
                        print("blacknova example.com -f")
                        print("blacknova 10.0.0.5 -a -e ftp")
                        print("")
                        print("Note : Cet outil est une simulation éducative, toutes les attaques sont fictives.")
                                
                                

                    elif cmd == "save":
                        history.append(cmd)
                        cmd_save()

                    elif cmd == "load":
                        history.append(cmd)
                        cmd_load()

                    elif cmd == "blackledger":
                        from Tools.BlackLedger.BlackLedger import generate_wordlist, WordlistConfig

                        print("\n=== BlackLedger Wordlist Generator ===")
                        print("Veuillez entrer les informations pour générer la wordlist.\n")

                        # Collecte interactive des inputs
                        inputs = {
                            "url": input("URL du site (laisser vide si aucun) : ").strip(),
                            "domain": input("Nom de domaine (ex: example.com) : ").strip(),
                            "title": input("Titre ou nom du projet : ").strip(),
                            "company": input("Nom de l'entreprise ou team : ").strip(),
                            "keywords": input("Mots-clés séparés par des espaces : ").strip(),
                            "location": input("Lieu (ville/pays) : ").strip(),
                            "user": input("Nom d'utilisateur ou handle : ").strip(),
                            "events": input("Événements ou dates (ex: launch2025, winter) : ").strip(),
                            "base": input("Terme de base (ex: Nebula, BlackLedger) : ").strip()
                        }

                        # Termes supplémentaires
                        extra_terms = input("Termes supplémentaires (séparés par des espaces) : ").split()

                        # Configuration
                        cfg = WordlistConfig(
                            max_words=20000,
                            max_depth=3,
                            leet_levels=2,
                            seed=1337
                        )

                        # Génération
                        wordlist = generate_wordlist(inputs, extra_terms=extra_terms, config=cfg)

                        # Demande du chemin de sauvegarde
                        save_path = input("Chemin complet pour sauvegarder la wordlist (ex: ./Tools/BlackLedger/wordlists/wordlists.txt) : ").strip()
                        if not save_path:
                            save_path = "wordlist.txt"  # valeur par défaut

                        with open(save_path, "w", encoding="utf-8") as f:
                            for w in wordlist:
                                f.write(w + "\n")

                        print(f"\n✅ Wordlist générée avec {len(wordlist)} mots et sauvegardée dans : {save_path}")


                    elif cmd == "calc": #calculatrice
                        history.append(cmd)
                        calculatrice()

                    elif parts[0] == "knano":
                        history.append(cmd)
                        knano_editor(parts)

                    elif cmd.startswith("ping"):
                        run_ping_command(cmd)

                    elif parts[0] == "kcat":
                        if len(parts) < 2:
                            print("Usage: kcat <fichier>")
                        else:
                            filename = parts[1]
                            dir_ref = get_current_dir()
                            if filename in dir_ref and isinstance(dir_ref[filename], str):
                                print(dir_ref[filename])
                            else:
                                print(f"Erreur : le fichier '{filename}' n'existe pas.")
                        
                    elif parts[0] == "k3d":
                        print("sa marhce pas encor patiente !")

                    elif cmd == "weather":
                        ville = input("Ville : ")
                        url = f"https://wttr.in/{ville}?0"  # "?0" = version compacte
                        try:
                            print(requests.get(url).text)
                        except:
                            print("Erreur : impossible de récupérer la météo.")

                    elif cmd == "time":  #afficher l'heure
                        heure = time.strftime("%H:%M:%S")
                        ascii_heure = pyfiglet.figlet_format(heure)
                        print(ascii_heure, end="")

                    elif cmd == "tools":
                        with open("txt.help.folder/Tools.txt", "rb") as f:  # lecture binaire
                            raw_bytes = f.read()

                        try:
                            # Essaye UTF-8 en premier
                            raw = raw_bytes.decode("utf-8")
                        except UnicodeDecodeError:
                            # Si ça plante, tente Latin-1 puis re-décode en UTF-8
                            raw = raw_bytes.decode("latin-1").encode("utf-8").decode("utf-8")

                        # Corrige les accents mal affichés (cas UTF8 lu en Latin-1)
                        try:
                            raw = raw.encode("latin-1").decode("utf-8")
                        except UnicodeEncodeError:
                            pass  # pas besoin si déjà correct

                        # Enlève accents si nécessaire
                        raw = enlever_accents(raw)

                        # Transforme les séquences \033 en vraies séquences ANSI
                        fixed = raw.replace("\\033", "\x1b")

                        print(fixed)








                    elif cmd == "ls": #lister le contenu du dossier actuel
                        history.append(cmd)
                        cmd_ls()


                    elif cmd.startswith("mkdir "): #créer un dossier
                        history.append(cmd)
                        cmd_mkdir(cmd[6:].strip())


                    elif cmd.startswith("cd "): #choisir un dossier
                        history.append(cmd)
                        cmd_cd(cmd[3:].strip())


                    elif cmd == "cd ..": #revenir au dossier précédent
                        history.append(cmd)
                        cmd_cd("..")


                    elif cmd == "color 2": #changer la couleur en vert
                        history.append(cmd)
                        os.system("color 2")

                    elif cmd == "color 3": #changer la couleur en vert
                        
                        history.append(cmd)
                        os.system("color 3")


                    elif cmd == "color 4": #changer la couleur en rouge
                        history.append(cmd)
                        os.system("color 4")

                    


                    elif cmd == "color 0": #changer la couleur en blanc
                        history.append(cmd)
                        os.system("color 0")

                    elif cmd == "browser":
                        history.append(cmd)
                        print("==== Nebula Secure Browser ====")
                        print("========= Version 1.0 =========")
                        print("")
                        url_choice = input("URL : ")
                        browser_history.append(url_choice)

                        try:
                            browse(url_choice)
                        except:
                            print("url invalide")

                    elif cmd == "browser.history":
                        print(browser_history)


                    elif cmd == "nebula_ascii": #afficher l'ascii art de nebula
                        history.append(cmd)
                        affichage_nebula()

                    elif cmd == "nexariscan":
                        target = input("URL cible (ex: https://example.com) : ").strip()
                        delay = input("Delay entre requêtes (default 0.5s) : ").strip()
                        delay = float(delay) if delay else 0.5

                        print(f"Lancement du scan Nexari sur {target}...")
                        results = run_scan(target, delay=delay, verbose=True, safe_only=True)

                        print("\n=== Résumé du scan ===")
                        print("Liens trouvés :", results.get('links_found'))
                        print("Tests de liens effectués :", results.get('tested_links_count'))
                        print("Tests de formulaires effectués :", results.get('tested_forms_count'))
                        print("XSS détectés dans les liens :", len(results.get('xss_in_links', [])))
                        for l in results.get('xss_in_links', []):
                            print(" ->", l)
                        print("XSS détectés dans les formulaires :", len(results.get('xss_in_forms', [])))
                        for f in results.get('xss_in_forms', []):
                            print(" -> page:", f['page'], " action:", f['form_action'])



                    elif cmd.startswith("rand"): #générer un nombre aléatoire
                        history.append(cmd)
                        parts = cmd.split()
                        min_val = int(parts[1])
                        max_val = int(parts[2])
                        print(random.randint(min_val, max_val))


                    elif cmd == "history": #afficher l'historique des commandes
                        history.append(cmd)
                        print(history)

                    elif cmd.startswith("blacknova"):
                        history.append(cmd)
                        parts = cmd.split()
                        if len(parts) >= 2:
                            cible = parts[1]
                            options = []
                            exploits = []
                            skip_next = False
                            for i in range(2, len(parts)):
                                if skip_next:
                                    skip_next = False
                                    continue
                                if parts[i].startswith("-"):
                                    if parts[i] in ["-f", "-a"]:
                                        options.append(parts[i])
                                    elif parts[i] == "-e" and i+1 < len(parts):
                                        exploits.append(parts[i+1])
                                        skip_next = True
                            blacknova(cible, options, exploits)
                        else:
                            print("Usage : blacknova <IP / Domaine> [-f|-a] [-e exploit1 exploit2...]")


                    elif cmd.startswith("netstorm"):    #netstorm
                        demande_légal = input("Cet outil peut être dangereux voulez vous continuer (y/n) ? ")
                        if demande_légal == "y":
                            args = cmd.split()
                            if len(args) >= 2:
                                ip = args[1]
                                port = int(args[2]) if len(args) >= 3 else 80
                                duration = int(args[3]) if len(args) >= 4 else 10
                                threads = int(args[4]) if len(args) >= 5 else 50
                                netstorm.run(ip, port, duration, threads)
                            else:
                                print("Utilisation : netstorm <IP> [PORT] [DUREE] [THREADS]")
                        

                    elif parts[0] == "rm":
                        if len(parts) > 1:
                            history.append(cmd)
                            print("Passage en mode réel")
                            commande = " ".join(parts[1:])   # ✅ Recolle tout ce qui vient après 'rm'
                            execute_command_real(commande)
                        else:
                            print("Syntaxe => rm 'commande'")





                    elif parts[0] == "iptracker": #ip tracker
                        if parts[1] == "-c":
                            history.append(cmd)
                            live_ip_tracker(parts[2], 3)
                        elif parts[1] == "-m":
                            history.append(cmd)
                            import requests
                            my_ip = requests.get("https://api.ipify.org").text
                            target_ip = parts[2]
                            show_map_with_positions(my_ip, target_ip)
                        else:
                            history.append(cmd)
                            live_ip_tracker(parts[1])



                    elif parts[0] == "shadowviper": #shadowviper
                        if len(parts) > 1:
                            # Si tu passes un argument direct, tu peux l’envoyer
                            Tools.shadowviper.run_shadowviper(parts[1])
                        else:
                            # Sinon, demande à l’utilisateur
                            user_input = input("shadowviper > Entrez une IP, domaine, URL, ASN ou email : ").strip()
                            Tools.shadowviper.run_shadowviper(user_input)




                    elif cmd == "dirb":
                        print("lunch dirb.help for having help")
                
                    elif parts[0] == "dirb":
                        if parts[1] == "-w":
                            url = parts[2]
                            wordlist = parts[3]
                            resultats = dirb(url, wordlist=wordlist, minimal=False)
                        elif parts[1] == "-m":
                            url = parts[2]
                            resultats = dirb(url, wordlist=None, minimal=True)
                        else:
                            url = parts[1]
                            resultats = dirb(url)



                    elif parts[0] == "scan": #outils de scan de ports
                        history.append(commande)
                        affichage_scan()


                        if len(parts) > 1:

                            if parts[1] == "-f": #scan rapide
                                if len(parts) < 2:
                                    print("Utilisation : scan [paramètre] <adresse_ip> [port_min] [port_max]")
                                else:
                                    host = parts[2]
                                    port_min = int(parts[3]) if len(parts) > 3 else 1
                                    port_max = int(parts[4]) if len(parts) > 4 else 1024

                                    print(f"Scan des ports de {host} ({port_min}-{port_max})...")
                                    start_time = time.time()

                                    for port in range(port_min, port_max + 1):
                                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                        s.settimeout(0.01)  # temps d'attente pour chaque port
                                        result = s.connect_ex((host, port))
                                        if result == 0:
                                            print(f"Port {port} ouvert")
                                        s.close()
                                    duration = time.time() - start_time
                                    print(f"Scan terminé en {duration:.2f} secondes.")




                            elif parts[1] == "-a": #scan tout les ports
                                if len(parts) < 2:
                                    print("Utilisation : scan [paramètre] <adresse_ip> [port_min] [port_max]")
                                else:
                                    host = parts[2]
                                    port_min = 1
                                    port_max = 65535

                                    print(f"Scan des ports de {host} ({port_min}-{port_max})...")
                                    start_time = time.time()

                                    for port in range(port_min, port_max + 1):
                                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                        s.settimeout(0.3)  # temps d'attente pour chaque port
                                        result = s.connect_ex((host, port))
                                        if result == 0:
                                            print(f"Port {port} ouvert")
                                        s.close()
                                    duration = time.time() - start_time
                                    print(f"Scan terminé en {duration:.2f} secondes.")



                            elif parts[1] == "-s":
                                if len(parts) < 2:
                                    print("Utilisation : scan [paramètre] <adresse_ip> [port_min] [port_max]")
                                else:
                                    host = parts[2]
                                    port_min = 1
                                    port_max = 256
                                    nombreDeScan = 1

                                    for i in range(4):
                                        print(f"Scan des ports de {host} ({port_min}-{port_max})...")
                                        start_time = time.time()

                                        for port in range(port_min, port_max + 1):
                                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                            s.settimeout(0.1)  # temps d'attente pour chaque port
                                            result = s.connect_ex((host, port))
                                            if result == 0:
                                                print(f"Port {port} ouvert")
                                            s.close()
                                        duration = time.time() - start_time
                                        print(f"Scan {nombreDeScan} terminé en {duration:.2f} secondes.")
                                        nombreDeScan += 1
                                        port_max += 256
                                        port_min += 256




                            else: #scan noraml
                                if len(parts) < 2:
                                    print("Utilisation : scan [paramètre] <adresse_ip> [port_min] [port_max]")
                                else:
                                    host = parts[1]
                                    port_min = int(parts[2]) if len(parts) > 2 else 1
                                    port_max = int(parts[3]) if len(parts) > 3 else 1024

                                    print(f"Scan des ports de {host} ({port_min}-{port_max})...")
                                    start_time = time.time()
                                    for port in range(port_min, port_max + 1):
                                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                        s.settimeout(0.3)  # temps d'attente pour chaque port
                                        result = s.connect_ex((host, port))
                                        if result == 0:
                                            print(f"Port {port} ouvert")
                                        s.close()
                                    duration = time.time() - start_time
                                    print(f"Scan terminé en {duration:.2f} secondes.")




                    else: #aucune commande reconnue
                        print(f"Commande inconnue : {cmd}. Tapez 'help' pour voir les commandes.")

            if __name__ == "__main__":
                terminal_custom()

    except Exception as e:
            print("Une erreur est survenue :", e)


