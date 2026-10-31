"""Re-read delivered V4-CLEAN parts and reject deliberately broken RAM-only copies.

Run with .venv/bin/python scripts/check-g-v4-interfaces.py.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'build/matplotlib'))
sys.path.insert(0, str(ROOT / 'cad/t0'))
from build123d import import_step
from generate_g_v4 import load_baseline
from t0_reference import load
import t0_g_v4 as V4
import g_v4_slider_checks as S
import g_v4_checks as C
from check_exports import verify_exports


def main():
    d = ROOT / 'deliverables/g-v4'
    base, kp, p, kq, v = load_baseline()
    parts, mounts, _ = load(ROOT.parent / 'ESP32-C5-Touch-LCD-2.8/dimensions/ESP32-C5-Touch-LCD-2.8.stp')
    m = V4.build(parts, mounts, base, kp, p, kq, v)
    for internal, filename in [('front', 'front_shell'), ('rear', 'rear_shell')]:
        m[internal] = import_step(d / f'{filename}.step')
    m['button_exports'] = {name: import_step(d / f'{name}.step') for name in m['button_exports']}
    m['buttons'] = {f'KEY{i}': m['button_exports'][f'button_{label}_nominal'] for i, label in [(1, 'power'), (2, 'boot')]}
    report = dict(
        sliders=S.check(m, parts, v),
        negative_controls=S.negative_controls(m, parts, v),
        left_hook=C.left_hook(m['front'], m['rear'], v),
        left_hook_negative=C.left_hook_negative_control(m['front'], m['rear'], v),
        USB=C.usb_access(m),
        USB_negative=C.usb_negative_control(m),
        speaker_notch=C.speaker_notch(m['front'], base, m['dimensions']),
        speaker_notch_negatives=C.speaker_notch_negative_controls(m['front'], base, m['dimensions']),
        speaker_supports=C.speaker_supports(m, base),
        speaker_support_negative=C.speaker_support_negative_control(m, base),
        screen=C.screen_column(m['front'], m['screen_geometry']),
        exports=verify_exports(d, names=('front_shell', 'rear_shell', *m['button_exports'])),
    )
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
