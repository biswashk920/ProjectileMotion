import math
import random
from pyscript import document, window
from pyodide.ffi import create_proxy, to_js

canvas = document.getElementById("c")
ctx = canvas.getContext("2d")
W, H = canvas.width, canvas.height

# ---------- planets ----------
G_EARTH = 9.80665          # m/s^2
M_EARTH = 5.972e24         # kg
D_EARTH = 12742.0          # km
# name: (mass in Earth masses, diameter km, emoji, ground colour)
PRESETS = {
    "Mercury": (0.0553, 4879, "☿️", "#78716c"),
    "Venus":   (0.815, 12104, "🟡", "#a16207"),
    "Earth":   (1.0, 12742, "🌍", "#14532d"),
    "Moon":    (0.0123, 3474, "🌕", "#64748b"),
    "Mars":    (0.107, 6779, "🔴", "#9a3412"),
    "Jupiter": (317.8, 139820, "🟠", "#92400e"),
    "Saturn":  (95.16, 116460, "🪐", "#a16207"),
    "Uranus":  (14.54, 50724, "🔵", "#0e7490"),
    "Neptune": (17.15, 49244, "🔷", "#1d4ed8"),
    "Pluto":   (0.00218, 2377, "⚪", "#57534e"),
}
G_MIN, G_MAX = 0.05, 1000.0


def gravity(mass_e, diam_km):
    return G_EARTH * mass_e / (diam_km / D_EARTH) ** 2


planet = {"name": "Earth", "emoji": "🌍", "g": G_EARTH, "ground": "#14532d"}

# ---------- simulation constants ----------
GROUND = 60
OX, OY = 60, H - GROUND
DT = 1 / 240
FRICTION = 0.90
STOP_VY = 1.2
LEAD_PX = 300
COLORS = ["#f97316", "#22d3ee", "#a3e635", "#f472b6", "#facc15", "#818cf8", "#fb7185"]


def view_scale():
    # zoom is tied to gravity so the biggest shot (100 m/s, straight up) always fits on screen
    return 0.0825 * planet["g"]      # pixels per metre (~0.8 on Earth)


shots = []
cam = 0.0


def el(i):
    return document.getElementById(i)


# ---------- sound (synthesised with the Web Audio API, no files needed) ----------
audio = {"ctx": None, "noise": None, "last_pop": 0.0}


def ensure_audio():
    """browsers only allow sound after a click, so this is called from Launch"""
    try:
        if audio["ctx"] is None:
            ac = window.AudioContext.new()
            n = int(ac.sampleRate * 0.6)
            buf = ac.createBuffer(1, n, ac.sampleRate)
            data = [random.uniform(-1, 1) * (1 - i / n) ** 2 for i in range(n)]
            buf.getChannelData(0).set(to_js(data))
            audio["noise"] = buf
            audio["ctx"] = ac
        if audio["ctx"].state == "suspended":
            audio["ctx"].resume()
    except Exception as ex:
        print("Audio unavailable:", ex)


def sound_on():
    return audio["ctx"] is not None and el("sound").checked


def play_boom():
    if not sound_on():
        return
    try:
        ac = audio["ctx"]; t = ac.currentTime
        o = ac.createOscillator(); g = ac.createGain()          # low thump
        o.type = "sine"
        o.frequency.setValueAtTime(140, t)
        o.frequency.exponentialRampToValueAtTime(30, t + 0.5)
        g.gain.setValueAtTime(1.0, t)
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.6)
        o.connect(g); g.connect(ac.destination)
        o.start(t); o.stop(t + 0.65)
        src = ac.createBufferSource(); src.buffer = audio["noise"]   # blast crackle
        f = ac.createBiquadFilter(); f.type = "lowpass"
        f.frequency.setValueAtTime(1800, t)
        f.frequency.exponentialRampToValueAtTime(200, t + 0.5)
        ng = ac.createGain()
        ng.gain.setValueAtTime(0.8, t)
        ng.gain.exponentialRampToValueAtTime(0.001, t + 0.55)
        src.connect(f); f.connect(ng); ng.connect(ac.destination)
        src.start(t)
    except Exception as ex:
        print("boom failed:", ex)


def bounce_sound(impact):
    """short pop, louder for harder hits; throttled so fast-forward doesn't machine-gun"""
    if not sound_on() or impact < 2:
        return
    now = window.performance.now()
    if now - audio["last_pop"] < 45:
        return
    audio["last_pop"] = now
    try:
        ac = audio["ctx"]; t = ac.currentTime
        vol = 0.15 + 0.55 * min(1.0, impact / 40.0)
        o = ac.createOscillator(); g = ac.createGain()
        o.type = "sine"
        o.frequency.setValueAtTime(700, t)
        o.frequency.exponentialRampToValueAtTime(250, t + 0.09)
        g.gain.setValueAtTime(vol, t)
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.11)
        o.connect(g); g.connect(ac.destination)
        o.start(t); o.stop(t + 0.13)
    except Exception as ex:
        print("pop failed:", ex)


class Shot:
    def __init__(self, angle, v, color, n, rebound, e, follow, g, scale):
        a = math.radians(angle)
        self.vx, self.vy = v * math.cos(a), v * math.sin(a)
        self.angle, self.v, self.color, self.n = angle, v, color, n
        self.rebound, self.e, self.follow = rebound, e, follow
        self.g = g
        self.xmax = (W - OX - 8) / scale
        self.xmin = -(OX - 8) / scale
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
        self.y += self.vy * dt - 0.5 * self.g * dt * dt
        self.vy -= self.g * dt
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
                bounce_sound(-self.vy)      # vy is still the impact velocity here
                self.marks.append((self.x, 0.0))
                if new_vy < STOP_VY:
                    self.vy = 0.0
                    self.done = True
                else:
                    self.vy = new_vy

        if self.rebound and not self.follow:
            if self.x > self.xmax:
                self.x, self.vx = self.xmax, -abs(self.vx) * self.e
            elif self.x < self.xmin:
                self.x, self.vx = self.xmin, abs(self.vx) * self.e

        if self.first_range is None:
            self.max_h = max(self.max_h, self.y)
        if self.steps % 6 == 0 or self.done:
            self.pts.append((self.x, self.y))


def px(x, y):
    return OX + (x - cam) * view_scale(), OY - y * view_scale()


def fmt_m(m):
    return f"{m / 1000:.1f} km" if abs(m) >= 1000 else f"{m:.3g} m"


def nice_step(raw):
    """round up to a 1-2-5 step"""
    p = 10 ** math.floor(math.log10(raw))
    for k in (1, 2, 5, 10):
        if raw <= k * p:
            return k * p
    return 10 * p


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
    sc = view_scale()
    g = planet["g"]
    ctx.clearRect(0, 0, W, H)
    ctx.fillStyle = "#1e293b"; ctx.fillRect(0, 0, W, H)
    ctx.fillStyle = planet["ground"]; ctx.fillRect(0, OY, W, GROUND)

    ctx.fillStyle = "#cbd5e1"; ctx.font = "11px sans-serif"; ctx.strokeStyle = "#64748b"
    ctx.setLineDash(to_js([])); ctx.lineWidth = 1
    step = nice_step(90 / sc)
    left = cam - OX / sc
    right = cam + (W - OX) / sc
    i = int(math.floor(left / step))
    while i * step <= right:
        m = i * step
        if m >= 0:
            cx, _ = px(m, 0)
            ctx.beginPath(); ctx.moveTo(cx, OY); ctx.lineTo(cx, OY + 8); ctx.stroke()
            ctx.fillText(fmt_m(m), cx - 14, OY + 22)
        i += 1

    if el("guide").checked:
        a = math.radians(angle)
        vx, vy = v * math.cos(a), v * math.sin(a)
        T = 2 * vy / g
        pts = [(vx * (T * k / 60), vy * (T * k / 60) - 0.5 * g * (T * k / 60) ** 2) for k in range(61)]
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

    cx0, _ = px(0, 0)
    if -80 < cx0 < W + 80:
        ctx.save()
        ctx.translate(cx0, OY); ctx.rotate(-math.radians(angle))
        ctx.fillStyle = "#cbd5e1"; ctx.fillRect(-6, -9, 56, 18)
        ctx.restore()
        ctx.fillStyle = "#475569"
        ctx.beginPath(); ctx.arc(cx0, OY, 18, math.pi, 0); ctx.fill()

    ctx.fillStyle = "#e2e8f0"; ctx.font = "13px sans-serif"
    ctx.textAlign = "right"
    ctx.fillText(f"{planet['emoji']} {planet['name']}  g = {g:.2f} m/s²", W - 14, 24)
    ctx.fillText(f"Shots: {len(shots)}", W - 14, 44)
    ctx.textAlign = "left"
    if shots:
        s = shots[-1]
        rng = fmt_m(s.first_range) if s.first_range is not None else "..."
        ctx.fillText(f"Last: {s.angle:.0f}° @ {s.v:.0f} m/s | peak {fmt_m(s.max_h)} | first range {rng}", 14, 24)


# ---------- controls ----------
def auto_speed():
    s = (G_EARTH / planet["g"]) ** 0.5          # low gravity = long flights, so play faster
    if el("rebound").checked:
        s *= 3
    return min(8.0, max(0.5, round(s * 2) / 2))


def launch(evt=None):
    ensure_audio()
    play_boom()
    n = len(shots) + 1
    shots.append(Shot(float(el("angle").value), float(el("vel").value),
                      COLORS[(n - 1) % len(COLORS)], n,
                      el("rebound").checked, float(el("rest").value), el("follow").checked,
                      planet["g"], view_scale()))


def clear(evt=None):
    global cam
    shots.clear()
    cam = 0.0


def on_rebound(evt=None):
    el("rest").disabled = not el("rebound").checked
    el("speed").value = auto_speed()


def set_planet_button():
    el("planet").innerText = f"{planet['emoji']} {planet['name']} · g = {planet['g']:.2f} m/s²"


# ---------- planet popup ----------
def mass_to_text(m_e):
    if el("massUnit").value == "kg":
        return f"{m_e * M_EARTH:.4g}"
    return f"{m_e:g}"


def read_modal():
    """returns (mass_in_earths, diameter_km) or None if invalid"""
    try:
        m = float(el("mass").value.strip())
        d = float(el("diam").value.strip())
    except ValueError:
        return None
    if m <= 0 or d <= 0:
        return None
    if el("massUnit").value == "kg":
        m = m / M_EARTH
    return m, d


def update_preview(evt=None):
    el("err").innerText = ""
    vals = read_modal()
    if vals is None:
        el("preview").innerText = "Enter a positive mass and diameter."
        return
    m, d = vals
    g = gravity(m, d)
    v_esc = math.sqrt(2 * g * d * 500) / 1000     # km/s  (radius = d/2 km = d*500 m)
    el("preview").innerText = (f"Surface gravity: {g:.2f} m/s² ({g / G_EARTH:.2f} × Earth) | "
                               f"escape speed: {v_esc:.1f} km/s")


def on_preset(evt=None):
    name = el("preset").value
    if name in PRESETS:
        m, d = PRESETS[name][0], PRESETS[name][1]
        el("mass").value = mass_to_text(m)
        el("diam").value = f"{d:g}"
    update_preview()


def on_edit(evt=None):
    el("preset").value = "Custom"
    update_preview()


def on_unit(evt=None):
    # convert the number currently shown to the newly chosen unit
    try:
        shown = float(el("mass").value.strip())
    except ValueError:
        return
    if el("massUnit").value == "kg":
        el("mass").value = f"{shown * M_EARTH:.4g}"
    else:
        el("mass").value = f"{shown / M_EARTH:g}"
    update_preview()


def open_modal(evt=None):
    el("modal").classList.add("open")
    update_preview()


def close_modal(evt=None):
    el("modal").classList.remove("open")


def apply_planet(evt=None):
    global cam
    vals = read_modal()
    if vals is None:
        el("err").innerText = "Please enter valid positive numbers."
        return
    m, d = vals
    g = gravity(m, d)
    if not (G_MIN <= g <= G_MAX):
        el("err").innerText = f"Gravity {g:.3g} m/s² is outside the supported range ({G_MIN}–{G_MAX})."
        return
    name = el("preset").value
    if name in PRESETS:
        planet.update(name=name, emoji=PRESETS[name][2], ground=PRESETS[name][3])
    else:
        planet.update(name="Custom", emoji="🪐", ground="#4b5563")
    planet["g"] = g
    shots.clear()               # the zoom level changes with gravity, so start with a clean sky
    cam = 0.0
    el("speed").value = auto_speed()
    set_planet_button()
    close_modal()


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

    if el("follow").checked and shots:
        active = [s for s in shots if not s.done]
        ref = active[-1] if active else shots[-1]
        target = max(0.0, ref.x - LEAD_PX / view_scale())
        cam += (target - cam) * (1 - math.exp(-dt * 6))
    else:
        cam = 0.0

    draw_scene(angle, v)
    window.requestAnimationFrame(frame_proxy)


frame_proxy = create_proxy(frame)
el("launch").addEventListener("click", create_proxy(launch))
el("clear").addEventListener("click", create_proxy(clear))
el("rebound").addEventListener("change", create_proxy(on_rebound))
el("planet").addEventListener("click", create_proxy(open_modal))
el("cancel").addEventListener("click", create_proxy(close_modal))
el("ok").addEventListener("click", create_proxy(apply_planet))
el("preset").addEventListener("change", create_proxy(on_preset))
el("massUnit").addEventListener("change", create_proxy(on_unit))
el("mass").addEventListener("input", create_proxy(on_edit))
el("diam").addEventListener("input", create_proxy(on_edit))
el("loading").style.display = "none"
set_planet_button()
window.requestAnimationFrame(frame_proxy)