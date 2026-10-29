"""Genera app/static/img/contours.svg: curvas de nivel estilizadas (como un mapa topográfico)."""
import math
from pathlib import Path

W, H = 1600, 700
cx, cy = 1180, 330


def blob(k: int, n: int = 120) -> str:
    base = 38 + k * 34
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        r = base * (1 + 0.16 * math.sin(3 * t + k * 0.35) + 0.09 * math.sin(5 * t - k * 0.5) + 0.05 * math.sin(9 * t + k))
        x = cx + r * 1.55 * math.cos(t)
        y = cy + r * 0.85 * math.sin(t)
        pts.append(f"{x:.1f},{y:.1f}")
    return "M" + " L".join(pts) + " Z"


paths = "".join(
    f'<path d="{blob(k)}" stroke="#fff" stroke-opacity="{0.16 if k % 4 == 0 else 0.08}" '
    f'stroke-width="{1.6 if k % 4 == 0 else 1}" fill="none"/>'
    for k in range(1, 17)
)
svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice">{paths}</svg>'
out = Path(__file__).resolve().parent.parent / "app" / "static" / "img"
out.mkdir(parents=True, exist_ok=True)
(out / "contours.svg").write_text(svg)
print("ok", len(svg))
