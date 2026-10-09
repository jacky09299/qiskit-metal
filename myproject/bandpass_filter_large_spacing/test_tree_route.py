import os

from qiskit_metal import designs, MetalGUI
from qiskit_metal.qlibrary.terminations.launchpad_wb import LaunchpadWirebond
from components import TreeRoute


# ============================================================
# User parameters (mm)
# ============================================================
TRACE_WIDTH = '10um'
TRACE_GAP = '6um'
FILLET = '17um'
ENABLE_GUI = os.environ.get('ENABLE_GUI', 'True').lower() == 'true'

a1 = 2.10                    # lower-row U depth
a2 = 2.00                    # middle-row U depth
a3 = 2.30                    # upper-row U depth
b = 0.40                     # every small horizontal segment
c = 0.85                     # clear vertical gap between adjacent rows
d = 0.2                     # half of the center opening, total opening = 2*d
delta = 0                # vertical offset after the straight launch segment
n = 5                        # complete U periods in each half-row

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
    return [
        round(float(value[0]), 6),
        round(float(value[1]), 6),
    ]


def path_coordinates(path):
    return [
        point(item)
        for item in path
        if isinstance(item, (list, tuple)) and len(item) == 2
    ]


def mirror_point(value):
    value = point(value)
    return [
        round(-value[0], 6),
        value[1],
    ]


def mirror_reverse_path(path, component=None, pin='tie'):
    result = [
        mirror_point(item)
        for item in reversed(path_coordinates(path))
    ]

    if component is not None:
        result.append({
            'component': component,
            'pin': pin,
        })

    return result


class PathBuilder:
    def __init__(self, start):
        self.current = point(start)
        self.path = [list(self.current)]

    def move(self, dx=0.0, dy=0.0):
        self.current = [
            round(self.current[0] + float(dx), 6),
            round(self.current[1] + float(dy), 6),
        ]
        self.path.append(list(self.current))
        return self

    def to_x(self, x):
        return self.move(
            dx=round(float(x) - self.current[0], 6)
        )

    def to_y(self, y):
        return self.move(
            dy=round(float(y) - self.current[1], 6)
        )


def add_u_cells_from_horizontal(builder, count, direction, depth):
    sx = 1.0 if direction == 'right' else -1.0

    for _ in range(count):
        builder.move(dx=sx * b)
        builder.move(dy=-depth)
        builder.move(dx=sx * b)
        builder.move(dy=depth)

    return builder


def add_u_cells_from_vertical(builder, count, direction, depth):
    sx = 1.0 if direction == 'right' else -1.0

    for _ in range(count):
        builder.move(dy=-depth)
        builder.move(dx=sx * b)
        builder.move(dy=depth)
        builder.move(dx=sx * b)

    return builder


def vertical_stub(start, length, direction):
    start = point(start)
    sign = 1.0 if direction == 'up' else -1.0

    return [
        start,
        [
            start[0],
            round(start[1] + sign * float(length), 6),
        ],
    ]


# ============================================================
# Parameter-derived geometry
# ============================================================
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

    # Left launch to left inner node
    p1 = PathBuilder(left_tie)
    p1.path.insert(0, {
        'component': 'left_launch',
        'pin': 'tie',
    })

    p1.move(dx=2.0 * b)
    p1.move(dy=delta - a1)
    p1.move(dx=b)
    p1.move(dy=a1)
    p1.move(dx=b)

    if n > 1:
        add_u_cells_from_vertical(
            p1,
            n - 1,
            'right',
            a1,
        )

    t1 = p1.path

    # Left inner node to left outer node
    p2 = PathBuilder(geometry['left_inner'])
    p2.to_y(geometry['middle_baseline'])
    add_u_cells_from_horizontal(
        p2,
        n,
        'left',
        a2,
    )
    t2 = p2.path

    # Left outer node to center node
    p3 = PathBuilder(geometry['left_outer'])
    p3.move(dx=-b)
    p3.to_y(geometry['upper_baseline'])
    add_u_cells_from_horizontal(
        p3,
        n,
        'right',
        a3,
    )
    p3.move(dx=b + d)
    t3 = p3.path

    # Right-side mirrored paths
    t4 = mirror_reverse_path(t3)
    t5 = mirror_reverse_path(t2)
    t6 = mirror_reverse_path(
        t1,
        component='right_launch',
        pin='tie',
    )

    # Use the actual right launch tie position
    t6[-2] = list(right_tie)

    stubs = {
        'ground_lp1': {
            'path': vertical_stub(left_tie, lp1, 'up'),
            'end': 'short',
        },
        'ground_lp2': {
            'path': vertical_stub(
                geometry['left_outer'],
                lp2,
                'down',
            ),
            'end': 'short',
        },
        'ground_lp3': {
            'path': vertical_stub(
                geometry['left_inner'],
                lp3,
                'down',
            ),
            'end': 'short',
        },
        'ground_lp4': {
            'path': vertical_stub(
                geometry['center'],
                lp4,
                'down',
            ),
            'end': 'short',
        },
        'ground_lp5': {
            'path': vertical_stub(
                geometry['right_inner'],
                lp5,
                'down',
            ),
            'end': 'short',
        },
        'ground_lp6': {
            'path': vertical_stub(
                geometry['right_outer'],
                lp6,
                'down',
            ),
            'end': 'short',
        },
        'ground_lp7': {
            'path': vertical_stub(right_tie, lp7, 'up'),
            'end': 'short',
        },
    }

    routes = (t1, t2, t3, t4, t5, t6)

    return routes, stubs


# ============================================================
# Main
# ============================================================
def main():
    geometry = derive_geometry()

    left_launch_x = (
        geometry['left_tie'][0] - LAUNCH_TIE_INSET
    )
    right_launch_x = (
        geometry['right_tie'][0] + LAUNCH_TIE_INSET
    )

    design = designs.DesignPlanar(
        overwrite_enabled=True
    )

    chip_width = 2.0 * abs(left_launch_x) + 2.0
    chip_height = max(
        14.0,
        geometry['upper_baseline']
        - (LAUNCH_Y - a1)
        + 4.0,
    )

    design.chips.main.size.size_x = f'{chip_width}mm'
    design.chips.main.size.size_y = f'{chip_height}mm'

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

    left_tie = point(
        left_launch.pins['tie']['middle']
    )
    right_tie = point(
        right_launch.pins['tie']['middle']
    )

    routes, stubs = generate_routes(
        left_tie,
        right_tie,
        geometry,
    )

    t1, t2, t3, t4, t5, t6 = routes

    tree_config = [
        {
            'name': 'j1_to_j4',
            'path': t1,
        },
        {
            'name': 'j4_to_j2',
            'path': t2,
        },
        {
            'name': 'j2_to_j3',
            'path': t3,
        },
        {
            'name': 'j3_to_j6',
            'path': t4,
        },
        {
            'name': 'j6_to_j5',
            'path': t5,
        },
        {
            'name': 'j5_to_j7',
            'path': t6,
        },
    ]

    tree_config += [
        dict(name=name, **config)
        for name, config in stubs.items()
    ]

    tree = TreeRoute(
        design=design,
        name='upper_alignment_fixed_filter',
        tree_config=tree_config,
        trace_width=TRACE_WIDTH,
        trace_gap=TRACE_GAP,
        fillet=FILLET,
        lead_in='0mm',
        lead_out='0mm',
    )

    if ENABLE_GUI:
        gui = MetalGUI(design)
        gui.rebuild()
        gui.autoscale()
        gui.main_window.show()
        gui.qApp.exec_()

    return design, tree


if __name__ == '__main__':
    main()
