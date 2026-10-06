# 🎯 Cannon Lab — Projectile Motion on Any Planet

**▶ Play it live: [Cannon Lab](https://biswashk920.github.io/ProjectileMotion/)**

A visual projectile motion simulator. Set the angle and velocity, fire the cannon, and watch the path. Then change the planet and see how gravity changes everything. Python runs right in the browser (PyScript), so there is nothing to install.

## Features

- **Angle and velocity controls**: aim from 0° to 90° at 10–100 m/s.
- **Persistent paths**: each shot leaves a colored trace. Adjust and fire again to compare, and press **Clear all** to wipe the screen.
- **Any planet**: click the planet button to pick a preset (Mercury to Pluto, plus the Moon) or enter your own **mass** and **diameter**. Gravity updates automatically.
- **Rebound mode**: the ball bounces again and again, losing energy each time, until it stops. Tune the bounciness.
- **Moving frame**: the camera follows the ball, so long flights and rolling bounces never leave the screen.
- **Sound**: a boom when the cannon fires and a pop on every bounce (with a mute checkbox).
- **Sim speed slider**: 0.5x to 8x. It adjusts automatically to the planet.
- **Aim guide**: an optional dotted preview of the trajectory.
- **Live stats**: flight time, range, peak height, bounce count and distance.

## The physics

Without air resistance:

| Quantity | Formula |
|---|---|
| Time of flight | `T = 2·v·sin(θ) / g` |
| Range | `R = v²·sin(2θ) / g` |
| Maximum height | `H = (v·sin θ)² / (2g)` |
| Surface gravity | `g = 9.81 × (M / M_Earth) / (D / D_Earth)²` |
| Escape speed | `v_esc = √(2·g·r)` |

Earth reference values: `M = 5.972×10²⁴ kg`, `D = 12,742 km`. A 45° launch gives the longest range on any planet.

Rebounds multiply the vertical speed by the bounciness value on every hit, and a little horizontal speed is lost to ground friction, so the ball always comes to rest.

## Try this

- Fire 45° at 60 m/s on **Earth**, then the **Moon**, then **Jupiter**. Compare the flight times (about 8.7 s, 52 s and 3.3 s).
- Make a custom planet with the same mass as Earth but twice the diameter, and check that gravity drops to a quarter.
- Turn on **Rebound** and **Moving frame**, then fire at 45° and 100 m/s to follow the ball for kilometers.

## Run locally

```bash
git clone https://github.com/biswashk920/ProjectileMotion.git
cd ProjectileMotion
python -m http.server 8000
```

Then open http://localhost:8000. The page must be served over http, because double-clicking `index.html` will not work.

## Files

- `index.html`: page layout, controls and the planet popup
- `main.py`: physics, sound and drawing (runs in the browser via PyScript)

## Hosting

Hosted free on GitHub Pages. Python runs client-side through [PyScript](https://pyscript.net), so no server is needed. Sounds are synthesized by the browser with the Web Audio API, so there are no audio files.