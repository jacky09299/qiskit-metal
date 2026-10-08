import traceback
from collections import OrderedDict

import numpy as np
from qiskit_metal import designs
from qiskit_metal.qlibrary.terminations.launchpad_wb import LaunchpadWirebond
from qiskit_metal.qlibrary.terminations.short_to_ground import ShortToGround

try:
    from qiskit_metal import MetalGUI
except ImportError:
    MetalGUI = None

from components import TreeRoute


# ============================================================
# Test 2 settings
# ============================================================

TRACE_WIDTH = '10um'
TRACE_GAP = '6um'
FILLET = '0um'
ENABLE_GUI = True

# Basic horizontal spacing shown as b in the sketch.
B = 0.60

# Seven red nodes:
# J1 = left launchpad; J7 = right launchpad.
# J2..J6 are VirtualJunction objects.
J2 = np.array([-6.60, -0.10])
J3 = np.array([ 0.00,  3.20])
J4 = np.array([-0.90, -2.80])
J5 = np.array([ 0.90, -2.80])  # J4-J5 spacing = 1.8 mm = 3b; no wire here.
J6 = np.array([ 6.60, -0.10])

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

    Both pins share the original tie location geometrically.  The main pin
    follows the original tie normal.  The ground pin points downward.
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
# Utility functions
# ============================================================

def as_anchors(points):
    return OrderedDict(
        (index + 1, np.asarray(point, dtype=float))
        for index, point in enumerate(points)
    )


def leaf(name, component, pin='short', points=None):
    return {
        'name': name,
        'anchors': as_anchors(points or []),
        'end_pin': {'component': component, 'pin': pin}
    }


def junction(name, coord, points, branches):
    return {
        'name': name,
        'anchors': as_anchors(points),
        'junction_coord': np.asarray(coord, dtype=float).tolist(),
        'branches': branches
    }


def pin_middle(design, component, pin):
    return np.asarray(
        design.components[component].pins[pin]['middle'],
        dtype=float
    )


def pin_normal(design, component, pin):
    value = np.asarray(
        design.components[component].pins[pin]['normal'],
        dtype=float
    )
    return value / np.linalg.norm(value)


def print_pin(design, component, pin):
    print(
        f'{component}.{pin}: '
        f'middle={pin_middle(design, component, pin).tolist()}, '
        f'normal={pin_normal(design, component, pin).tolist()}'
    )


def assert_opposite_normals(design, comp_a, pin_a, comp_b, pin_b):
    a = pin_normal(design, comp_a, pin_a)
    b = pin_normal(design, comp_b, pin_b)
    dot = float(np.dot(a, b))
    print(f'{comp_a}.{pin_a} vs {comp_b}.{pin_b}: dot={dot:.6f}')
    assert dot < -0.99, (
        f'Pins do not face each other: {comp_a}.{pin_a}={a.tolist()}, '
        f'{comp_b}.{pin_b}={b.tolist()}'
    )


def assert_manhattan(points, name):
    for index, (first, second) in enumerate(zip(points, points[1:])):
        p1 = np.asarray(first, dtype=float)
        p2 = np.asarray(second, dtype=float)
        same_x = np.isclose(p1[0], p2[0])
        same_y = np.isclose(p1[1], p2[1])
        if same_x and same_y:
            raise ValueError(f'{name}: duplicate anchors at {index}/{index + 1}: {p1.tolist()}')
        if not same_x and not same_y:
            raise ValueError(
                f'{name}: diagonal anchors {p1.tolist()} -> {p2.tolist()}'
            )


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


def create_shorts(design):
    j1 = pin_middle(design, 'left_launch', 'ground')
    j7 = pin_middle(design, 'right_launch', 'ground')

    # All shorts are below their corresponding red nodes.
    specs = [
        ('short_1', float(j1[0]), float(j1[1] - 0.75)),
        ('short_2', float(J2[0]), float(J2[1] - 0.75)),
        ('short_3', float(J3[0]), float(J3[1] - 0.75)),
        ('short_4', float(J4[0]), float(J4[1] - 0.75)),
        ('short_5', float(J5[0]), float(J5[1] - 0.75)),
        ('short_6', float(J6[0]), float(J6[1] - 0.75)),
        ('short_7', float(j7[0]), float(j7[1] - 0.75)),
    ]

    result = {}
    for name, x, y in specs:
        result[name] = ShortToGround(
            design,
            name,
            options=dict(
                pos_x=f'{x}mm',
                pos_y=f'{y}mm',
                orientation='270',
                width=TRACE_WIDTH
            )
        )
    return result


# ============================================================
# Six black meander routes from the sketch
# Tree direction: J1 -> J4 -> J2 -> J3 -> J6 -> J5 -> J7
# This direction is only for recursion. Geometry matches the sketch.
# ============================================================

def bottom_left_points(j1):
    """J1 -> J4: lower-left meander."""
    points = [
        [j1[0] + 0.45, j1[1]],
        [-7.80, j1[1]],
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
    ]
    assert_manhattan(points, 'J1_to_J4')
    return points


def middle_left_points():
    """J4 -> J2: middle-left meander, traversed right-to-left."""
    points = [
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
    ]
    assert_manhattan(points, 'J4_to_J2')
    return points


def upper_left_points():
    """J2 -> J3: upper-left meander."""
    points = [
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
    ]
    assert_manhattan(points, 'J2_to_J3')
    return points


def upper_right_points():
    """J3 -> J6: upper-right meander."""
    points = [
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
    ]
    assert_manhattan(points, 'J3_to_J6')
    return points


def middle_right_points():
    """J6 -> J5: middle-right meander, traversed right-to-left."""
    points = [
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
    ]
    assert_manhattan(points, 'J6_to_J5')
    return points


def bottom_right_points(j7):
    """J5 -> J7: lower-right meander."""
    points = [
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
        # j7[1] currently equals Y_BOTTOM_LOW.  Do not insert both
        # [7.20, Y_BOTTOM_LOW] and [7.20, j7[1]], because they become
        # the same anchor and RouteAnchors rejects duplicate points.
        [7.20, j7[1]],
        [j7[0] - 0.45, j7[1]],
    ]
    assert_manhattan(points, 'J5_to_J7')
    return points


# ============================================================
# Tree configuration
# ============================================================

def build_main_tree_config(design):
    j1 = pin_middle(design, 'left_launch', 'main')
    j7 = pin_middle(design, 'right_launch', 'main')

    j5_to_j7 = leaf(
        'j5_to_j7',
        'right_launch',
        'main',
        bottom_right_points(j7)
    )

    j6_to_j5 = junction(
        'j6_to_j5',
        J5,
        middle_right_points(),
        [leaf('ground_5', 'short_5'), j5_to_j7]
    )

    j3_to_j6 = junction(
        'j3_to_j6',
        J6,
        upper_right_points(),
        [leaf('ground_6', 'short_6'), j6_to_j5]
    )

    j2_to_j3 = junction(
        'j2_to_j3',
        J3,
        upper_left_points(),
        [leaf('ground_3', 'short_3'), j3_to_j6]
    )

    j4_to_j2 = junction(
        'j4_to_j2',
        J2,
        middle_left_points(),
        [leaf('ground_2', 'short_2'), j2_to_j3]
    )

    return {
        'name': 'j1_to_j4',
        'start_pin': {'component': 'left_launch', 'pin': 'main'},
        'anchors': as_anchors(bottom_left_points(j1)),
        'junction_coord': J4.tolist(),
        'branches': [leaf('ground_4', 'short_4'), j4_to_j2]
    }


def endpoint_ground_config(launchpad, short_name):
    return {
        'name': 'ground',
        'start_pin': {'component': launchpad, 'pin': 'ground'},
        'anchors': OrderedDict(),
        'end_pin': {'component': short_name, 'pin': 'short'}
    }


# ============================================================
# Diagnostics
# ============================================================

def collect_and_validate(main_tree, left_ground_tree, right_ground_tree):
    all_routes = {}
    for manager in (main_tree, left_ground_tree, right_ground_tree):
        for name, route in manager.routes.items():
            if name in all_routes:
                raise AssertionError(f'Duplicate route name: {name}')
            all_routes[name] = route

    expected = {
        'test2_main_j1_to_j4',
        'test2_main_j4_to_j2',
        'test2_main_j2_to_j3',
        'test2_main_j3_to_j6',
        'test2_main_j6_to_j5',
        'test2_main_j5_to_j7',
        'test2_main_ground_2',
        'test2_main_ground_3',
        'test2_main_ground_4',
        'test2_main_ground_5',
        'test2_main_ground_6',
        'test2_left_ground_ground',
        'test2_right_ground_ground',
    }

    missing = expected - set(all_routes)
    extra = set(all_routes) - expected
    failures = []
    total = 0.0

    print('\n' + '=' * 80)
    print('Test 2 result')
    print('=' * 80)
    print(f'Main routes:       6')
    print(f'Ground routes:     7')
    print(f'Total routes:      {len(all_routes)} / expected 13')
    print(f'Virtual junctions: {len(main_tree.junctions)} / expected 5')
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
    assert len(main_tree.routes) == 11
    assert len(left_ground_tree.routes) == 1
    assert len(right_ground_tree.routes) == 1
    assert len(main_tree.junctions) == EXPECTED_VIRTUAL_JUNCTIONS
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
    create_shorts(design)

    for component in (left, right):
        missing = {'tie', 'main', 'ground'} - set(component.pins)
        assert not missing, f'{component.name} missing pins: {sorted(missing)}'

    print('\n' + '=' * 80)
    print('Endpoint diagnostics')
    print('=' * 80)
    for component, pin in [
        ('left_launch', 'ground'),
        ('short_1', 'short'),
        ('right_launch', 'ground'),
        ('short_7', 'short'),
    ]:
        print_pin(design, component, pin)

    assert_opposite_normals(
        design, 'left_launch', 'ground', 'short_1', 'short'
    )
    assert_opposite_normals(
        design, 'right_launch', 'ground', 'short_7', 'short'
    )

    main_config = build_main_tree_config(design)
    left_ground_config = endpoint_ground_config('left_launch', 'short_1')
    right_ground_config = endpoint_ground_config('right_launch', 'short_7')

    try:
        main_tree = TreeRoute(
            design=design,
            name='test2_main',
            tree_config=main_config,
            trace_width=TRACE_WIDTH,
            trace_gap=TRACE_GAP,
            fillet=FILLET,
            lead_in='0mm',
            lead_out='0mm'
        )

        left_ground_tree = TreeRoute(
            design=design,
            name='test2_left_ground',
            tree_config=left_ground_config,
            trace_width=TRACE_WIDTH,
            trace_gap=TRACE_GAP,
            fillet=FILLET,
            lead_in='0mm',
            lead_out='0mm'
        )

        right_ground_tree = TreeRoute(
            design=design,
            name='test2_right_ground',
            tree_config=right_ground_config,
            trace_width=TRACE_WIDTH,
            trace_gap=TRACE_GAP,
            fillet=FILLET,
            lead_in='0mm',
            lead_out='0mm'
        )

    except Exception:
        print('\nTreeRoute construction failed. GUI has not been created yet.')
        traceback.print_exc()
        raise

    routes = collect_and_validate(
        main_tree,
        left_ground_tree,
        right_ground_tree
    )

    # Create Qt only after every route has passed validation.
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

    return design, main_tree, left_ground_tree, right_ground_tree, routes


if __name__ == '__main__':
    run_test_2()

