# Cannon Lab

Python (via PyScript/Pyodide) projectile game. Set angle + velocity, launch; paths stay until **Clear all**.

## Run locally
```bash
cd cannon
python -m http.server 8000   # open http://localhost:8000
```
(Must be served over http, not opened as a file.)

## Host free on GitHub Pages
```bash
git init
git add index.html main.py README.md
git commit -m "Cannon Lab"
git branch -M main
git remote add origin https://github.com/<you>/cannon-lab.git
git push -u origin main
```
Then on GitHub: **Settings → Pages → Source: Deploy from branch → main / (root)**.
Your game goes live at `https://<you>.github.io/cannon-lab/`.
