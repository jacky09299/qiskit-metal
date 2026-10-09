import os
import numpy as np

from qiskit_metal import designs, MetalGUI
from qiskit_metal.qlibrary.terminations.launchpad_wb import LaunchpadWirebond
from components import TreeRoute

# ============================================================
# Parameters, unit: mm
# ============================================================
TRACE_WIDTH = '10um'
TRACE_GAP = '6um'
FILLET = '0um'
ENABLE_GUI = os.environ.get('ENABLE_GUI', 'True').lower() == 'true'

a1 = 2.10
a2 = 2.00
a3 = 2.30
b = 0.60
c = 0.85
d = 0.40
delta = 1.05
n = 3

lp1 = 1.13
lp2 = 0.08
lp3 = 0.21
lp4 = 0.10
lp5 = 0.21
lp6 = 0.08
lp7 = 1.13

LAUNCH_Y = -3.00
LAUNCH_TIE_INSET = 0.025


def pt(value):
    return [round(float(value[0]), 6), round(float(value[1]), 6)]


def is_coord(value):
    return isinstance(value, (list, tuple, np.ndarray)) and len(value) == 2


def coords(path):
    return [pt(item) for item in path if is_coord(item)]


def mirror_point(value):
    value = pt(value)
    return [-value[0], value[1]]


def mirror_reverse(path, component=None, pin='tie'):
    result = [mirror_point(item) for item in reversed(coords(path))]
    if component:
        result.append({'component': component, 'pin': pin})
    return result


class PathBuilder:
    def __init__(self, start):
        self.now = pt(start)
        self.path = [list(self.now)]

    def move(self, dx=0.0, dy=0.0):
        dx, dy = float(dx), float(dy)
        if abs(dx) > 1e-12 and abs(dy) > 1e-12:
            raise ValueError('Only orthogonal moves are allowed')
        if abs(dx) <= 1e-12 and abs(dy) <= 1e-12:
            return self
        self.now = [round(self.now[0] + dx, 6), round(self.now[1] + dy, 6)]
        self.path.append(list(self.now))
        return self

    def to_x(self, x):
        return self.move(dx=round(float(x) - self.now[0], 6))

    def to_y(self, y):
        return self.move(dy=round(float(y) - self.now[1], 6))


def add_u_cells(builder, count, direction, depth):
    """Every horizontal segment in a U cell is exactly b."""
    sx = 1.0 if direction == 'right' else -1.0
    for _ in range(count):
        builder.move(dx=sx * b)
        builder.move(dy=-depth)
        builder.move(dx=sx * b)
        builder.move(dy=depth)
    return builder


def derive_geometry():
    if n < 1 or not isinstance(n, int):
        raise ValueError('n must be a positive integer')

    cell_width = 2.0 * b
    half_width = n * cell_width

    # Inner nodes have center separation 2*d.
    j4_x = -d
    j5_x = d
    j2_x = j4_x - half_width
    j6_x = -j2_x

    # Red launch segment is one straight horizontal section of length 2*b.
    left_tie_x = j2_x - 2.0 * b
    right_tie_x = -left_tie_x

    # delta is applied only after the straight launch segment.
    y_lower = LAUNCH_Y + delta
    # Keep c as the clear vertical gap between adjacent meander bands.
    y_middle = y_lower + a2 + c
    y_upper = y_middle + a3 + c

    return {
        'left_tie': pt([left_tie_x, LAUNCH_Y]),
        'right_tie': pt([right_tie_x, LAUNCH_Y]),
        'j4': pt([j4_x, y_lower]),
        'j2': pt([j2_x, y_middle]),
        'j3': pt([0.0, y_upper]),
        'j6': pt([j6_x, y_middle]),
        'j5': pt([j5_x, y_lower]),
        'y_lower': y_lower,
        'y_middle': y_middle,
        'y_upper': y_upper,
    }


def generate_routes(left_tie, right_tie, g):
    left_tie, right_tie = pt(left_tie), pt(right_tie)

    # t1: straight red 2*b, then delta, then lower meander.
    p1 = PathBuilder(left_tie)
    p1.path.insert(0, {'component': 'left_launch', 'pin': 'tie'})
    p1.move(dx=2.0 * b)
    p1.move(dy=delta)
    add_u_cells(p1, n, 'right', a1)
    if not np.allclose(p1.now, g['j4']):
        raise ValueError(f't1 endpoint {p1.now} != J4 {g["j4"]}')
    t1 = p1.path

    # t2: middle meander, all horizontal pieces b.
    p2 = PathBuilder(g['j4'])
    p2.to_y(g['y_middle'])
    add_u_cells(p2, n, 'left', a2)
    if not np.allclose(p2.now, g['j2']):
        raise ValueError(f't2 endpoint {p2.now} != J2 {g["j2"]}')
    t2 = p2.path

    # t3: upper meander, all horizontal pieces b, then center d.
    p3 = PathBuilder(g['j2'])
    p3.to_y(g['y_upper'])
    add_u_cells(p3, n, 'right', a3)
    p3.move(dx=d)
    if not np.allclose(p3.now, g['j3']):
        raise ValueError(f't3 endpoint {p3.now} != J3 {g["j3"]}')
    t3 = p3.path

    t4 = mirror_reverse(t3)
    t5 = mirror_reverse(t2)
    t6 = mirror_reverse(t1, 'right_launch', 'tie')
    t6[-2] = list(right_tie)

    def stub(start, length, direction):
        start = pt(start)
        sign = 1.0 if direction == 'up' else -1.0
        return [start, [start[0], round(start[1] + sign * length, 6)]]

    stubs = {
        'ground_lp1': {'path': stub(left_tie, lp1, 'up'), 'end': 'short'},
        'ground_lp2': {'path': stub(g['j4'], lp2, 'down'), 'end': 'short'},
        'ground_lp3': {'path': stub(g['j2'], lp3, 'down'), 'end': 'short'},
        'ground_lp4': {'path': stub(g['j3'], lp4, 'down'), 'end': 'short'},
        'ground_lp5': {'path': stub(g['j6'], lp5, 'down'), 'end': 'short'},
        'ground_lp6': {'path': stub(g['j5'], lp6, 'down'), 'end': 'short'},
        'ground_lp7': {'path': stub(right_tie, lp7, 'up'), 'end': 'short'},
    }
    return (t1, t2, t3, t4, t5, t6), stubs


def validate(routes, g, left_tie, right_tie):
    t1, t2, t3, t4, t5, t6 = routes

    # Exact mirror validation.
    for left, right, name in [(t1, t6, 't1/t6'), (t2, t5, 't2/t5'), (t3, t4, 't3/t4')]:
        expected = [mirror_point(p) for p in reversed(coords(left))]
        actual = coords(right)
        if len(expected) != len(actual) or not np.allclose(expected, actual):
            raise ValueError(f'{name} mirror validation failed')

    # Red segment is horizontal, uninterrupted, and exactly 2*b.
    t1c = coords(t1)
    if not (np.isclose(t1c[0][1], t1c[1][1]) and
            np.isclose(t1c[1][0] - t1c[0][0], 2.0 * b)):
        raise ValueError('Left red segment must be a straight horizontal 2*b line')

    # All internal U-cell horizontal segments are b.
    for path, name in [(t1, 't1'), (t2, 't2'), (t3, 't3')]:
        pc = coords(path)
        for p0, p1 in zip(pc, pc[1:]):
            dx, dy = abs(p1[0] - p0[0]), abs(p1[1] - p0[1])
            if dx > 1e-9 and dy < 1e-9:
                allowed = np.isclose(dx, b) or np.isclose(dx, 2*b) or np.isclose(dx, d)
                if not allowed:
                    raise ValueError(f'{name}: invalid horizontal width {dx}')

    print('Validation passed: red launch lines are straight 2*b; U widths are b.')


def main():
    g = derive_geometry()

    left_pos_x = g['left_tie'][0] - LAUNCH_TIE_INSET
    right_pos_x = g['right_tie'][0] + LAUNCH_TIE_INSET

    design = designs.DesignPlanar(overwrite_enabled=True)
    design.chips.main.size.size_x = f'{2 * abs(left_pos_x) + 2.0}mm'
    design.chips.main.size.size_y = '14mm'

    left_launch = LaunchpadWirebond(
        design, 'left_launch',
        options=dict(pos_x=f'{left_pos_x}mm', pos_y=f'{LAUNCH_Y}mm',
                     orientation='0', trace_width=TRACE_WIDTH, trace_gap=TRACE_GAP)
    )
    right_launch = LaunchpadWirebond(
        design, 'right_launch',
        options=dict(pos_x=f'{right_pos_x}mm', pos_y=f'{LAUNCH_Y}mm',
                     orientation='180', trace_width=TRACE_WIDTH, trace_gap=TRACE_GAP)
    )

    left_tie = pt(left_launch.pins['tie']['middle'])
    right_tie = pt(right_launch.pins['tie']['middle'])
    print('left_launch.tie =', left_tie)
    print('right_launch.tie =', right_tie)

    if not np.allclose(left_tie, g['left_tie'], atol=1e-6):
        raise ValueError('Adjust LAUNCH_TIE_INSET for this Qiskit Metal version')

    routes, stubs = generate_routes(left_tie, right_tie, g)
    validate(routes, g, left_tie, right_tie)
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
        design=design, name='parameterized_filter_latest', tree_config=tree_config,
        trace_width=TRACE_WIDTH, trace_gap=TRACE_GAP, fillet=FILLET,
        lead_in='0mm', lead_out='0mm'
    )

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

