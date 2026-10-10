import os
import numpy as np

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
b = 0.45
c = 0.85
d = 0.20
delta = -0.1
n = 2

lp1 = 1.13357
lp2 = 0.211113
lp3 = 0.104681
lp4 = 0.826346
lp5 = 0.104681
lp6 = 0.211113
lp7 = 1.13357

LAUNCH_Y = -3.00
LAUNCH_TIE_INSET = 0.025


def point(value):
    return [float(value[0]), float(value[1])]


def path_coordinates(path):
    return [
        point(item)
        for item in path
        if isinstance(item, (list, tuple)) and len(item) == 2
    ]


def mirror_point(value):
    val = point(value)
    return [-val[0], val[1]]


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
            self.current[0] + dx,
            self.current[1] + dy,
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
        return self.move(dy=float(y) - self.current[1])


def derive_geometry(launch_y=LAUNCH_Y):
    half_row_width = n * 2.0 * b

    j4_x = -d
    j5_x = d
    j2_x = j4_x - half_row_width
    j6_x = -j2_x

    left_tie_x = j2_x - 2.0 * b
    right_tie_x = -left_tie_x

    lower_baseline = launch_y + delta
    middle_baseline = lower_baseline + a2 + c
    upper_baseline = middle_baseline + a3 + c

    # Blue-circle nodes: one b outside the normal middle-row endpoint.
    left_shared_x = j2_x - b
    right_shared_x = j6_x + b

    return {
        'left_tie': point([left_tie_x, launch_y]),
        'left_outer': point([j2_x, middle_baseline]),
        'left_shared': point([left_shared_x, middle_baseline]),
        'left_inner': point([j4_x, lower_baseline]),
        'center': point([0.0, upper_baseline]),
        'right_inner': point([j5_x, lower_baseline]),
        'right_outer': point([j6_x, middle_baseline]),
        'right_shared': point([right_shared_x, middle_baseline]),
        'right_tie': point([right_tie_x, launch_y]),
        'lower_baseline': lower_baseline,
        'middle_baseline': middle_baseline,
        'upper_baseline': upper_baseline,
    }


import layout_builder

def generate_routes(left_tie, right_tie, geometry):
    return layout_builder.generate_routes(
        left_tie, right_tie, geometry,
        a1, a2, a3, b, c, d, delta, n,
        [lp1, lp2, lp3, lp4, lp5, lp6, lp7],
        left_component='left_launch',
        right_component='right_launch'
    )


def main():
    half_row_width = n * 2.0 * b
    j4_x = -d
    j2_x = j4_x - half_row_width
    left_tie_x = j2_x - 2.0 * b
    left_launch_x = left_tie_x - LAUNCH_TIE_INSET
    right_launch_x = -left_launch_x

    design = designs.DesignPlanar(overwrite_enabled=True)
    chip_width = 2.0 * abs(left_launch_x) + 2.0
    chip_height = 14.0
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

    geometry = derive_geometry(launch_y=left_tie[1])

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
