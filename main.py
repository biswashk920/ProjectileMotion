import math
from pyscript import document, window
from pyodide.ffi import create_proxy, to_js

canvas = document.getElementById("c")
ctx = canvas.getContext("2d")
W, H = canvas.width, canvas.height

G = 9.81
SCALE = 0.8          # pixels per metre
GROUND = 60
OX, OY = 60, H - GROUND
DT = 1 / 240         # physics step (s)
FRICTION = 0.90      # horizontal speed kept after each ground bounce
STOP_VY = 1.2        # below this bounce speed the ball rests
XMAX = (W - OX - 8) / SCALE    # walls (static frame + rebound only)
XMIN = -(OX - 8) / SCALE
LEAD_PX = 300        # in moving-frame mode the ball is kept this far from the left edge
COLORS = ["#f97316", "#22d3ee", "#a3e635", "#f472b6", "#facc15", "#818cf8", "#fb7185"]

shots = []
cam = 0.0            # world x (metres) shown at the cannon's screen position


def el(i):
    return document.getElementById(i)


class Shot:
    def __init__(self, angle, v, color, n, rebound, e, follow):
        a = math.radians(angle)
        self.vx, self.vy = v * math.cos(a), v * math.sin(a)
        self.angle, self.v, self.color, self.n = angle, v, color, n
        self.rebound, self.e, self.follow = rebound, e, follow
        self.x = self.y = 0.0
        self.t = 0.0
        self.acc = 0.0
        self.steps = 0
        self.pts = [(0.0, 0.0)]
        self.marks = []
        self.bounces = 0
        self.first_range = None
        self.max_h = 0.0
        self.done = False

    def advance(self, sim_dt):
        if self.done:
            return
        self.acc += sim_dt
        while self.acc >= DT and not self.done:
            self.acc -= DT
            self.step(DT)

    def step(self, dt):
        px_, py_ = self.x, self.y
        self.y += self.vy * dt - 0.5 * G * dt * dt
        self.vy -= G * dt
        self.x += self.vx * dt
        self.t += dt
        self.steps += 1

        if self.y < 0:
            frac = py_ / (py_ - self.y) if py_ > self.y else 0.0
            self.x = px_ + (self.x - px_) * frac
            self.t -= dt * (1 - frac)
            self.y = 0.0
            if self.first_range is None:
                self.first_range = self.x
            if not self.rebound:
                self.done = True
            else:
                new_vy = -self.vy * self.e
                self.vx *= FRICTION
                self.bounces += 1
                self.marks.append((self.x, 0.0))
                if new_vy < STOP_VY:
                    self.vy = 0.0
                    self.done = True
                else:
                    self.vy = new_vy

        if self.rebound and not self.follow:   # walls only in the static frame
            if self.x > XMAX:
                self.x, self.vx = XMAX, -abs(self.vx) * self.e
            elif self.x < XMIN:
                self.x, self.vx = XMIN, abs(self.vx) * self.e

        if self.first_range is None:
            self.max_h = max(self.max_h, self.y)
        if self.steps % 6 == 0 or self.done:
            self.pts.append((self.x, self.y))


def px(x, y):
    return OX + (x - cam) * SCALE, OY - y * SCALE


def fmt_m(m):
    return f"{m / 1000:.1f} km" if abs(m) >= 1000 else f"{m:.0f} m"


def trace(points):
    ctx.beginPath()
    for i, (x, y) in enumerate(points):
        cx, cy = px(x, y)
        if i == 0:
            ctx.moveTo(cx, cy)
        else:
            ctx.lineTo(cx, cy)
    ctx.stroke()


def draw_scene(angle, v):
    ctx.clearRect(0, 0, W, H)
    ctx.fillStyle = "#1e293b"; ctx.fillRect(0, 0, W, H)
    ctx.fillStyle = "#14532d"; ctx.fillRect(0, OY, W, GROUND)

    # distance ticks every 100 m, scrolling with the camera
    ctx.fillStyle = "#94a3b8"; ctx.font = "11px sans-serif"; ctx.strokeStyle = "#475569"
    ctx.setLineDash(to_js([])); ctx.lineWidth = 1
    left = cam - OX / SCALE
    right = cam + (W - OX) / SCALE
    m = int(math.floor(left / 100.0)) * 100
    while m <= right:
        if m >= 0:
            cx, _ = px(m, 0)
            ctx.beginPath(); ctx.moveTo(cx, OY); ctx.lineTo(cx, OY + 8); ctx.stroke()
            ctx.fillText(fmt_m(m), cx - 14, OY + 22)
        m += 100

    if el("guide").checked:
        a = math.radians(angle)
        vx, vy = v * math.cos(a), v * math.sin(a)
        T = 2 * vy / G
        pts = [(vx * (T * i / 60), vy * (T * i / 60) - 0.5 * G * (T * i / 60) ** 2) for i in range(61)]
        ctx.strokeStyle = "rgba(255,255,255,0.35)"; ctx.lineWidth = 1.5
        ctx.setLineDash(to_js([4, 6])); trace(pts); ctx.setLineDash(to_js([]))

    for s in shots:
        ctx.strokeStyle = s.color; ctx.lineWidth = 2
        trace(s.pts)
        for mx, my in s.marks:
            bx, by = px(mx, my)
            ctx.fillStyle = s.color
            ctx.beginPath(); ctx.arc(bx, by, 3, 0, math.tau); ctx.fill()
        ex, ey = px(s.x, s.y)
        ctx.font = "12px sans-serif"
        if s.done:
            ctx.strokeStyle = s.color
            ctx.beginPath(); ctx.moveTo(ex - 5, ey - 5); ctx.lineTo(ex + 5, ey + 5)
            ctx.moveTo(ex + 5, ey - 5); ctx.lineTo(ex - 5, ey + 5); ctx.stroke()
            ctx.fillStyle = s.color
            if s.rebound:
                ctx.fillText(f"#{s.n} stopped at {fmt_m(s.x)} | {s.bounces} bounces | {s.t:.1f} s",
                             ex - 90, ey - 12)
            else:
                ctx.fillText(f"#{s.n}  {fmt_m(s.first_range)}  {s.t:.2f} s", ex - 40, ey - 12)
        else:
            ctx.fillStyle = "#e2e8f0"
            ctx.beginPath(); ctx.arc(ex, ey, 6, 0, math.tau); ctx.fill()
            ctx.fillStyle = s.color
            ctx.fillText(f"{s.t:.2f} s | {fmt_m(s.x)}", ex + 10, ey - 10)

    # cannon (scrolls away with the world in moving-frame mode)
    cx0, _ = px(0, 0)
    if -80 < cx0 < W + 80:
        ctx.save()
        ctx.translate(cx0, OY); ctx.rotate(-math.radians(angle))
        ctx.fillStyle = "#cbd5e1"; ctx.fillRect(-6, -9, 56, 18)
        ctx.restore()
        ctx.fillStyle = "#475569"
        ctx.beginPath(); ctx.arc(cx0, OY, 18, math.pi, 0); ctx.fill()

    ctx.fillStyle = "#e2e8f0"; ctx.font = "13px sans-serif"
    ctx.fillText(f"Shots: {len(shots)}", W - 90, 24)
    if shots:
        s = shots[-1]
        rng = fmt_m(s.first_range) if s.first_range is not None else "..."
        ctx.fillText(f"Last: {s.angle:.0f}° @ {s.v:.0f} m/s | peak {s.max_h:.0f} m | first range {rng}", 14, 24)


def launch(evt=None):
    n = len(shots) + 1
    shots.append(Shot(float(el("angle").value), float(el("vel").value),
                      COLORS[(n - 1) % len(COLORS)], n,
                      el("rebound").checked, float(el("rest").value), el("follow").checked))


def clear(evt=None):
    global cam
    shots.clear()
    cam = 0.0


def on_rebound(evt=None):
    on = el("rebound").checked
    el("rest").disabled = not on
    el("speed").value = 3 if on else 1


last_ts = None


def frame(ts):
    global last_ts, cam
    dt = 0.0 if last_ts is None else min((ts - last_ts) / 1000.0, 0.25)
    last_ts = ts
    angle = float(el("angle").value)
    v = float(el("vel").value)
    speed = float(el("speed").value)
    el("angleVal").innerText = f"{angle:.0f}°"
    el("velVal").innerText = f"{v:.0f} m/s"
    el("speedVal").innerText = f"{speed:.1f}x"
    el("restVal").innerText = f"{float(el('rest').value):.2f}"

    for s in shots:
        s.advance(dt * speed)

    # camera: follow the newest moving ball (or the last shot once everything has stopped)
    if el("follow").checked and shots:
        active = [s for s in shots if not s.done]
        ref = active[-1] if active else shots[-1]
        target = max(0.0, ref.x - LEAD_PX / SCALE)
        cam += (target - cam) * (1 - math.exp(-dt * 6))
    else:
        cam = 0.0

    draw_scene(angle, v)
    window.requestAnimationFrame(frame_proxy)


frame_proxy = create_proxy(frame)
el("launch").addEventListener("click", create_proxy(launch))
el("clear").addEventListener("click", create_proxy(clear))
el("rebound").addEventListener("change", create_proxy(on_rebound))
el("loading").style.display = "none"
window.requestAnimationFrame(frame_proxy)