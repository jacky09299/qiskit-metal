import os
import traceback
from collections import OrderedDict

import numpy as np
from qiskit_metal import designs
from qiskit_metal.qlibrary.terminations.launchpad_wb import LaunchpadWirebond

try:
    from qiskit_metal import MetalGUI
except ImportError:
    MetalGUI = None

from components import TreeRoute


# ============================================================
# Test settings
# ============================================================

TRACE_WIDTH = '10um'
TRACE_GAP = '6um'
FILLET = '0um'
ENABLE_GUI = os.environ.get('ENABLE_GUI', 'True').lower() == 'true'

# Nodes coordinates from the meander sketch
J1 = np.array([-8.75, -4.05])
J2 = np.array([-6.60, -0.10])
J3 = np.array([ 0.00,  3.20])
J4 = np.array([-0.90, -2.80])
J5 = np.array([ 0.90, -2.80])
J6 = np.array([ 6.60, -0.10])
J7 = np.array([ 8.75, -4.05])

Y_TOP = 3.20
Y_UPPER_LOW = 0.90
Y_MIDDLE_HIGH = 0.05
Y_MIDDLE_LOW = -1.95
Y_BOTTOM_HIGH = -1.95
Y_BOTTOM_LOW = -4.05

EXPECTED_MAIN_ROUTES = 6
EXPECTED_GROUND_ROUTES = 7
EXPECTED_TOTAL_ROUTES = 13
EXPECTED_VIRTUAL_JUNCTIONS = 5


# ============================================================
# Launchpad used as J1/J7
# ============================================================

class BranchLaunchpadWirebond(LaunchpadWirebond):
    """Launchpad endpoint with separate main and ground routing pins.
    """

    def make(self):
        super().make()

        tie = self.pins['tie']
        middle = np.asarray(tie['middle'], dtype=float)
        main_normal = np.asarray(tie['normal'], dtype=float)
        main_normal /= np.linalg.norm(main_normal)
        width = float(tie['width'])
        step = 0.01

        self.add_pin(
            'main',
            [middle - main_normal * step, middle],
            width,
            input_as_norm=True
        )

        down = np.array([0.0, -1.0], dtype=float)
        self.add_pin(
            'ground',
            [middle - down * step, middle],
            width,
            input_as_norm=True
        )


# ============================================================
# Path generators for routes
# ============================================================

def bottom_left_path():
    """J1 -> J4: lower-left meander."""
    return [
        {'component': 'left_launch', 'pin': 'main'},
        [J1[0] + 0.45, J1[1]],
        [-7.80, J1[1]],
        [-7.80, Y_BOTTOM_HIGH],
        [-7.20, Y_BOTTOM_HIGH],
        [-7.20, Y_BOTTOM_LOW],
        [-6.60, Y_BOTTOM_LOW],
        [-6.60, Y_BOTTOM_HIGH],
        [-6.00, Y_BOTTOM_HIGH],
        [-6.00, Y_BOTTOM_LOW],
        [-5.40, Y_BOTTOM_LOW],
        [-5.40, Y_BOTTOM_HIGH],
        [-4.80, Y_BOTTOM_HIGH],
        [-4.80, Y_BOTTOM_LOW],
        [-4.20, Y_BOTTOM_LOW],
        [-4.20, Y_BOTTOM_HIGH],
        [-3.60, Y_BOTTOM_HIGH],
        [-3.60, Y_BOTTOM_LOW],
        [-3.00, Y_BOTTOM_LOW],
        [-3.00, Y_BOTTOM_HIGH],
        [-2.40, Y_BOTTOM_HIGH],
        [-2.40, Y_BOTTOM_LOW],
        [-1.80, Y_BOTTOM_LOW],
        [-1.80, float(J4[1])],
        [-1.20, float(J4[1])],
        J4.tolist()
    ]


def middle_left_path():
    """J4 -> J2: middle-left meander."""
    return [
        J4.tolist(),
        [-1.30, float(J4[1])],
        [-1.30, Y_MIDDLE_HIGH],
        [-1.90, Y_MIDDLE_HIGH],
        [-1.90, Y_MIDDLE_LOW],
        [-2.50, Y_MIDDLE_LOW],
        [-2.50, Y_MIDDLE_HIGH],
        [-3.10, Y_MIDDLE_HIGH],
        [-3.10, Y_MIDDLE_LOW],
        [-3.70, Y_MIDDLE_LOW],
        [-3.70, Y_MIDDLE_HIGH],
        [-4.30, Y_MIDDLE_HIGH],
        [-4.30, Y_MIDDLE_LOW],
        [-4.90, Y_MIDDLE_LOW],
        [-4.90, Y_MIDDLE_HIGH],
        [-5.50, Y_MIDDLE_HIGH],
        [-5.50, Y_MIDDLE_LOW],
        [-6.10, Y_MIDDLE_LOW],
        [-6.10, float(J2[1])],
        J2.tolist()
    ]


def upper_left_path():
    """J2 -> J3: upper-left meander."""
    return [
        J2.tolist(),
        [-6.60, 0.55],
        [-6.60, Y_TOP],
        [-6.00, Y_TOP],
        [-6.00, Y_UPPER_LOW],
        [-5.40, Y_UPPER_LOW],
        [-5.40, Y_TOP],
        [-4.80, Y_TOP],
        [-4.80, Y_UPPER_LOW],
        [-4.20, Y_UPPER_LOW],
        [-4.20, Y_TOP],
        [-3.60, Y_TOP],
        [-3.60, Y_UPPER_LOW],
        [-3.00, Y_UPPER_LOW],
        [-3.00, Y_TOP],
        [-2.40, Y_TOP],
        [-2.40, Y_UPPER_LOW],
        [-1.80, Y_UPPER_LOW],
        [-1.80, Y_TOP],
        [-0.40, Y_TOP],
        J3.tolist()
    ]


def upper_right_path():
    """J3 -> J6: upper-right meander."""
    return [
        J3.tolist(),
        [0.40, Y_TOP],
        [1.80, Y_TOP],
        [1.80, Y_UPPER_LOW],
        [2.40, Y_UPPER_LOW],
        [2.40, Y_TOP],
        [3.00, Y_TOP],
        [3.00, Y_UPPER_LOW],
        [3.60, Y_UPPER_LOW],
        [3.60, Y_TOP],
        [4.20, Y_TOP],
        [4.20, Y_UPPER_LOW],
        [4.80, Y_UPPER_LOW],
        [4.80, Y_TOP],
        [5.40, Y_TOP],
        [5.40, Y_UPPER_LOW],
        [6.00, Y_UPPER_LOW],
        [6.00, Y_TOP],
        [6.60, Y_TOP],
        [6.60, 0.55],
        J6.tolist()
    ]


def middle_right_path():
    """J6 -> J5: middle-right meander."""
    return [
        J6.tolist(),
        [6.10, float(J6[1])],
        [6.10, Y_MIDDLE_LOW],
        [5.50, Y_MIDDLE_LOW],
        [5.50, Y_MIDDLE_HIGH],
        [4.90, Y_MIDDLE_HIGH],
        [4.90, Y_MIDDLE_LOW],
        [4.30, Y_MIDDLE_LOW],
        [4.30, Y_MIDDLE_HIGH],
        [3.70, Y_MIDDLE_HIGH],
        [3.70, Y_MIDDLE_LOW],
        [3.10, Y_MIDDLE_LOW],
        [3.10, Y_MIDDLE_HIGH],
        [2.50, Y_MIDDLE_HIGH],
        [2.50, Y_MIDDLE_LOW],
        [1.90, Y_MIDDLE_LOW],
        [1.90, float(J5[1])],
        [1.30, float(J5[1])],
        J5.tolist()
    ]


def bottom_right_path():
    """J5 -> J7: lower-right meander."""
    return [
        J5.tolist(),
        [1.20, float(J5[1])],
        [1.80, float(J5[1])],
        [1.80, Y_BOTTOM_LOW],
        [2.40, Y_BOTTOM_LOW],
        [2.40, Y_BOTTOM_HIGH],
        [3.00, Y_BOTTOM_HIGH],
        [3.00, Y_BOTTOM_LOW],
        [3.60, Y_BOTTOM_LOW],
        [3.60, Y_BOTTOM_HIGH],
        [4.20, Y_BOTTOM_HIGH],
        [4.20, Y_BOTTOM_LOW],
        [4.80, Y_BOTTOM_LOW],
        [4.80, Y_BOTTOM_HIGH],
        [5.40, Y_BOTTOM_HIGH],
        [5.40, Y_BOTTOM_LOW],
        [6.00, Y_BOTTOM_LOW],
        [6.00, Y_BOTTOM_HIGH],
        [6.60, Y_BOTTOM_HIGH],
        [6.60, Y_BOTTOM_LOW],
        [7.20, J7[1]],
        [J7[0] - 0.45, J7[1]],
        {'component': 'right_launch', 'pin': 'main'}
    ]


# ============================================================
# Physical QComponents
# ============================================================

def create_launchpads(design):
    left = BranchLaunchpadWirebond(
        design,
        'left_launch',
        options=dict(
            pos_x='-9.0mm',
            pos_y='-4.05mm',
            orientation='0',
            trace_width=TRACE_WIDTH,
            trace_gap=TRACE_GAP,
            lead_length='250um',
            pad_width='300um',
            pad_height='300um',
            pad_gap='60um',
            taper_height='250um'
        )
    )

    right = BranchLaunchpadWirebond(
        design,
        'right_launch',
        options=dict(
            pos_x='9.0mm',
            pos_y='-4.05mm',
            orientation='180',
            trace_width=TRACE_WIDTH,
            trace_gap=TRACE_GAP,
            lead_length='250um',
            pad_width='300um',
            pad_height='300um',
            pad_gap='60um',
            taper_height='250um'
        )
    )

    return left, right


# ============================================================
# Configuration using intuition path-based syntax
# ============================================================

def build_tree_config():
    return [
        # Main 6 routes
        {'name': 'j1_to_j4', 'path': bottom_left_path()},
        {'name': 'j4_to_j2', 'path': middle_left_path()},
        {'name': 'j2_to_j3', 'path': upper_left_path()},
        {'name': 'j3_to_j6', 'path': upper_right_path()},
        {'name': 'j6_to_j5', 'path': middle_right_path()},
        {'name': 'j5_to_j7', 'path': bottom_right_path()},

        # 5 Ground routes connecting junctions J2..J6 to auto-created ShortToGround
        {'name': 'ground_2', 'path': [J2.tolist(), [J2[0], J2[1] - 0.75]], 'end': 'short'},
        {'name': 'ground_3', 'path': [J3.tolist(), [J3[0], J3[1] - 0.75]], 'end': 'short'},
        {'name': 'ground_4', 'path': [J4.tolist(), [J4[0], J4[1] - 0.75]], 'end': 'short'},
        {'name': 'ground_5', 'path': [J5.tolist(), [J5[0], J5[1] - 0.75]], 'end': 'short'},
        {'name': 'ground_6', 'path': [J6.tolist(), [J6[0], J6[1] - 0.75]], 'end': 'short'},

        # 2 Launchpad ground routes to auto-created ShortToGround
        {
            'name': 'left_ground',
            'start': {'component': 'left_launch', 'pin': 'ground'},
            'end': 'short',
            'path': [[J1[0], J1[1] - 0.75]]
        },
        {
            'name': 'right_ground',
            'start': {'component': 'right_launch', 'pin': 'ground'},
            'end': 'short',
            'path': [[J7[0], J7[1] - 0.75]]
        }
    ]


# ============================================================
# Diagnostics
# ============================================================

def collect_and_validate(tree):
    all_routes = tree.routes

    expected = {
        'test2_j1_to_j4',
        'test2_j4_to_j2',
        'test2_j2_to_j3',
        'test2_j3_to_j6',
        'test2_j6_to_j5',
        'test2_j5_to_j7',
        'test2_ground_2',
        'test2_ground_3',
        'test2_ground_4',
        'test2_ground_5',
        'test2_ground_6',
        'test2_left_ground',
        'test2_right_ground',
    }

    missing = expected - set(all_routes)
    extra = set(all_routes) - expected
    failures = []
    total = 0.0

    print('\n' + '=' * 80)
    print('Test 2 result')
    print('=' * 80)
    print(f'Total routes:      {len(all_routes)} / expected 13')
    print(f'Virtual junctions: {len(tree.junctions)} / expected 5')
    print(f'Shorts created:    {len(tree.shorts)} / expected 7')
    print('-' * 80)

    for name in sorted(all_routes):
        route = all_routes[name]
        try:
            length = float(route.length)
            if not np.isfinite(length) or length <= 0:
                raise ValueError(f'invalid length={length}')
            total += length
            print(
                f'[OK] {name:<34} '
                f'{route.__class__.__name__:<16} {length:>10.5f} mm'
            )
        except Exception as exc:
            failures.append((name, str(exc)))
            print(f'[FAIL] {name}: {exc}')

    assert len(all_routes) == EXPECTED_TOTAL_ROUTES
    assert len(tree.junctions) == EXPECTED_VIRTUAL_JUNCTIONS
    assert len(tree.shorts) == EXPECTED_GROUND_ROUTES
    assert not missing, f'Missing routes: {sorted(missing)}'
    assert not extra, f'Extra routes: {sorted(extra)}'
    assert not failures, f'Route length errors: {failures}'

    print('-' * 80)
    print(f'Total route length: {total:.6f} mm')
    print('TEST 2 PASS')
    return all_routes


# ============================================================
# Main
# ============================================================

def run_test_2():
    design = designs.DesignPlanar(overwrite_enabled=True)
    design.chips.main.size.size_x = '22mm'
    design.chips.main.size.size_y = '12mm'

    left, right = create_launchpads(design)

    tree_config = build_tree_config()

    try:
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
    except Exception:
        print('\nTreeRoute construction failed.')
        traceback.print_exc()
        raise

    routes = collect_and_validate(tree)

    if ENABLE_GUI and MetalGUI is not None:
        try:
            gui = MetalGUI(design)
            gui.rebuild()
            gui.autoscale()
            if hasattr(gui, 'main_window') and gui.main_window is not None:
                gui.main_window.show()
                gui.qApp.exec_()
        except Exception:
            print('GUI failed after routing validation.')
            traceback.print_exc()

    return design, tree, routes


if __name__ == '__main__':
    run_test_2()
