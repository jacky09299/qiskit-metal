import os
import numpy as np

from qiskit_metal import designs
from qiskit_metal.qlibrary.terminations.launchpad_wb import LaunchpadWirebond
from qiskit_metal import MetalGUI

from components import TreeRoute


# ============================================================
# Design Parameters
# ============================================================

TRACE_WIDTH = '10um'
TRACE_GAP = '6um'
FILLET = '0um'

ENABLE_GUI = os.environ.get(
    'ENABLE_GUI',
    'True'
).lower() == 'true'


# ============================================================
# Geometry Parameters
# Units: mm
# ============================================================

B = 0.60
D = 0.40
C = 0.85
DELTA = 1.05

A1 = 2.10
A2 = 2.00
A3 = 2.30

LP1 = 1.13
LP2 = 0.08
LP3 = 0.10
LP4 = 0.21
LP5 = 0.10


# ============================================================
# Utility Functions
# ============================================================

def normalize_point(point, digits=6):
    """Convert a numpy array, tuple, or list to a float coordinate list."""
    return [
        round(float(point[0]), digits),
        round(float(point[1]), digits)
    ]


def points_close(point_a, point_b, atol=1e-9):
    """Return True when two coordinates are equal within tolerance."""
    return np.allclose(
        np.asarray(point_a, dtype=float),
        np.asarray(point_b, dtype=float),
        atol=atol,
        rtol=0.0
    )


# ============================================================
# Path Builder
# ============================================================

class PathBuilder:
    def __init__(self, start_pt):
        start_pt = normalize_point(start_pt, digits=6)
        self.P_now = [start_pt[0], start_pt[1]]
        self.path = [list(self.P_now)]

    def move(self, dx, dy):
        """Add one horizontal or vertical movement."""
        dx = float(dx)
        dy = float(dy)

        if abs(dx) > 1e-12 and abs(dy) > 1e-12:
            raise ValueError(
                f'PathBuilder.move() only accepts horizontal or vertical '
                f'movement, received dx={dx}, dy={dy}'
            )

        if abs(dx) <= 1e-12 and abs(dy) <= 1e-12:
            return self

        self.P_now[0] = round(self.P_now[0] + dx, 6)
        self.P_now[1] = round(self.P_now[1] + dy, 6)
        self.path.append(list(self.P_now))
        return self

    def move_to_x(self, target_x):
        dx = round(float(target_x) - self.P_now[0], 6)
        if abs(dx) > 1e-12:
            self.move(dx, 0)
        return self

    def move_to_y(self, target_y):
        dy = round(float(target_y) - self.P_now[1], 6)
        if abs(dy) > 1e-12:
            self.move(0, dy)
        return self

    def move_to(self, target_pt, horizontal_first=True):
        target_pt = normalize_point(target_pt, digits=6)
        if horizontal_first:
            self.move_to_x(target_pt[0])
            self.move_to_y(target_pt[1])
        else:
            self.move_to_y(target_pt[1])
            self.move_to_x(target_pt[0])
        return self


# ============================================================
# Incremental Path Generation
# ============================================================

def generate_routes(left_tie, right_tie):
    """Build the main routes and all ground stubs."""
    left_tie = normalize_point(left_tie)
    right_tie = normalize_point(right_tie)

    print('\n' + '=' * 60)
    print('Route endpoint coordinates')
    print('=' * 60)
    print(f'left_launch.tie  = {left_tie}')
    print(f'right_launch.tie = {right_tie}')
    print('=' * 60 + '\n')

    # ---------------- Left side ----------------
    left_nominal_entry = [-8.75, -3.00]

    # Path 1: Left Launchpad -> J4
    pb1 = PathBuilder(left_tie)
    pb1.path.insert(0, {'component': 'left_launch', 'pin': 'tie'})
    pb1.move_to(left_nominal_entry, horizontal_first=True)
    pb1.move(0.95, 0)
    pb1.move(0, DELTA)

    for i in range(5):
        pb1.move(B, 0)
        pb1.move(0, -A1)
        pb1.move(B, 0)
        if i < 4:
            pb1.move(0, A1)

    pb1.move(0, 1.25)
    pb1.move(0.90, 0)
    t1 = pb1.path

    # Path 2: J4 -> J2
    pb2 = PathBuilder([-0.90, -2.80])
    pb2.move(0, 2.85)
    pb2.move(-1.00, 0)

    for _ in range(3):
        pb2.move(0, -A2)
        pb2.move(-B, 0)
        pb2.move(0, A2)
        pb2.move(-B, 0)

    pb2.move(0, -A2)
    pb2.move(-B, 0)
    pb2.move(0, 1.85)
    pb2.move(-0.50, 0)
    t2 = pb2.path

    # Path 3: J2 -> J3
    pb3 = PathBuilder([-6.60, -0.10])
    pb3.move(0, 3.30)

    for _ in range(4):
        pb3.move(B, 0)
        pb3.move(0, -A3)
        pb3.move(B, 0)
        pb3.move(0, A3)

    pb3.move(1.80, 0)
    t3 = pb3.path

    # ---------------- Right side ----------------

    # Path 4: J3 -> J6
    pb4 = PathBuilder([0.00, 3.20])
    pb4.move(1.80, 0)

    for _ in range(4):
        pb4.move(0, -A3)
        pb4.move(B, 0)
        pb4.move(0, A3)
        pb4.move(B, 0)

    pb4.move(0, -3.30)
    t4 = pb4.path

    # Path 5: J6 -> J5
    pb5 = PathBuilder([6.60, -0.10])
    pb5.move(-0.50, 0)
    pb5.move(0, -1.85)

    for _ in range(3):
        pb5.move(-B, 0)
        pb5.move(0, A2)
        pb5.move(-B, 0)
        pb5.move(0, -A2)

    pb5.move(-B, 0)
    pb5.move(0, -0.85)
    pb5.move(-1.00, 0)
    t5 = pb5.path

    # Path 6: J5 -> Right Launchpad
    pb6 = PathBuilder([0.90, -2.80])
    pb6.move(0.90, 0)

    for _ in range(4):
        pb6.move(0, -1.25)
        pb6.move(B, 0)
        pb6.move(0, A1)
        pb6.move(B, 0)

    pb6.move(0, -1.05)
    pb6.move(1.20, 0)
    pb6.move_to(right_tie, horizontal_first=True)
    pb6.path.append({'component': 'right_launch', 'pin': 'tie'})
    t6 = pb6.path

    # ---------------- Ground stubs ----------------
    def stub(pt, length):
        pt = normalize_point(pt)
        return [
            list(pt),
            [pt[0], round(pt[1] - float(length), 6)]
        ]

    stubs = {
        'left_ground': {
            'path': stub(left_tie, -LP1),
            'end': 'short'
        },
        'right_ground': {
            'path': stub(right_tie, -LP1),
            'end': 'short'
        },
        'ground_4': {
            'path': stub([-0.90, -2.80], LP2),
            'end': 'short'
        },
        'ground_2': {
            'path': stub([-6.60, -0.10], LP4),
            'end': 'short'
        },
        'ground_3': {
            'path': stub([0.00, 3.20], LP3),
            'end': 'short'
        },
        'ground_6': {
            'path': stub([6.60, -0.10], LP4),
            'end': 'short'
        },
        'ground_5': {
            'path': stub([0.90, -2.80], LP5),
            'end': 'short'
        }
    }

    return t1, t2, t3, t4, t5, t6, stubs


# ============================================================
# Validation
# ============================================================

def validate_route_connections(t1, t2, t3, t4, t5, t6, stubs,
                               left_tie, right_tie):
    left_tie = normalize_point(left_tie)
    right_tie = normalize_point(right_tie)

    checks = [
        ('t1 -> t2 at J4', [-0.90, -2.80], t1[-1], t2[0]),
        ('t2 -> t3 at J2', [-6.60, -0.10], t2[-1], t3[0]),
        ('t3 -> t4 at J3', [0.00, 3.20], t3[-1], t4[0]),
        ('t4 -> t5 at J6', [6.60, -0.10], t4[-1], t5[0]),
        ('t5 -> t6 at J5', [0.90, -2.80], t5[-1], t6[0]),
        ('left_ground start', left_tie,
         stubs['left_ground']['path'][0], left_tie),
        ('right_ground start', right_tie,
         stubs['right_ground']['path'][0], right_tie)
    ]

    print('\n' + '=' * 60)
    print('Route connection validation')
    print('=' * 60)

    errors = []
    for name, expected, actual_a, actual_b in checks:
        valid = (
            points_close(expected, actual_a)
            and points_close(expected, actual_b)
        )
        status = 'OK' if valid else 'ERROR'
        print(
            f'[{status}] {name}: expected={expected}, '
            f'a={actual_a}, b={actual_b}'
        )
        if not valid:
            errors.append(name)

    print('=' * 60 + '\n')

    if errors:
        raise ValueError(
            'Route connection coordinate mismatch: ' + ', '.join(errors)
        )


# ============================================================
# Main Execution
# ============================================================

def main():
    design = designs.DesignPlanar(overwrite_enabled=True)
    design.chips.main.size.size_x = '22mm'
    design.chips.main.size.size_y = '12mm'

    left_launch = LaunchpadWirebond(
        design,
        'left_launch',
        options=dict(
            pos_x='-9.0mm',
            pos_y='-3mm',
            orientation='0',
            trace_width=TRACE_WIDTH,
            trace_gap=TRACE_GAP
        )
    )

    right_launch = LaunchpadWirebond(
        design,
        'right_launch',
        options=dict(
            pos_x='9.0mm',
            pos_y='-3mm',
            orientation='180',
            trace_width=TRACE_WIDTH,
            trace_gap=TRACE_GAP
        )
    )

    left_tie = normalize_point(left_launch.pins['tie']['middle'])
    right_tie = normalize_point(right_launch.pins['tie']['middle'])

    print('\nLaunchpad pin coordinates:')
    print(f'left_launch.tie  = {left_tie}')
    print(f'right_launch.tie = {right_tie}')

    t1, t2, t3, t4, t5, t6, stubs = generate_routes(
        left_tie=left_tie,
        right_tie=right_tie
    )

    validate_route_connections(
        t1=t1,
        t2=t2,
        t3=t3,
        t4=t4,
        t5=t5,
        t6=t6,
        stubs=stubs,
        left_tie=left_tie,
        right_tie=right_tie
    )

    tree_config = [
        {'name': 'j1_to_j4', 'path': t1},
        {'name': 'j4_to_j2', 'path': t2},
        {'name': 'j2_to_j3', 'path': t3},
        {'name': 'j3_to_j6', 'path': t4},
        {'name': 'j6_to_j5', 'path': t5},
        {'name': 'j5_to_j7', 'path': t6}
    ]

    for stub_name, stub_config in stubs.items():
        tree_config.append({'name': stub_name, **stub_config})

    tree = TreeRoute(
        design=design,
        name='test2',
        tree_config=tree_config,
        trace_width=TRACE_WIDTH,
        trace_gap=TRACE_GAP,
        fillet=FILLET,
        lead_in='0mm',
        lead_out='0mm'
    )

    print('\nTreeRoute created successfully.')

    if hasattr(tree, 'print_routes'):
        tree.print_routes()

    if hasattr(tree, 'print_junctions'):
        tree.print_junctions()

    if hasattr(tree, 'get_total_length'):
        try:
            print(f'\nTotal route length: {tree.get_total_length()} mm')
        except Exception as exc:
            print(f'\nUnable to calculate total route length: {exc}')

    if ENABLE_GUI and MetalGUI is not None:
        gui = MetalGUI(design)
        gui.rebuild()
        gui.autoscale()

        if hasattr(gui, 'main_window') and gui.main_window is not None:
            gui.main_window.show()
            gui.qApp.exec_()

    return design, tree


if __name__ == '__main__':
    main()

