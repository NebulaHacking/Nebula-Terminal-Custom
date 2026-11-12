@echo off
rem Lanceur Nebula : ajoute ce dossier au PATH pour taper "nebula" de n'importe ou.
rem   nebula          lance le terminal
rem   nebula update   met Nebula a jour (git pull)
python "%~dp0launch.py" %*
