import socket
import threading
import time

def worker(ip, port, stop_time, counter):
    while time.time() < stop_time:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((ip, port))
            s.send(b"PING / HTTP/1.1\r\n\r\n")
            s.close()
            counter['count'] += 1
        except:
            pass

def barre_progression(pourcentage, taille=30):
    remplissage = int(taille * pourcentage / 100)
    vide = taille - remplissage
    return "[" + "█" * remplissage + "░" * vide + f"] {pourcentage:.1f}%"

def run(ip, port=80, duration=10, threads=50):
    """
    Test réseau avec threads, verdict précis et barre visuelle.
    ip : IP cible
    port : port cible (default 80)
    duration : durée en secondes
    threads : nombre de threads
    """
    print(f"[NetStorm] Lancement du test sur {ip}:{port} pendant {duration}s avec {threads} threads")
    stop_time = time.time() + duration
    counter = {'count': 0}

    thread_list = []
    for _ in range(threads):
        t = threading.Thread(target=worker, args=(ip, port, stop_time, counter))
        t.daemon = True
        t.start()
        thread_list.append(t)

    while time.time() < stop_time:
        time.sleep(0.1)

    for t in thread_list:
        t.join(timeout=0.1)

    total_sent = counter['count']
    print(f"[NetStorm] Test terminé : {total_sent} paquets envoyés.")

    seuil_theorique = duration * threads * 10  # cible théorique
    pourcentage = min((total_sent / seuil_theorique) * 100, 100)

    if pourcentage <= 30:
        statut = "Très perturbé"
    elif pourcentage <= 60:
        statut = "Moyennement perturbé"
    elif pourcentage <= 90:
        statut = "Légèrement perturbé"
    else:
        statut = "A bien résisté"

    barre = barre_progression(pourcentage)
    print(f"[NetStorm] Évaluation : {statut} {barre}")
