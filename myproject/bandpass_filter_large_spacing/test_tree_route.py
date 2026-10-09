import os

from qiskit_metal import designs
try:
    from qiskit_metal import MetalGUI
except ImportError:
    MetalGUI = None

from components import TreeRoute

TRACE_WIDTH = '10um'
TRACE_GAP = '6um'
FILLET = '17um'
ENABLE_GUI = os.environ.get('ENABLE_GUI', 'True').lower() == 'true'

a1 = 2.10
a2 = 2.00
a3 = 2.30
b = 0.40
c = 0.85
d = 0.20
delta = -0.1
n = 5

lp1 = 1.13
lp2 = 0.08
lp3 = 0.21
lp4 = 0.10
lp5 = 0.21
lp6 = 0.08
lp7 = 1.13

LAUNCH_Y = -3.00
LAUNCH_TIE_INSET = 0.025


def point(value):
    return [round(float(value[0]), 6), round(float(value[1]), 6)]


def path_coordinates(path):
    return [
        point(item)
        for item in path
        if isinstance(item, (list, tuple)) and len(item) == 2
    ]


def mirror_point(value):
    val = point(value)
    return [round(-val[0], 6), val[1]]


def mirror_reverse_path(path, component=None, pin='tie'):
    result = [mirror_point(item) for item in reversed(path_coordinates(path))]
    if component is not None:
        result.append({'component': component, 'pin': pin})
    return result


class PathBuilder:
    """Intuitive path builder using relative directional moves."""

    def __init__(self, start):
        self.current = point(start)
        self.path = [list(self.current)]

    def move(self, dx=0.0, dy=0.0):
        dx = float(dx)
        dy = float(dy)
        if abs(dx) > 1e-12 and abs(dy) > 1e-12:
            raise ValueError('Only horizontal or vertical moves are allowed')
        if abs(dx) <= 1e-12 and abs(dy) <= 1e-12:
            return self
        self.current = [
            round(self.current[0] + dx, 6),
            round(self.current[1] + dy, 6),
        ]
        self.path.append(list(self.current))
        return self

    def right(self, dist):
        return self.move(dx=dist)

    def left(self, dist):
        return self.move(dx=-dist)

    def up(self, dist):
        return self.move(dy=dist)

    def down(self, dist):
        return self.move(dy=-dist)

    def to_y(self, y):
        return self.move(dy=round(float(y) - self.current[1], 6))


def derive_geometry():
    half_row_width = n * 2.0 * b

    j4_x = -d
    j5_x = d
    j2_x = j4_x - half_row_width
    j6_x = -j2_x

    left_tie_x = j2_x - 2.0 * b
    right_tie_x = -left_tie_x

    lower_baseline = LAUNCH_Y + delta
    middle_baseline = lower_baseline + a2 + c
    upper_baseline = middle_baseline + a3 + c

    # Blue-circle nodes: one b outside the normal middle-row endpoint.
    left_shared_x = j2_x - b
    right_shared_x = j6_x + b

    return {
        'left_tie': point([left_tie_x, LAUNCH_Y]),
        'left_outer': point([j2_x, middle_baseline]),
        'left_shared': point([left_shared_x, middle_baseline]),
        'left_inner': point([j4_x, lower_baseline]),
        'center': point([0.0, upper_baseline]),
        'right_inner': point([j5_x, lower_baseline]),
        'right_outer': point([j6_x, middle_baseline]),
        'right_shared': point([right_shared_x, middle_baseline]),
        'right_tie': point([right_tie_x, LAUNCH_Y]),
        'lower_baseline': round(lower_baseline, 6),
        'middle_baseline': round(middle_baseline, 6),
        'upper_baseline': round(upper_baseline, 6),
    }


def generate_routes(left_tie, right_tie, geometry):
    left_tie = point(left_tie)
    right_tie = point(right_tie)

    # Lower row (t1): start at launch tie, move down-right with n U-cells to inner node.
    p1 = PathBuilder(left_tie)
    p1.path.insert(0, {'component': 'left_launch', 'pin': 'tie'})
    p1.right(2.0 * b).down(a1 - delta).right(b).up(a1).right(b)
    for _ in range(n - 1):
        p1.down(a1).right(b).up(a1).right(b)
    t1 = p1.path

    # Middle row (t2): start at inner node, rise to middle baseline, move left with n U-cells to shared node.
    p2 = PathBuilder(geometry['left_inner'])
    p2.to_y(geometry['middle_baseline'])
    for _ in range(n):
        p2.left(b).down(a2).left(b).up(a2)
    p2.left(b)
    if p2.current != geometry['left_shared']:
        raise ValueError(
            f'Middle endpoint {p2.current} != shared node {geometry["left_shared"]}'
        )
    t2 = p2.path

    # Upper row (t3): start at shared node, rise to upper baseline, move right with n U-cells to center.
    p3 = PathBuilder(geometry['left_shared'])
    p3.to_y(geometry['upper_baseline'])
    for _ in range(n):
        p3.right(b).down(a3).right(b).up(a3)
    p3.right(b + d)
    if p3.current != geometry['center']:
        raise ValueError(
            f'Upper endpoint {p3.current} != center {geometry["center"]}'
        )
    t3 = p3.path

    # Mirror routes for the right half of the symmetric structure.
    t4 = mirror_reverse_path(t3)
    t5 = mirror_reverse_path(t2)
    t6 = mirror_reverse_path(t1, component='right_launch', pin='tie')
    t6[-2] = list(right_tie)

    # Ground stubs attached to junction nodes.
    stubs = {
        'ground_lp1': {
            'path': [left_tie, [left_tie[0], round(left_tie[1] + lp1, 6)]],
            'end': 'short',
        },
        'ground_lp2': {
            'path': [
                geometry['left_shared'],
                [geometry['left_shared'][0], round(geometry['left_shared'][1] - lp2, 6)],
            ],
            'end': 'short',
        },
        'ground_lp3': {
            'path': [
                geometry['left_inner'],
                [geometry['left_inner'][0], round(geometry['left_inner'][1] - lp3, 6)],
            ],
            'end': 'short',
        },
        'ground_lp4': {
            'path': [
                geometry['center'],
                [geometry['center'][0], round(geometry['center'][1] - lp4, 6)],
            ],
            'end': 'short',
        },
        'ground_lp5': {
            'path': [
                geometry['right_inner'],
                [geometry['right_inner'][0], round(geometry['right_inner'][1] - lp5, 6)],
            ],
            'end': 'short',
        },
        'ground_lp6': {
            'path': [
                geometry['right_shared'],
                [geometry['right_shared'][0], round(geometry['right_shared'][1] - lp6, 6)],
            ],
            'end': 'short',
        },
        'ground_lp7': {
            'path': [right_tie, [right_tie[0], round(right_tie[1] + lp7, 6)]],
            'end': 'short',
        },
    }

    # Shared-junction consistency checks.
    if path_coordinates(t2)[-1] != geometry['left_shared']:
        raise ValueError('t2 does not end at left shared junction')
    if path_coordinates(t3)[0] != geometry['left_shared']:
        raise ValueError('t3 does not start at left shared junction')
    if stubs['ground_lp2']['path'][0] != geometry['left_shared']:
        raise ValueError('ground_lp2 does not start at left shared junction')

    return (t1, t2, t3, t4, t5, t6), stubs


def main():
    geometry = derive_geometry()

    left_launch_x = geometry['left_tie'][0] - LAUNCH_TIE_INSET
    right_launch_x = geometry['right_tie'][0] + LAUNCH_TIE_INSET

    design = designs.DesignPlanar(overwrite_enabled=True)
    chip_width = 2.0 * abs(left_launch_x) + 2.0
    chip_height = max(
        14.0,
        geometry['upper_baseline'] - (LAUNCH_Y - a1) + 4.0,
    )
    design.chips.main.size.size_x = f'{chip_width}mm'
    design.chips.main.size.size_y = f'{chip_height}mm'

    from qiskit_metal.qlibrary.terminations.launchpad_wb import LaunchpadWirebond

    left_launch = LaunchpadWirebond(
        design,
        'left_launch',
        options=dict(
            pos_x=f'{left_launch_x}mm',
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
            pos_x=f'{right_launch_x}mm',
            pos_y=f'{LAUNCH_Y}mm',
            orientation='180',
            trace_width=TRACE_WIDTH,
            trace_gap=TRACE_GAP,
        ),
    )

    left_tie = point(left_launch.pins['tie']['middle'])
    right_tie = point(right_launch.pins['tie']['middle'])

    routes, stubs = generate_routes(left_tie, right_tie, geometry)
    t1, t2, t3, t4, t5, t6 = routes

    tree_config = [
        {'name': 'j1_to_j4', 'path': t1},
        {'name': 'j4_to_j2', 'path': t2},
        {'name': 'j2_to_j3', 'path': t3},
        {'name': 'j3_to_j6', 'path': t4},
        {'name': 'j6_to_j5', 'path': t5},
        {'name': 'j5_to_j7', 'path': t6},
    ]
    tree_config += [dict(name=name, **config) for name, config in stubs.items()]

    tree = TreeRoute(
        design=design,
        name='shared_junction_fixed_filter',
        tree_config=tree_config,
        trace_width=TRACE_WIDTH,
        trace_gap=TRACE_GAP,
        fillet=FILLET,
        lead_in='0mm',
        lead_out='0mm',
    )

    if ENABLE_GUI and MetalGUI is not None:
        gui = MetalGUI(design)
        gui.rebuild()
        gui.autoscale()
        gui.main_window.show()
        gui.qApp.exec_()

    return design, tree


if __name__ == '__main__':
    main()
