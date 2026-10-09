import os
import numpy as np

from qiskit_metal import designs, MetalGUI
from qiskit_metal.qlibrary.terminations.launchpad_wb import LaunchpadWirebond

from components import TreeRoute


# ============================================================
# User Parameters
# Geometry unit: mm
# ============================================================

TRACE_WIDTH = '10um'
TRACE_GAP = '6um'
FILLET = '0um'
ENABLE_GUI = os.environ.get('ENABLE_GUI', 'True').lower() == 'true'

# Vertical depth of the lower, middle, and upper meanders.
a1 = 2.10
a2 = 2.00
a3 = 2.30

# Horizontal geometry of one U cell:
#     b + 2*d + b
# Therefore one complete cell has width 2*b + 2*d.
b = 0.60
d = 0.40

# Vertical clearance between neighboring meander bands.
c = 0.85

# Vertical offset from the launchpad level to the lower-band baseline.
delta = 1.05

# Number of complete U cells in each half of each meander band.
n = 3

# Seven independent grounding-stub lengths.
lp1 = 1.13
lp2 = 0.08
lp3 = 0.21
lp4 = 0.10
lp5 = 0.21
lp6 = 0.08
lp7 = 1.13

# Launchpad vertical position.
LAUNCH_Y = -3.00

# LaunchpadWirebond tie pin is normally 0.025 mm inward from pos_x for
# the default component dimensions. The code verifies the real pin position
# after component creation and uses the real pin coordinates for all routes.
LAUNCH_TIE_INSET = 0.025


# ============================================================
# Basic Helpers
# ============================================================

def pt(value, digits=6):
    return [
        round(float(value[0]), digits),
        round(float(value[1]), digits),
    ]


def is_coord(value):
    return isinstance(value, (list, tuple, np.ndarray)) and len(value) == 2


def mirror_point(value):
    value = pt(value)
    return [round(-value[0], 6), value[1]]


def route_coords(path):
    return [pt(item) for item in path if is_coord(item)]


def mirror_reverse_path(path, end_component=None, end_pin='tie'):
    """Mirror a left route about x=0, then reverse its travel direction."""
    mirrored = [mirror_point(item) for item in reversed(route_coords(path))]
    if end_component is not None:
        mirrored.append({'component': end_component, 'pin': end_pin})
    return mirrored


def validate_parameters():
    positive = {
        'a1': a1, 'a2': a2, 'a3': a3,
        'b': b, 'c': c, 'd': d, 'delta': delta,
        'lp1': lp1, 'lp2': lp2, 'lp3': lp3, 'lp4': lp4,
        'lp5': lp5, 'lp6': lp6, 'lp7': lp7,
    }
    invalid = [name for name, value in positive.items() if float(value) <= 0]
    if invalid:
        raise ValueError('These parameters must be positive: ' + ', '.join(invalid))

    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError(f'n must be a positive integer, received {n!r}')


class PathBuilder:
    def __init__(self, start):
        self.current = pt(start)
        self.path = [list(self.current)]

    def move(self, dx=0.0, dy=0.0):
        dx = float(dx)
        dy = float(dy)

        if abs(dx) > 1e-12 and abs(dy) > 1e-12:
            raise ValueError(
                f'Only horizontal or vertical moves are allowed: dx={dx}, dy={dy}'
            )

        if abs(dx) <= 1e-12 and abs(dy) <= 1e-12:
            return self

        self.current = [
            round(self.current[0] + dx, 6),
            round(self.current[1] + dy, 6),
        ]
        self.path.append(list(self.current))
        return self

    def to_x(self, x):
        return self.move(dx=round(float(x) - self.current[0], 6))

    def to_y(self, y):
        return self.move(dy=round(float(y) - self.current[1], 6))


# ============================================================
# Meander Cell
# ============================================================

def add_u_cells(builder, count, x_direction, depth):
    """
    Add count complete downward U cells.

    For a right-moving cell:
        horizontal b
        vertical down a
        horizontal 2*d
        vertical up a
        horizontal b

    A left-moving cell is the exact horizontal mirror.
    Total width per cell is 2*b + 2*d.
    """
    sx = 1.0 if x_direction == 'right' else -1.0

    for _ in range(count):
        builder.move(dx=sx * b)
        builder.move(dy=-depth)
        builder.move(dx=sx * 2.0 * d)
        builder.move(dy=depth)
        builder.move(dx=sx * b)

    return builder


# ============================================================
# Derived Geometry
# ============================================================

def derive_geometry():
    """Derive all design coordinates from a1/a2/a3/b/c/d/delta/n."""
    validate_parameters()

    cell_width = 2.0 * b + 2.0 * d
    half_meander_width = n * cell_width

    # The inner lower/middle junctions are separated by exactly 2*d.
    j4_x = -d
    j5_x = d

    # The outer junctions are one half-meander width from the inner nodes.
    j2_x = j4_x - half_meander_width
    j6_x = -j2_x

    # The launch-to-first-meander horizontal segment is exactly 2*b.
    left_tie_x = j2_x - 2.0 * b
    right_tie_x = -left_tie_x

    # Baselines:
    # lower baseline is delta above launch level;
    # middle U bottoms remain c above the lower baseline;
    # upper U bottoms remain c above the middle baseline.
    y_lower = LAUNCH_Y + delta
    y_middle = y_lower + a2 + c
    y_upper = y_middle + a3 + c

    return {
        'cell_width': cell_width,
        'half_meander_width': half_meander_width,
        'left_tie_target': pt([left_tie_x, LAUNCH_Y]),
        'right_tie_target': pt([right_tie_x, LAUNCH_Y]),
        'j4': pt([j4_x, y_lower]),
        'j2': pt([j2_x, y_middle]),
        'j3': pt([0.0, y_upper]),
        'j6': pt([j6_x, y_middle]),
        'j5': pt([j5_x, y_lower]),
        'y_lower': round(y_lower, 6),
        'y_middle': round(y_middle, 6),
        'y_upper': round(y_upper, 6),
    }


# ============================================================
# Route Generation
# ============================================================

def generate_routes(left_tie, right_tie, geometry):
    left_tie = pt(left_tie)
    right_tie = pt(right_tie)

    if not np.allclose(right_tie, mirror_point(left_tie), atol=1e-6, rtol=0.0):
        raise ValueError(
            f'Launchpad ties are not symmetric: left={left_tie}, right={right_tie}'
        )

    j4 = geometry['j4']
    j2 = geometry['j2']
    j3 = geometry['j3']

    # --------------------------------------------------------
    # t1: left launch -> lower band -> J4
    # --------------------------------------------------------
    pb1 = PathBuilder(left_tie)
    pb1.path.insert(0, {'component': 'left_launch', 'pin': 'tie'})

    # Exactly 2*b from launch tie to the first vertical transition.
    lower_start_x = round(left_tie[0] + 2.0 * b, 6)
    pb1.to_x(lower_start_x)

    # delta independently controls launch level -> lower baseline.
    pb1.to_y(geometry['y_lower'])

    add_u_cells(pb1, n, x_direction='right', depth=a1)

    if not np.allclose(pb1.current, j4, atol=1e-6, rtol=0.0):
        raise ValueError(
            f't1 derived endpoint mismatch: actual={pb1.current}, expected j4={j4}'
        )
    t1 = pb1.path

    # --------------------------------------------------------
    # t2: J4 -> middle band -> J2
    # --------------------------------------------------------
    pb2 = PathBuilder(j4)
    pb2.to_y(geometry['y_middle'])
    add_u_cells(pb2, n, x_direction='left', depth=a2)

    if not np.allclose(pb2.current, j2, atol=1e-6, rtol=0.0):
        raise ValueError(
            f't2 derived endpoint mismatch: actual={pb2.current}, expected j2={j2}'
        )
    t2 = pb2.path

    # --------------------------------------------------------
    # t3: J2 -> upper band -> center J3
    # --------------------------------------------------------
    pb3 = PathBuilder(j2)
    pb3.to_y(geometry['y_upper'])
    add_u_cells(pb3, n, x_direction='right', depth=a3)

    # Last center segment is d. Together with its mirror it gives 2*d.
    pb3.to_x(0.0)

    if not np.allclose(pb3.current, j3, atol=1e-6, rtol=0.0):
        raise ValueError(
            f't3 derived endpoint mismatch: actual={pb3.current}, expected j3={j3}'
        )
    t3 = pb3.path

    # Right side is generated only by exact mirror transformation.
    t4 = mirror_reverse_path(t3)
    t5 = mirror_reverse_path(t2)
    t6 = mirror_reverse_path(t1, end_component='right_launch', end_pin='tie')

    if not np.allclose(t6[-2], right_tie, atol=1e-6, rtol=0.0):
        raise ValueError(
            f'Mirrored t6 endpoint {t6[-2]} does not match right tie {right_tie}'
        )
    t6[-2] = list(right_tie)

    # --------------------------------------------------------
    # Seven independent ground stubs
    # --------------------------------------------------------
    def stub(start, length, direction):
        start = pt(start)
        sign = 1.0 if direction == 'up' else -1.0
        return [
            start,
            [start[0], round(start[1] + sign * float(length), 6)],
        ]

    stubs = {
        'ground_lp1': {
            'path': stub(left_tie, lp1, 'up'),
            'end': 'short',
        },
        'ground_lp2': {
            'path': stub(geometry['j4'], lp2, 'down'),
            'end': 'short',
        },
        'ground_lp3': {
            'path': stub(geometry['j2'], lp3, 'down'),
            'end': 'short',
        },
        'ground_lp4': {
            'path': stub(geometry['j3'], lp4, 'down'),
            'end': 'short',
        },
        'ground_lp5': {
            'path': stub(geometry['j6'], lp5, 'down'),
            'end': 'short',
        },
        'ground_lp6': {
            'path': stub(geometry['j5'], lp6, 'down'),
            'end': 'short',
        },
        'ground_lp7': {
            'path': stub(right_tie, lp7, 'up'),
            'end': 'short',
        },
    }

    routes = (t1, t2, t3, t4, t5, t6)
    return routes, stubs


# ============================================================
# Validation
# ============================================================

def assert_mirror_pair(left_path, right_path, name):
    expected = [mirror_point(p) for p in reversed(route_coords(left_path))]
    actual = route_coords(right_path)

    if len(expected) != len(actual):
        raise ValueError(
            f'{name} point-count mismatch: expected={len(expected)}, actual={len(actual)}'
        )

    for index, (expected_pt, actual_pt) in enumerate(zip(expected, actual)):
        if not np.allclose(expected_pt, actual_pt, atol=1e-6, rtol=0.0):
            raise ValueError(
                f'{name} asymmetry at {index}: expected={expected_pt}, actual={actual_pt}'
            )


def validate_geometry(routes, stubs, geometry, left_tie, right_tie):
    t1, t2, t3, t4, t5, t6 = routes

    assert_mirror_pair(t1, t6, 't1/t6')
    assert_mirror_pair(t2, t5, 't2/t5')
    assert_mirror_pair(t3, t4, 't3/t4')

    connections = [
        ('t1->t2', route_coords(t1)[-1], route_coords(t2)[0]),
        ('t2->t3', route_coords(t2)[-1], route_coords(t3)[0]),
        ('t3->t4', route_coords(t3)[-1], route_coords(t4)[0]),
        ('t4->t5', route_coords(t4)[-1], route_coords(t5)[0]),
        ('t5->t6', route_coords(t5)[-1], route_coords(t6)[0]),
    ]

    for name, endpoint, startpoint in connections:
        if not np.allclose(endpoint, startpoint, atol=1e-6, rtol=0.0):
            raise ValueError(f'{name} mismatch: {endpoint} != {startpoint}')

    stub_starts = {
        'ground_lp1': left_tie,
        'ground_lp2': geometry['j4'],
        'ground_lp3': geometry['j2'],
        'ground_lp4': geometry['j3'],
        'ground_lp5': geometry['j6'],
        'ground_lp6': geometry['j5'],
        'ground_lp7': right_tie,
    }

    for name, expected in stub_starts.items():
        actual = stubs[name]['path'][0]
        if not np.allclose(actual, expected, atol=1e-6, rtol=0.0):
            raise ValueError(f'{name} start mismatch: {actual} != {expected}')

    # Verify the key dimensional intentions.
    first_lower_x = route_coords(t1)[1][0]
    if not np.isclose(first_lower_x - left_tie[0], 2.0 * b, atol=1e-6):
        raise ValueError('Launch-to-meander spacing is not 2*b')

    if not np.isclose(geometry['j5'][0] - geometry['j4'][0], 2.0 * d, atol=1e-6):
        raise ValueError('Center lower/middle junction spacing is not 2*d')

    print('Geometry validation passed.')
    print(f"  cell width       = {geometry['cell_width']} mm")
    print(f"  half width       = {geometry['half_meander_width']} mm")
    print(f"  lower baseline   = {geometry['y_lower']} mm")
    print(f"  middle baseline  = {geometry['y_middle']} mm")
    print(f"  upper baseline   = {geometry['y_upper']} mm")
    print(f"  J4/J5 center gap = {2.0 * d} mm")


# ============================================================
# Main
# ============================================================

def main():
    geometry = derive_geometry()

    # Place launchpads from the parameter-derived target tie coordinates.
    # The actual tie coordinates are read back immediately after creation.
    left_launch_pos_x = geometry['left_tie_target'][0] - LAUNCH_TIE_INSET
    right_launch_pos_x = geometry['right_tie_target'][0] + LAUNCH_TIE_INSET

    chip_width = 2.0 * max(abs(left_launch_pos_x), abs(right_launch_pos_x)) + 2.0
    chip_height = (
        geometry['y_upper'] - (geometry['y_lower'] - a1) + 4.0
    )

    design = designs.DesignPlanar(overwrite_enabled=True)
    design.chips.main.size.size_x = f'{chip_width}mm'
    design.chips.main.size.size_y = f'{chip_height}mm'

    left_launch = LaunchpadWirebond(
        design,
        'left_launch',
        options=dict(
            pos_x=f'{left_launch_pos_x}mm',
            pos_y=f'{LAUNCH_Y}mm',
            orientation='0',
            trace_width=TRACE_WIDTH,
            trace_gap=TRACE_GAP,
        ),
    )

    right_launch = LaunchpadWirebond(
        design,
        'right_launch',
        options=dict(
            pos_x=f'{right_launch_pos_x}mm',
            pos_y=f'{LAUNCH_Y}mm',
            orientation='180',
            trace_width=TRACE_WIDTH,
            trace_gap=TRACE_GAP,
        ),
    )

    left_tie = pt(left_launch.pins['tie']['middle'])
    right_tie = pt(right_launch.pins['tie']['middle'])

    print(f'left_launch.tie  = {left_tie}')
    print(f'right_launch.tie = {right_tie}')

    # Re-anchor target coordinates to the real Qiskit Metal pin centers while
    # retaining all parameter-derived widths and exact mirror symmetry.
    tie_error = left_tie[0] - geometry['left_tie_target'][0]
    if abs(tie_error) > 1e-6:
        raise ValueError(
            'Unexpected LaunchpadWirebond tie inset. '
            f'target={geometry["left_tie_target"]}, actual={left_tie}. '
            'Adjust LAUNCH_TIE_INSET to match this Qiskit Metal version.'
        )

    routes, stubs = generate_routes(left_tie, right_tie, geometry)
    validate_geometry(routes, stubs, geometry, left_tie, right_tie)

    t1, t2, t3, t4, t5, t6 = routes

    tree_config = [
        {'name': 'j1_to_j4', 'path': t1},
        {'name': 'j4_to_j2', 'path': t2},
        {'name': 'j2_to_j3', 'path': t3},
        {'name': 'j3_to_j6', 'path': t4},
        {'name': 'j6_to_j5', 'path': t5},
        {'name': 'j5_to_j7', 'path': t6},
    ] + [dict(name=name, **config) for name, config in stubs.items()]

    tree = TreeRoute(
        design=design,
        name='parameterized_filter',
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

