"""Read the vendor assembly without changing it; accumulate ALL parent placements."""
import csv
from build123d import Axis, Compound, GeomType, Location, import_step

SELECT = {'BOARD': 'PCB_BOARD', '2_8INCH_ASM': 'DISPLAY',
          'KEY1_ASM': 'KEY1', 'KEY2_ASM': 'KEY2', 'KEY3_ASM': 'KEY3',
          'MIC1_ASM': 'MIC1', 'J2_ASM': 'J2_USB_SIDE'}


def bounds(shape):
    b = shape.bounding_box()
    return [*b.min, *b.max]


def load_reference(path):
    source = import_step(path)
    selected, mounts = {}, []

    def walk(node, parent=Location()):
        if node.label in SELECT or node.label == 'SMTSO-M2_5-4ET':
            # Child coordinates are LOCAL to the parent, not to the STEP root.
            global_shape = Compound.cast(node.wrapped.Moved(parent.wrapped))
            global_shape.parent = None
            if node.label in SELECT:
                selected[SELECT[node.label]] = global_shape
            else:
                mounts.append(global_shape)
        for child in node.children:
            walk(child, parent * node.location)

    walk(source)
    assert set(selected) == set(SELECT.values())
    assert len(mounts) == 4
    selected['ASSEMBLY'] = Compound(source.wrapped)
    return selected, mounts


def to_pocket(shape):
    # A proper rigid rotation, NOT a mirror. Preserve z and every relative placement.
    result = shape.rotate(Axis.Z, 180)
    result.parent = None
    return result


def hole_axes(pcb):
    """Read circular edge centers on BOARD; use through-hole circles, not nut boxes."""
    holes = {}
    for edge in pcb.edges():
        if edge.geom_type == GeomType.CIRCLE and 2.0 < edge.radius < 2.3:
            c = edge.arc_center
            holes[(round(c.X, 5), round(c.Y, 5), round(edge.radius, 5))] = None
    assert len(holes) == 4, f'Expected four PCB holes, found {holes}'
    return [list(h) for h in sorted(holes)]


def compare_recorded(selected, csv_path, tolerance):
    results = {}
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            name = row['name']
            recorded = [float(row[k]) for k in (
                'x_min_mm', 'y_min_mm', 'z_min_mm', 'x_max_mm', 'y_max_mm', 'z_max_mm')]
            actual = bounds(selected[name])
            delta = max(abs(a-b) for a,b in zip(actual, recorded))
            results[name] = {'actual_original_bounds_mm': actual,
                             'max_difference_from_recorded_mm': delta,
                             'pass': delta <= tolerance}
    assert all(r['pass'] for r in results.values()), results
    return results
