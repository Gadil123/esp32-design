"""Re-read delivered STEP interfaces and destructively test their gates.

Run with .venv/bin/python scripts/check-g-v4-interfaces.py. Mutated shapes stay
in memory; no delivery, source parameter or vendor file is changed.
"""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cad/t0'))
from build123d import import_step
import g_v4_checks as C


def main():
    d=ROOT/'deliverables/g-v4'
    v=json.loads((ROOT/'cad/t0/t0-g-v4.json').read_text())
    plate=import_step(d/'0127_retainer.step')
    fixtures={f'0127_coupon_{name}':(import_step(d/f'0127_coupon_{name}.step'),
              import_step(d/f'0127_coupon_{name}_bezel.step'),clearance)
              for name,clearance in zip('ABC',v['silicone_keys']['coupon_clearances_per_side_mm'])}
    report=dict(retainer=C.retainer_windows(plate,v,v['silicone_keys']['y_mm']),
                reset=C.retainer_reset_window(plate,v),
                coupons={name:C.coupon_interface(block,bezel,v,clearance)
                         for name,(block,bezel,clearance) in fixtures.items()},
                negative_controls=C.interface_negative_controls(plate,fixtures,v))
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
