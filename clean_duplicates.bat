@echo off
del "entities (1).py" 2>nul
del "files (1).zip" 2>nul
del "files (2).zip" 2>nul
del "README (1).md" 2>nul
del "ui (1).py" 2>nul
del "ui (2).py" 2>nul
del "cleanup.py" 2>nul
echo All duplicate files removed!
del "%~f0" 2>nul
