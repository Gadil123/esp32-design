#!/usr/bin/env python3
"""T1 final print export: cut the user-approved Ø1.5 mm MIC aperture into G-V1 front shell.

Reads the independently reviewed 95.60 mm candidate STEP from PR #6, uses
OpenCascade BRep boolean subtraction, exports exact STEP and watertight STL.
Rear shell is unchanged. DOES NOT authorize manufacturing or pretend that
physical microphone sound-port orientation has been proven.

Repro:
  python -m pip install cadquery-ocp-novtk trimesh
  python scripts/finalize-g-v1-t1-print.py

This isolated finalization avoids rerunning the 723-part official-board analysis
which was already completed in PR #6. Do not use the old generator to replace
the finalized print artifacts without cutting this bore again.
"""
import json
import math
import shutil
import zipfile
from pathlib import Path

from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.Bnd import Bnd_Box
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Reader, STEPControl_Writer
from OCP.StlAPI import StlAPI_Writer
from OCP.TopAbs import TopAbs_SHELL, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "deliverables" / "g-v1-95mm"
OUTPUT = ROOT / "deliverables" / "g-v1-t1-final"
X, Y, DIAMETER = 27.30, 1.395, 1.50
# PR #7 independently measured front panel Z=-0.50..+0.70.
# Extend the cutting cylinder on both sides; avoid deeper cavity geometry.
Z_START, Z_END = -0.60, 0.80
EXPECTED_REMOVED_MM3 = math.pi * (DIAMETER / 2) ** 2 * 1.2


def read_step(path):
    reader = STEPControl_Reader()
    assert reader.ReadFile(str(path)) == IFSelect_RetDone, f"read STEP failed: {path}"
    assert reader.TransferRoots() > 0, f"empty STEP: {path}"
    shape = reader.OneShape()
    assert BRepCheck_Analyzer(shape).IsValid(), f"invalid STEP input: {path}"
    return shape


def count(shape, kind):
    it = TopExp_Explorer(shape, kind)
    n = 0
    while it.More():
        n += 1
        it.Next()
    return n


def volume(shape):
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    return props.Mass()


def bbox(shape):
    b = Bnd_Box()
    BRepBndLib.Add_s(shape, b)
    return tuple(float(x) for x in b.Get())


def write_step(shape, path):
    writer = STEPControl_Writer()
    assert writer.Transfer(shape, STEPControl_AsIs) == IFSelect_RetDone
    assert writer.Write(str(path)) == IFSelect_RetDone, f"write STEP failed: {path}"


def write_stl(shape, path):
    mesh = BRepMesh_IncrementalMesh(shape, 0.015, False, 0.12, False)
    mesh.Perform()
    assert mesh.IsDone(), "mesher failed"
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    assert writer.Write(shape, str(path)), f"write STL failed: {path}"


def main():
    import trimesh

    OUTPUT.mkdir(parents=True, exist_ok=True)
    original = read_step(INPUT / "front_shell.step")
    rear = read_step(INPUT / "rear_shell.step")
    assert count(original, TopAbs_SOLID) == 1 and count(rear, TopAbs_SOLID) == 1

    tool = BRepPrimAPI_MakeCylinder(
        gp_Ax2(gp_Pnt(X, Y, Z_START), gp_Dir(0, 0, 1)),
        DIAMETER / 2, Z_END - Z_START
    ).Shape()
    touch = BRepAlgoAPI_Common(original, tool)
    touch.Build()
    assert touch.IsDone()
    removed = volume(touch.Shape())
    assert abs(removed - EXPECTED_REMOVED_MM3) < 0.02, (
        f"MIC drill path intersects unexpected material: {removed:.8f} vs "
        f"{EXPECTED_REMOVED_MM3:.8f} mm³"
    )

    cut = BRepAlgoAPI_Cut(original, tool)
    cut.Build()
    assert cut.IsDone(), "OCP boolean cut failed"
    front = cut.Shape()
    assert BRepCheck_Analyzer(front).IsValid(), "front shell no longer valid"
    assert count(front, TopAbs_SOLID) == 1, "front shell must remain one solid"
    assert count(front, TopAbs_SHELL) == 1, "front shell has an unexpected cavity"
    assert abs((volume(original) - volume(front)) - removed) < 0.005, (
        "unexpected front-shell change beyond MIC bore"
    )

    probe = BRepAlgoAPI_Common(front, tool)
    probe.Build()
    assert probe.IsDone() and volume(probe.Shape()) < 0.0001, (
        "MIC hole is not fully open"
    )

    front_step = OUTPUT / "front_shell_MIC_1p5mm.step"
    front_stl = OUTPUT / "front_shell_MIC_1p5mm.stl"
    rear_step = OUTPUT / "rear_shell_UNCHANGED.step"
    rear_stl = OUTPUT / "rear_shell_UNCHANGED.stl"
    write_step(front, front_step)
    write_stl(front, front_stl)
    shutil.copy2(INPUT / "rear_shell.step", rear_step)
    shutil.copy2(INPUT / "rear_shell.stl", rear_stl)

    checked_front = read_step(front_step)
    checked_rear = read_step(rear_step)
    assert count(checked_front, TopAbs_SOLID) == 1
    assert count(checked_rear, TopAbs_SOLID) == 1
    assert abs(volume(checked_front) - volume(front)) < 0.02
    assert abs(volume(checked_rear) - volume(rear)) < 0.02
    mesh_checks = {}
    for label, stl, solid in [
        ("front", front_stl, checked_front),
        ("rear", rear_stl, checked_rear),
    ]:
        mesh = trimesh.load_mesh(str(stl))
        assert mesh.is_watertight, f"{label} STL is not watertight"
        assert mesh.is_winding_consistent, f"{label} winding inconsistent"
        assert mesh.volume > 0, f"{label} STL negative volume"
        assert abs(mesh.volume - volume(solid)) < 2.0, (
            f"{label} STL/STEP volume mismatch"
        )
        mesh_checks[label] = dict(
            triangles=len(mesh.faces),
            watertight=True,
            winding_consistent=True,
            mesh_volume_mm3=float(mesh.volume),
            step_volume_mm3=float(volume(solid)),
        )

    before = bbox(original)
    after = bbox(checked_front)
    r_before = bbox(rear)
    r_after = bbox(checked_rear)
    assert all(abs(a-b) < 0.002 for a,b in zip(before,after)), (
        "front bounding box shifted"
    )
    assert all(abs(a-b) < 0.002 for a,b in zip(r_before,r_after)), (
        "rear bounding box shifted"
    )

    report = dict(
        candidate="G-V1 95.60mm / T1 first print",
        source="PR #6 reviewed CAD; PR #7 CONDITIONAL GO",
        status="FILES_VERIFIED_MANUFACTURER_CHECKS_PENDING",
        actual_mic_port_acoustic_response="UNVERIFIED; T1 functional test required",
        front_mic_aperture=dict(
            x_mm=X, y_mm=Y, diameter_mm=DIAMETER,
            through_front_panel=True, removed_mm3=removed,
        ),
        original_front_volume_mm3=volume(original),
        finished_front_volume_mm3=volume(checked_front),
        rear_unchanged=True,
        front_bbox_mm=list(after),
        mesh_checks=mesh_checks,
        order_or_print_approved=False,
        remaining_preorder_conditions=[
            "MJF PA12 supplier sign-off for 0.81mm continuous wall, 1mm U slot, "
            "latch/keys/0.15mm play, 1mm screw seats, clean-out, no tumbling "
            "or grit blasting on mating surfaces, no arbitrary scaling",
            "Verify real metal inserts and M2.5 screw pitch with physical screw",
        ],
    )
    (OUTPUT / "print_checks.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    archive = OUTPUT / "G-V1_95p60_T1_MIC1p5_PRINT_FILES.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for p in [front_step, front_stl, rear_step, rear_stl, OUTPUT / "print_checks.json"]:
            z.write(p, p.name)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"T1 files exported: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
