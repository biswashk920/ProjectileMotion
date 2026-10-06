# 🎯 Cannon Lab — Projectile Motion Simulator

**▶ Play it live: [Cannon Lab](https://biswashk920.github.io/ProjectileMotion/)**

A simple, visual projectile motion simulator for kids and students. Set the angle and velocity, fire the cannon, and compare your results with your notebook answers. Built with Python running in the browser (PyScript), so there is nothing to install.

## Features

- **Angle and velocity controls**: aim anywhere from 0° to 90° at 10–100 m/s.
- **Persistent paths**: every shot leaves a colored trace, so you can adjust and fire again to compare. Press **Clear all** to wipe the screen.
- **Real-time physics**: flight time, range and peak height are shown for each shot.
- **Rebound mode**: the ball bounces again and again, losing energy each time, until it stops. Adjust the bounciness slider.
- **Moving frame**: the camera follows the ball, so long flights and rolling bounces never leave the screen.
- **Sim speed slider**: slow things down or speed them up (0.5x to 8x).
- **Aim guide**: an optional dotted preview of the trajectory.

## The physics

Without air resistance:

| Quantity | Formula |
|---|---|
| Time of flight | `T = 2·v·sin(θ) / g` |
| Range | `R = v²·sin(2θ) / g` |
| Maximum height | `H = (v·sin θ)² / (2g)` |

with `g = 9.81 m/s²`. A 45° launch gives the longest range.

## Run locally

```bash
git clone https://github.com/biswashk920/ProjectileMotion.git
cd ProjectileMotion
python -m http.server 8000
```

Then open http://localhost:8000. The page must be served over http (double-clicking `index.html` will not work).

## Files

- `index.html`: page layout and controls
- `main.py`: physics and drawing (runs in the browser via PyScript)

## Hosting

Hosted free on GitHub Pages. Python runs client-side through [PyScript](https://pyscript.net), so no server is needed.
