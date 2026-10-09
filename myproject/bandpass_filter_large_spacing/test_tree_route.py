import os
import numpy as np

from qiskit_metal import designs, MetalGUI
from qiskit_metal.qlibrary.terminations.launchpad_wb import LaunchpadWirebond

from components import TreeRoute


# ============================================================
# Design Parameters
# ============================================================

TRACE_WIDTH = '10um'
TRACE_GAP = '6um'
FILLET = '0um'
ENABLE_GUI = os.environ.get('ENABLE_GUI', 'True').lower() == 'true'

# Geometry parameters, unit: mm
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
# Helpers
# ============================================================

def normalize_point(point, digits=6):
    return [
        round(float(point[0]), digits),
        round(float(point[1]), digits),
    ]


def mirror_point_y_axis(point):
    """Mirror one coordinate across the Y axis: (x, y) -> (-x, y)."""
    point = normalize_point(point)
    return [round(-point[0], 6), point[1]]


def mirror_reverse_path(path, component_name=None, pin_name='tie'):
    """
    Mirror a route across the Y axis and reverse its travel direction.

    Coordinate entries are mirrored and reversed. Component pin entries are
    replaced with the requested component pin and placed at the opposite end.
    """
    mirrored_coords = [
        mirror_point_y_axis(item)
        for item in path
        if isinstance(item, (list, tuple, np.ndarray))
    ]
    mirrored_coords.reverse()

    if component_name is not None:
        mirrored_coords.append({
            'component': component_name,
            'pin': pin_name,
        })

    return mirrored_coords


class PathBuilder:
    def __init__(self, start_pt):
        self.P_now = normalize_point(start_pt)
        self.path = [list(self.P_now)]

    def move(self, dx, dy):
        """Add a strictly horizontal or vertical movement."""
        dx = float(dx)
        dy = float(dy)

        if abs(dx) > 1e-12 and abs(dy) > 1e-12:
            raise ValueError(
                f'move() must be horizontal or vertical: dx={dx}, dy={dy}'
            )

        if abs(dx) <= 1e-12 and abs(dy) <= 1e-12:
            return self

        self.P_now[0] = round(self.P_now[0] + dx, 6)
        self.P_now[1] = round(self.P_now[1] + dy, 6)
        self.path.append(list(self.P_now))
        return self

    def move_to_x(self, target_x):
        return self.move(round(float(target_x) - self.P_now[0], 6), 0)

    def move_to_y(self, target_y):
        return self.move(0, round(float(target_y) - self.P_now[1], 6))

    def move_to(self, target_pt, horizontal_first=True):
        target_pt = normalize_point(target_pt)
        if horizontal_first:
            self.move_to_x(target_pt[0])
            self.move_to_y(target_pt[1])
        else:
            self.move_to_y(target_pt[1])
            self.move_to_x(target_pt[0])
        return self


# ============================================================
# Symmetric Route Generation
# ============================================================

def generate_routes(left_tie, right_tie):
    left_tie = normalize_point(left_tie)
    right_tie = normalize_point(right_tie)

    expected_right_tie = mirror_point_y_axis(left_tie)
    if not np.allclose(right_tie, expected_right_tie, atol=1e-6, rtol=0.0):
        raise ValueError(
            'Launchpad tie pins are not symmetric. '
            f'left_tie={left_tie}, right_tie={right_tie}, '
            f'expected_right_tie={expected_right_tie}'
        )

    # --------------------------------------------------------
    # Left half: build only the known-correct geometry
    # --------------------------------------------------------

    # t1: left launch -> J4
    pb1 = PathBuilder(left_tie)
    pb1.path.insert(0, {'component': 'left_launch', 'pin': 'tie'})

    # Preserve the nominal entry used by the original correct left geometry.
    pb1.move_to([-8.75, -3.00], horizontal_first=True)
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

    # t2: J4 -> J2
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

    # t3: J2 -> J3
    pb3 = PathBuilder([-6.60, -0.10])
    pb3.move(0, 3.30)

    for _ in range(4):
        pb3.move(B, 0)
        pb3.move(0, -A3)
        pb3.move(B, 0)
        pb3.move(0, A3)

    pb3.move(1.80, 0)
    t3 = pb3.path

    # --------------------------------------------------------
    # Right half: exact Y-axis mirror of the left half
    # --------------------------------------------------------

    # Reverse direction after mirroring so the routes remain center-to-right:
    # t3 (J2 -> J3) mirrors to t4 (J3 -> J6)
    # t2 (J4 -> J2) mirrors to t5 (J6 -> J5)
    # t1 (left launch -> J4) mirrors to t6 (J5 -> right launch)
    t4 = mirror_reverse_path(t3)
    t5 = mirror_reverse_path(t2)
    t6 = mirror_reverse_path(
        t1,
        component_name='right_launch',
        pin_name='tie',
    )

    # Force the last geometric coordinate to the actual right tie pin.
    # This retains symmetry and avoids floating-point or component pin mismatch.
    if not np.allclose(t6[-2], right_tie, atol=1e-6, rtol=0.0):
        raise ValueError(
            f'Mirrored t6 endpoint {t6[-2]} does not match right tie {right_tie}'
        )
    t6[-2] = list(right_tie)

    # --------------------------------------------------------
    # Ground stubs
    # --------------------------------------------------------

    def downward_stub(point, length):
        point = normalize_point(point)
        return [
            list(point),
            [point[0], round(point[1] - float(length), 6)],
        ]

    def upward_stub(point, length):
        point = normalize_point(point)
        return [
            list(point),
            [point[0], round(point[1] + float(length), 6)],
        ]

    stubs = {
        'left_ground': {
            'path': upward_stub(left_tie, LP1),
            'end': 'short',
        },
        'right_ground': {
            'path': upward_stub(right_tie, LP1),
            'end': 'short',
        },
        'ground_4': {
            'path': downward_stub([-0.90, -2.80], LP2),
            'end': 'short',
        },
        'ground_2': {
            'path': downward_stub([-6.60, -0.10], LP4),
            'end': 'short',
        },
        'ground_3': {
            'path': downward_stub([0.00, 3.20], LP3),
            'end': 'short',
        },
        'ground_6': {
            'path': downward_stub([6.60, -0.10], LP4),
            'end': 'short',
        },
        'ground_5': {
            'path': downward_stub([0.90, -2.80], LP2),
            'end': 'short',
        },
    }

    return t1, t2, t3, t4, t5, t6, stubs


# ============================================================
# Symmetry Validation
# ============================================================

def coordinate_items(path):
    return [
        normalize_point(item)
        for item in path
        if isinstance(item, (list, tuple, np.ndarray))
    ]


def assert_mirror_pair(left_path, right_path, pair_name):
    left_coords = coordinate_items(left_path)
    expected_right = [mirror_point_y_axis(p) for p in reversed(left_coords)]
    right_coords = coordinate_items(right_path)

    if len(expected_right) != len(right_coords):
        raise ValueError(
            f'{pair_name} point count mismatch: '
            f'expected={len(expected_right)}, actual={len(right_coords)}'
        )

    for index, (expected, actual) in enumerate(zip(expected_right, right_coords)):
        if not np.allclose(expected, actual, atol=1e-6, rtol=0.0):
            raise ValueError(
                f'{pair_name} is not symmetric at point {index}: '
                f'expected={expected}, actual={actual}'
            )


def validate_symmetry(t1, t2, t3, t4, t5, t6, stubs):
    assert_mirror_pair(t1, t6, 't1/t6')
    assert_mirror_pair(t2, t5, 't2/t5')
    assert_mirror_pair(t3, t4, 't3/t4')

    stub_pairs = [
        ('left_ground', 'right_ground'),
        ('ground_4', 'ground_5'),
        ('ground_2', 'ground_6'),
    ]

    for left_name, right_name in stub_pairs:
        left_path = stubs[left_name]['path']
        right_path = stubs[right_name]['path']
        expected = [mirror_point_y_axis(p) for p in left_path]

        if not np.allclose(expected, right_path, atol=1e-6, rtol=0.0):
            raise ValueError(
                f'Ground stubs {left_name}/{right_name} are not symmetric: '
                f'expected={expected}, actual={right_path}'
            )

    print('Symmetry validation passed: t1/t6, t2/t5, t3/t4 and ground stubs.')


# ============================================================
# Main
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
            trace_gap=TRACE_GAP,
        ),
    )

    right_launch = LaunchpadWirebond(
        design,
        'right_launch',
        options=dict(
            pos_x='9.0mm',
            pos_y='-3mm',
            orientation='180',
            trace_width=TRACE_WIDTH,
            trace_gap=TRACE_GAP,
        ),
    )

    left_tie = normalize_point(left_launch.pins['tie']['middle'])
    right_tie = normalize_point(right_launch.pins['tie']['middle'])

    print(f'left_launch.tie  = {left_tie}')
    print(f'right_launch.tie = {right_tie}')

    t1, t2, t3, t4, t5, t6, stubs = generate_routes(
        left_tie,
        right_tie,
    )

    validate_symmetry(t1, t2, t3, t4, t5, t6, stubs)

    tree_config = [
        {'name': 'j1_to_j4', 'path': t1},
        {'name': 'j4_to_j2', 'path': t2},
        {'name': 'j2_to_j3', 'path': t3},
        {'name': 'j3_to_j6', 'path': t4},
        {'name': 'j6_to_j5', 'path': t5},
        {'name': 'j5_to_j7', 'path': t6},
    ] + [
        dict(name=name, **config)
        for name, config in stubs.items()
    ]

    tree = TreeRoute(
        design=design,
        name='test2',
        tree_config=tree_config,
        trace_width=TRACE_WIDTH,
        trace_gap=TRACE_GAP,
        fillet=FILLET,
        lead_in='0mm',
        lead_out='0mm',
    )

    print('TreeRoute created successfully.')

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

