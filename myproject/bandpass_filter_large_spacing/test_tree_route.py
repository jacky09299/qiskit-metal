import os
import numpy as np

from qiskit_metal import designs, MetalGUI
from qiskit_metal.qlibrary.terminations.launchpad_wb import LaunchpadWirebond

from components import TreeRoute


# ============================================================
# User Parameters
# All geometric values below are in mm.
# ============================================================

TRACE_WIDTH = '10um'
TRACE_GAP = '6um'
FILLET = '0um'
ENABLE_GUI = os.environ.get('ENABLE_GUI', 'True').lower() == 'true'

# Vertical depths of the lower, middle, and upper meanders.
a1 = 2.10
a2 = 2.00
a3 = 2.30

# b: horizontal width of each meander leg.
# c: vertical clearance between neighboring meander bands.
# d: horizontal half-spacing at the center and transition sections.
# n: number of U-shaped meander cells in each half-band.
b = 0.60
c = 0.85
d = 0.40
n = 4

# Seven independently controlled grounding-stub lengths.
# lp1/lp7: launchpad-side stubs.
# lp2/lp6: lower-to-middle junction stubs.
# lp3/lp5: middle-to-upper junction stubs.
# lp4: center stub.
lp1 = 1.13
lp2 = 0.10
lp3 = 0.21
lp4 = 0.10
lp5 = 0.21
lp6 = 0.10
lp7 = 1.13

# Fixed launchpad positions. The route itself reads the actual tie-pin centers.
LEFT_LAUNCH_X = -9.0
RIGHT_LAUNCH_X = 9.0
LAUNCH_Y = -3.0


# ============================================================
# Basic Helpers
# ============================================================

def point(value, digits=6):
    return [round(float(value[0]), digits), round(float(value[1]), digits)]


def is_coord(value):
    return isinstance(value, (list, tuple, np.ndarray)) and len(value) == 2


def mirror_point(value):
    value = point(value)
    return [round(-value[0], 6), value[1]]


def route_coords(path):
    return [point(item) for item in path if is_coord(item)]


def mirror_reverse_path(path, end_component=None, end_pin='tie'):
    """Mirror a left-side path about x=0 and reverse route direction."""
    result = [mirror_point(item) for item in reversed(route_coords(path))]
    if end_component is not None:
        result.append({'component': end_component, 'pin': end_pin})
    return result


def assert_positive_parameters():
    values = {
        'a1': a1, 'a2': a2, 'a3': a3,
        'b': b, 'c': c, 'd': d,
        'lp1': lp1, 'lp2': lp2, 'lp3': lp3, 'lp4': lp4,
        'lp5': lp5, 'lp6': lp6, 'lp7': lp7,
    }
    invalid = [name for name, value in values.items() if float(value) <= 0]
    if invalid:
        raise ValueError('Parameters must be positive: ' + ', '.join(invalid))
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError(f'n must be a positive integer, received {n!r}')


class PathBuilder:
    def __init__(self, start):
        self.current = point(start)
        self.path = [list(self.current)]

    def move(self, dx=0.0, dy=0.0):
        dx = float(dx)
        dy = float(dy)
        if abs(dx) > 1e-12 and abs(dy) > 1e-12:
            raise ValueError(f'Only orthogonal moves are allowed: dx={dx}, dy={dy}')
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

    def to_point(self, target, horizontal_first=True):
        target = point(target)
        if horizontal_first:
            self.to_x(target[0])
            self.to_y(target[1])
        else:
            self.to_y(target[1])
            self.to_x(target[0])
        return self


# ============================================================
# Meander Builder
# ============================================================

def add_horizontal_meander(builder, cells, step_x, depth, first_direction):
    """
    Add repeated rectangular U cells.

    Each cell occupies a horizontal width of 2*b. The route first moves one
    horizontal b segment, makes a vertical excursion of depth, moves another b,
    and returns to the original baseline except after the final cell when the
    caller requests a later transition.
    """
    vertical_sign = 1.0 if first_direction == 'up' else -1.0
    horizontal_sign = 1.0 if step_x > 0 else -1.0

    for _ in range(cells):
        builder.move(dx=horizontal_sign * b)
        builder.move(dy=vertical_sign * depth)
        builder.move(dx=horizontal_sign * b)
        builder.move(dy=-vertical_sign * depth)
    return builder


# ============================================================
# Geometry Generation
# ============================================================

def generate_routes(left_tie, right_tie):
    assert_positive_parameters()

    left_tie = point(left_tie)
    right_tie = point(right_tie)
    expected_right_tie = mirror_point(left_tie)

    if not np.allclose(right_tie, expected_right_tie, atol=1e-6, rtol=0.0):
        raise ValueError(
            'Launchpad tie pins are not mirror-symmetric: '
            f'left={left_tie}, right={right_tie}, expected={expected_right_tie}'
        )

    # Derived coordinates. The three left routes form the complete left half.
    # Right-side coordinates are never calculated independently.
    x_center_half = d
    x_inner = -x_center_half
    x_outer = x_inner - 2.0 * n * b

    y_lower = left_tie[1]
    y_middle = y_lower + a1 + c
    y_upper = y_middle + a2 + c

    j4 = point([x_inner, y_lower])
    j2 = point([x_outer, y_middle])
    j3 = point([0.0, y_upper])

    # Ensure the generated geometry remains inside the launchpads.
    if x_outer <= left_tie[0]:
        raise ValueError(
            'The left meander is wider than the available launchpad span. '
            f'x_outer={x_outer}, left_tie_x={left_tie[0]}. '
            'Reduce n or b, or move the launchpads outward.'
        )

    # --------------------------------------------------------
    # Lower-left band: left launch -> J4
    # --------------------------------------------------------
    lower_start_x = x_outer - 2.0 * b
    pb1 = PathBuilder(left_tie)
    pb1.path.insert(0, {'component': 'left_launch', 'pin': 'tie'})
    pb1.to_x(lower_start_x)

    # One entry cell plus n controlled cells, ending at the inner junction.
    add_horizontal_meander(pb1, n, step_x=1.0, depth=a1, first_direction='down')
    pb1.to_x(j4[0])
    pb1.to_y(j4[1])
    t1 = pb1.path

    # --------------------------------------------------------
    # Middle-left band: J4 -> J2
    # The route climbs by a1+c, then meanders from inside to outside.
    # --------------------------------------------------------
    pb2 = PathBuilder(j4)
    pb2.to_y(y_middle)
    add_horizontal_meander(pb2, n, step_x=-1.0, depth=a2, first_direction='down')
    pb2.to_x(j2[0])
    pb2.to_y(j2[1])
    t2 = pb2.path

    # --------------------------------------------------------
    # Upper-left band: J2 -> center J3
    # The route climbs by a2+c, then meanders toward the center.
    # --------------------------------------------------------
    pb3 = PathBuilder(j2)
    pb3.to_y(y_upper)
    add_horizontal_meander(pb3, n, step_x=1.0, depth=a3, first_direction='down')
    pb3.to_x(j3[0])
    pb3.to_y(j3[1])
    t3 = pb3.path

    # Exact mirror symmetry for the complete right half.
    t4 = mirror_reverse_path(t3)
    t5 = mirror_reverse_path(t2)
    t6 = mirror_reverse_path(t1, end_component='right_launch', end_pin='tie')

    if not np.allclose(t6[-2], right_tie, atol=1e-6, rtol=0.0):
        raise ValueError(
            f'Mirrored endpoint {t6[-2]} does not match right tie {right_tie}'
        )
    t6[-2] = list(right_tie)

    # Seven independent grounding stubs. Positive direction is upward for the
    # launchpad stubs; all internal stubs point downward as in the sketch.
    def stub(start, length, direction='down'):
        start = point(start)
        sign = -1.0 if direction == 'down' else 1.0
        return [start, [start[0], round(start[1] + sign * float(length), 6)]]

    j6 = mirror_point(j2)
    j5 = mirror_point(j4)

    stubs = {
        'ground_lp1': {'path': stub(left_tie, lp1, 'up'), 'end': 'short'},
        'ground_lp2': {'path': stub(j4, lp2, 'down'), 'end': 'short'},
        'ground_lp3': {'path': stub(j2, lp3, 'down'), 'end': 'short'},
        'ground_lp4': {'path': stub(j3, lp4, 'down'), 'end': 'short'},
        'ground_lp5': {'path': stub(j6, lp5, 'down'), 'end': 'short'},
        'ground_lp6': {'path': stub(j5, lp6, 'down'), 'end': 'short'},
        'ground_lp7': {'path': stub(right_tie, lp7, 'up'), 'end': 'short'},
    }

    nodes = {
        'left_tie': left_tie,
        'j4': j4,
        'j2': j2,
        'j3': j3,
        'j6': j6,
        'j5': j5,
        'right_tie': right_tie,
    }

    return (t1, t2, t3, t4, t5, t6), stubs, nodes


# ============================================================
# Validation
# ============================================================

def assert_mirror_pair(left_path, right_path, name):
    expected = [mirror_point(p) for p in reversed(route_coords(left_path))]
    actual = route_coords(right_path)
    if len(expected) != len(actual):
        raise ValueError(
            f'{name}: point count differs, expected {len(expected)}, got {len(actual)}'
        )
    for index, (expected_point, actual_point) in enumerate(zip(expected, actual)):
        if not np.allclose(expected_point, actual_point, atol=1e-6, rtol=0.0):
            raise ValueError(
                f'{name}: asymmetry at index {index}, '
                f'expected={expected_point}, actual={actual_point}'
            )


def validate_geometry(routes, stubs, nodes):
    t1, t2, t3, t4, t5, t6 = routes

    assert_mirror_pair(t1, t6, 'lower band t1/t6')
    assert_mirror_pair(t2, t5, 'middle band t2/t5')
    assert_mirror_pair(t3, t4, 'upper band t3/t4')

    expected_endpoints = [
        ('t1 end / t2 start', route_coords(t1)[-1], route_coords(t2)[0]),
        ('t2 end / t3 start', route_coords(t2)[-1], route_coords(t3)[0]),
        ('t3 end / t4 start', route_coords(t3)[-1], route_coords(t4)[0]),
        ('t4 end / t5 start', route_coords(t4)[-1], route_coords(t5)[0]),
        ('t5 end / t6 start', route_coords(t5)[-1], route_coords(t6)[0]),
    ]
    for name, p1, p2 in expected_endpoints:
        if not np.allclose(p1, p2, atol=1e-6, rtol=0.0):
            raise ValueError(f'{name} mismatch: {p1} != {p2}')

    stub_node_map = {
        'ground_lp1': 'left_tie',
        'ground_lp2': 'j4',
        'ground_lp3': 'j2',
        'ground_lp4': 'j3',
        'ground_lp5': 'j6',
        'ground_lp6': 'j5',
        'ground_lp7': 'right_tie',
    }
    for stub_name, node_name in stub_node_map.items():
        actual = stubs[stub_name]['path'][0]
        expected = nodes[node_name]
        if not np.allclose(actual, expected, atol=1e-6, rtol=0.0):
            raise ValueError(
                f'{stub_name} starts at {actual}, expected node {node_name}={expected}'
            )

    print('Geometry validation passed.')
    for name, coord in nodes.items():
        print(f'  {name:>10}: {coord}')


# ============================================================
# Main
# ============================================================

def main():
    design = designs.DesignPlanar(overwrite_enabled=True)
    design.chips.main.size.size_x = '22mm'
    design.chips.main.size.size_y = '14mm'

    left_launch = LaunchpadWirebond(
        design,
        'left_launch',
        options=dict(
            pos_x=f'{LEFT_LAUNCH_X}mm',
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
            pos_x=f'{RIGHT_LAUNCH_X}mm',
            pos_y=f'{LAUNCH_Y}mm',
            orientation='180',
            trace_width=TRACE_WIDTH,
            trace_gap=TRACE_GAP,
        ),
    )

    left_tie = point(left_launch.pins['tie']['middle'])
    right_tie = point(right_launch.pins['tie']['middle'])

    print(f'left_launch.tie  = {left_tie}')
    print(f'right_launch.tie = {right_tie}')

    routes, stubs, nodes = generate_routes(left_tie, right_tie)
    validate_geometry(routes, stubs, nodes)

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

