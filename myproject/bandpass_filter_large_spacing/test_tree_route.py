import os
import numpy as np

from qiskit_metal import designs, MetalGUI
from qiskit_metal.qlibrary.terminations.launchpad_wb import LaunchpadWirebond
from components import TreeRoute

# ============================================================
# User parameters (mm)
# ============================================================
TRACE_WIDTH = '10um'
TRACE_GAP = '6um'
FILLET = '0um'
ENABLE_GUI = os.environ.get('ENABLE_GUI', 'True').lower() == 'true'

a1 = 2.10                    # lower-row U depth
a2 = 2.00                    # middle-row U depth
a3 = 2.30                    # upper-row U depth
b = 0.60                     # every small horizontal segment
c = 0.85                     # clear vertical gap between adjacent rows
d = 0.40                     # half of the center opening, total opening = 2*d
delta = 1.05                 # vertical offset after the straight launch segment
n = 3                        # complete U periods in each half-row

# Ground-stub lengths, ordered from the leftmost node to the rightmost node.
lp1 = 1.13                   # left launch node
lp2 = 0.08                   # left outer node
lp3 = 0.21                   # left inner node
lp4 = 0.10                   # center node
lp5 = 0.21                   # right inner node
lp6 = 0.08                   # right outer node
lp7 = 1.13                   # right launch node

LAUNCH_Y = -3.00
LAUNCH_TIE_INSET = 0.025


# ============================================================
# Helpers
# ============================================================
def point(value):
    return [round(float(value[0]), 6), round(float(value[1]), 6)]


def is_coordinate(value):
    return isinstance(value, (list, tuple, np.ndarray)) and len(value) == 2


def path_coordinates(path):
    return [point(item) for item in path if is_coordinate(item)]


def mirror_point(value):
    value = point(value)
    return [round(-value[0], 6), value[1]]


def mirror_reverse_path(path, component=None, pin='tie'):
    result = [mirror_point(p) for p in reversed(path_coordinates(path))]
    if component is not None:
        result.append({'component': component, 'pin': pin})
    return result


class PathBuilder:
    def __init__(self, start):
        self.current = point(start)
        self.path = [list(self.current)]

    def move(self, dx=0.0, dy=0.0):
        dx = float(dx)
        dy = float(dy)
        if abs(dx) > 1e-12 and abs(dy) > 1e-12:
            raise ValueError(f'Only orthogonal movement is allowed: dx={dx}, dy={dy}')
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


def add_u_cells_from_horizontal(builder, count, direction, depth):
    """
    Add U cells beginning with a horizontal segment.

    Sequence for a right-moving cell:
        horizontal b
        vertical down depth
        horizontal b
        vertical up depth

    Used by the middle and upper rows.
    """
    sx = 1.0 if direction == 'right' else -1.0

    for _ in range(count):
        builder.move(dx=sx * b)
        builder.move(dy=-depth)
        builder.move(dx=sx * b)
        builder.move(dy=depth)

    return builder


def add_u_cells_from_vertical(builder, count, direction, depth):
    """
    Add U cells beginning with a vertical segment.

    Sequence for a right-moving cell:
        vertical down depth
        horizontal b
        vertical up depth
        horizontal b

    Used by the lower row so the endpoint of the launch 2*b line and delta
    transition is also the first vertical edge of the lower meander.
    """
    sx = 1.0 if direction == 'right' else -1.0

    for _ in range(count):
        builder.move(dy=-depth)
        builder.move(dx=sx * b)
        builder.move(dy=depth)
        builder.move(dx=sx * b)

    return builder


# ============================================================
# Parameter-derived geometry
# ============================================================
def derive_geometry():
    numeric = {
        'a1': a1, 'a2': a2, 'a3': a3, 'b': b, 'c': c,
        'd': d, 'delta': delta,
        'lp1': lp1, 'lp2': lp2, 'lp3': lp3, 'lp4': lp4,
        'lp5': lp5, 'lp6': lp6, 'lp7': lp7,
    }
    invalid = [name for name, value in numeric.items() if float(value) <= 0]
    if invalid:
        raise ValueError('Parameters must be positive: ' + ', '.join(invalid))
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError(f'n must be a positive integer, received {n!r}')

    half_row_width = n * 2.0 * b

    # Inner nodes are d from the center, giving a center opening of 2*d.
    j4_x = -d
    j5_x = d

    # Outer nodes are exactly n periods away from the inner nodes.
    j2_x = j4_x - half_row_width
    j6_x = -j2_x

    # Launch tie to the first lower-row vertical transition is exactly 2*b.
    left_tie_x = j2_x - 2.0 * b
    right_tie_x = -left_tie_x

    # The launch line stays at LAUNCH_Y. delta is applied only at its endpoint.
    lower_baseline = LAUNCH_Y + delta

    # c is the clear gap from the lower baseline to the bottom of middle U's,
    # and from the middle baseline to the bottom of upper U's.
    middle_baseline = lower_baseline + a2 + c
    upper_baseline = middle_baseline + a3 + c

    return {
        'left_tie': point([left_tie_x, LAUNCH_Y]),
        'left_outer': point([j2_x, middle_baseline]),
        'left_inner': point([j4_x, lower_baseline]),
        'center': point([0.0, upper_baseline]),
        'right_inner': point([j5_x, lower_baseline]),
        'right_outer': point([j6_x, middle_baseline]),
        'right_tie': point([right_tie_x, LAUNCH_Y]),
        'lower_baseline': round(lower_baseline, 6),
        'middle_baseline': round(middle_baseline, 6),
        'upper_baseline': round(upper_baseline, 6),
    }


# ============================================================
# Route generation
# ============================================================
def generate_routes(left_tie, right_tie, geometry):
    left_tie = point(left_tie)
    right_tie = point(right_tie)

    if not np.allclose(right_tie, mirror_point(left_tie), atol=1e-6, rtol=0.0):
        raise ValueError(f'Launch ties are not symmetric: {left_tie}, {right_tie}')

    # t1: left launch -> straight 2b -> delta -> lower row -> left inner node.
    p1 = PathBuilder(left_tie)
    p1.path.insert(0, {'component': 'left_launch', 'pin': 'tie'})
    p1.move(dx=2.0 * b)                  # uninterrupted launch line

    # Merge the former +delta and -a1 movements into one vertical segment.
    # This prevents RouteAnchors from retracing the same X coordinate.
    p1.move(dy=delta - a1)
    p1.move(dx=b)
    p1.move(dy=a1)
    p1.move(dx=b)

    # Remaining lower-row cells keep the vertical-first phase.
    if n > 1:
        add_u_cells_from_vertical(p1, n - 1, 'right', a1)
    if not np.allclose(p1.current, geometry['left_inner'], atol=1e-6):
        raise ValueError(f't1 endpoint {p1.current} != {geometry["left_inner"]}')
    t1 = p1.path

    # t2: left inner node -> middle baseline -> middle row toward outside.
    # The first operation is vertical, so the red node lies on one straight
    # vertical transition with no horizontal notch.
    p2 = PathBuilder(geometry['left_inner'])
    p2.to_y(geometry['middle_baseline'])
    add_u_cells_from_horizontal(p2, n, 'left', a2)
    if not np.allclose(p2.current, geometry['left_outer'], atol=1e-6):
        raise ValueError(f't2 endpoint {p2.current} != {geometry["left_outer"]}')
    t2 = p2.path

    # t3: left outer node -> upper baseline -> upper row -> center.
    # The final d section and its mirror form the center opening 2*d.
    p3 = PathBuilder(geometry['left_outer'])
    p3.to_y(geometry['upper_baseline'])
    add_u_cells_from_horizontal(p3, n, 'right', a3)
    p3.move(dx=d)
    if not np.allclose(p3.current, geometry['center'], atol=1e-6):
        raise ValueError(f't3 endpoint {p3.current} != {geometry["center"]}')
    t3 = p3.path

    # Exact right-side mirror.
    t4 = mirror_reverse_path(t3)
    t5 = mirror_reverse_path(t2)
    t6 = mirror_reverse_path(t1, component='right_launch', pin='tie')
    if not np.allclose(t6[-2], right_tie, atol=1e-6):
        raise ValueError(f't6 endpoint {t6[-2]} != right tie {right_tie}')
    t6[-2] = list(right_tie)

    def vertical_stub(start, length, direction):
        start = point(start)
        sign = 1.0 if direction == 'up' else -1.0
        return [start, [start[0], round(start[1] + sign * float(length), 6)]]

    # lp1..lp7 follow the seven nodes from left to right.
    stubs = {
        'ground_lp1': {'path': vertical_stub(left_tie, lp1, 'up'), 'end': 'short'},
        'ground_lp2': {'path': vertical_stub(geometry['left_outer'], lp2, 'down'), 'end': 'short'},
        'ground_lp3': {'path': vertical_stub(geometry['left_inner'], lp3, 'down'), 'end': 'short'},
        'ground_lp4': {'path': vertical_stub(geometry['center'], lp4, 'down'), 'end': 'short'},
        'ground_lp5': {'path': vertical_stub(geometry['right_inner'], lp5, 'down'), 'end': 'short'},
        'ground_lp6': {'path': vertical_stub(geometry['right_outer'], lp6, 'down'), 'end': 'short'},
        'ground_lp7': {'path': vertical_stub(right_tie, lp7, 'up'), 'end': 'short'},
    }

    return (t1, t2, t3, t4, t5, t6), stubs


# ============================================================
# Geometry checks
# ============================================================
def validate_geometry(routes, geometry, left_tie, right_tie):
    t1, t2, t3, t4, t5, t6 = routes

    # Mirror symmetry checks.
    for left, right, name in (
        (t1, t6, 't1/t6'),
        (t2, t5, 't2/t5'),
        (t3, t4, 't3/t4'),
    ):
        expected = [mirror_point(p) for p in reversed(path_coordinates(left))]
        actual = path_coordinates(right)
        if len(expected) != len(actual) or not np.allclose(expected, actual, atol=1e-6):
            raise ValueError(f'{name} mirror validation failed')

    # Main-route connectivity.
    pairs = (
        (t1, t2, 't1/t2'), (t2, t3, 't2/t3'),
        (t3, t4, 't3/t4'), (t4, t5, 't4/t5'), (t5, t6, 't5/t6'),
    )
    for first, second, name in pairs:
        if not np.allclose(path_coordinates(first)[-1], path_coordinates(second)[0], atol=1e-6):
            raise ValueError(f'{name} endpoint mismatch')

    # Launch segment must be a single straight horizontal 2*b segment.
    lower = path_coordinates(t1)
    first_dx = lower[1][0] - lower[0][0]
    first_dy = lower[1][1] - lower[0][1]
    if not np.isclose(first_dx, 2.0 * b) or not np.isclose(first_dy, 0.0):
        raise ValueError('Left launch segment must be one horizontal 2*b segment')

    # The first lower-row vertical edge combines delta and -a1.
    # It must be one non-retracing segment with displacement delta - a1.
    first_vertical_dx = lower[2][0] - lower[1][0]
    first_vertical_dy = lower[2][1] - lower[1][1]
    if not np.isclose(first_vertical_dx, 0.0, atol=1e-6) or not np.isclose(
        first_vertical_dy, delta - a1, atol=1e-6
    ):
        raise ValueError(
            'First lower vertical segment must equal delta - a1 without retracing'
        )

    # The next three segments complete the first lower U cell.
    expected_first_cell = [
        (b, 0.0),
        (0.0, a1),
        (b, 0.0),
    ]
    for index, (expected_dx, expected_dy) in enumerate(expected_first_cell, start=2):
        actual_dx = lower[index + 1][0] - lower[index][0]
        actual_dy = lower[index + 1][1] - lower[index][1]
        if not np.isclose(actual_dx, expected_dx, atol=1e-6) or not np.isclose(
            actual_dy, expected_dy, atol=1e-6
        ):
            raise ValueError(
                f'Invalid first lower U segment at index {index}: '
                f'actual=({actual_dx}, {actual_dy})'
            )

    # Every ordinary meander horizontal segment must have width b.
    # The only exceptions are launch 2*b and center d.
    for route, name in ((t1, 't1'), (t2, 't2'), (t3, 't3')):
        route_points = path_coordinates(route)
        for index, (p0, p1) in enumerate(zip(route_points, route_points[1:])):
            dx = abs(p1[0] - p0[0])
            dy = abs(p1[1] - p0[1])
            if dx > 1e-9 and dy <= 1e-9:
                allowed = np.isclose(dx, b, atol=1e-6)
                if name == 't1' and index == 0:
                    allowed = np.isclose(dx, 2.0 * b, atol=1e-6)
                if name == 't3' and index == len(route_points) - 2:
                    allowed = np.isclose(dx, d, atol=1e-6)
                if not allowed:
                    raise ValueError(f'{name} horizontal segment {index} has width {dx}')

    if not np.isclose(
        geometry['right_inner'][0] - geometry['left_inner'][0],
        2.0 * d,
        atol=1e-6,
    ):
        raise ValueError('Center width is not 2*d')

    print('Geometry validation passed.')
    print(f'  U period = 2*b = {2*b} mm')
    print(f'  each small horizontal segment b = {b} mm')
    print(f'  launch straight length = 2*b = {2*b} mm')
    print(f'  center opening = 2*d = {2*d} mm')
    print(f'  delta = {delta} mm')


# ============================================================
# Main
# ============================================================
def main():
    geometry = derive_geometry()

    left_launch_x = geometry['left_tie'][0] - LAUNCH_TIE_INSET
    right_launch_x = geometry['right_tie'][0] + LAUNCH_TIE_INSET

    design = designs.DesignPlanar(overwrite_enabled=True)
    chip_width = 2.0 * abs(left_launch_x) + 2.0
    chip_height = max(14.0, geometry['upper_baseline'] - (LAUNCH_Y - a1) + 4.0)
    design.chips.main.size.size_x = f'{chip_width}mm'
    design.chips.main.size.size_y = f'{chip_height}mm'

    left_launch = LaunchpadWirebond(
        design,
        'left_launch',
        options=dict(
            pos_x=f'{left_launch_x}mm', pos_y=f'{LAUNCH_Y}mm',
            orientation='0', trace_width=TRACE_WIDTH, trace_gap=TRACE_GAP,
        ),
    )
    right_launch = LaunchpadWirebond(
        design,
        'right_launch',
        options=dict(
            pos_x=f'{right_launch_x}mm', pos_y=f'{LAUNCH_Y}mm',
            orientation='180', trace_width=TRACE_WIDTH, trace_gap=TRACE_GAP,
        ),
    )

    left_tie = point(left_launch.pins['tie']['middle'])
    right_tie = point(right_launch.pins['tie']['middle'])
    print('left_launch.tie  =', left_tie)
    print('right_launch.tie =', right_tie)

    if not np.allclose(left_tie, geometry['left_tie'], atol=1e-6):
        raise ValueError(
            'Launchpad tie offset differs in this Qiskit Metal version. '
            'Adjust LAUNCH_TIE_INSET.'
        )

    routes, stubs = generate_routes(left_tie, right_tie, geometry)
    validate_geometry(routes, geometry, left_tie, right_tie)
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
        name='overlap_fixed_filter',
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

