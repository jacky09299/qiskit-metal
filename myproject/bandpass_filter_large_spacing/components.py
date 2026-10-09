import math
from collections import OrderedDict
import numpy as np

from qiskit_metal.qlibrary.core import QComponent
from qiskit_metal.qlibrary.sample_shapes.rectangle import Rectangle
from qiskit_metal.qlibrary.tlines.anchored_path import RouteAnchors
from qiskit_metal.qlibrary.tlines.straight_path import RouteStraight
from qiskit_metal.qlibrary.terminations.short_to_ground import ShortToGround

import config
import utils


class UShapeComponent:
    """
    U形元件類別

    參數說明:
    - cx, cy: 中心點座標
    - bl: 底部寬度 (預設 0.3)
    - sh: 側邊高度 (預設 0.1)  
    - tw: 線條厚度 (預設 0.01)
    """

    def __init__(self, design, base_name='u_shape', bl=0.3, sh=0.1, tw=0.01):
        """
        初始化 U 形元件

        Args:
            design: 設計物件
            base_name: 元件基礎名稱
            bl: 底部寬度
            sh: 側邊高度
            tw: 線條厚度
        """
        self.design = design
        self.base_name = base_name
        self.bl = bl  # 底部寬度
        self.sh = sh  # 側邊高度
        self.tw = tw  # 線條厚度

        # 儲存矩形元件的參考
        self.rect_bottom = None
        self.rect_left = None
        self.rect_right = None

    def create(self, cx, cy):
        """
        在指定位置創建 U 形元件

        Args:
            cx: 中心點 X 座標
            cy: 中心點 Y 座標
        """
        # === 計算各部分位置與尺寸 ===

        # 底部矩形
        self.rect_bottom = Rectangle(
            self.design, 
            f'{self.base_name}_bottom', 
            options=dict(
                pos_x=cx,
                pos_y=cy,
                width=self.bl,
                height=self.tw
            )
        )

        # 左側矩形
        left_x = cx - self.bl / 2 + self.tw / 2
        left_y = cy + self.sh / 2 - self.tw / 2
        self.rect_left = Rectangle(
            self.design,
            f'{self.base_name}_left',
            options=dict(
                pos_x=left_x,
                pos_y=left_y,
                width=self.tw,
                height=self.sh
            )
        )

        # 右側矩形
        right_x = cx + self.bl / 2 - self.tw / 2
        right_y = cy + self.sh / 2 - self.tw / 2
        self.rect_right = Rectangle(
            self.design,
            f'{self.base_name}_right',
            options=dict(
                pos_x=right_x,
                pos_y=right_y,
                width=self.tw,
                height=self.sh
            )
        )

        self.rect_bottom.add_pin(f"node", points = [[cx,cy],[cx,cy-0.0000001]],width = config.cpw_width, input_as_norm=True)


        return self

    def update_position(self, cx, cy):
        """
        更新 U 形元件位置

        Args:
            cx: 新的中心點 X 座標
            cy: 新的中心點 Y 座標
        """
        if not self.rect_bottom:
            raise ValueError("請先使用 create() 方法創建元件")

        # 更新底部矩形
        self.rect_bottom.options['pos_x'] = cx
        self.rect_bottom.options['pos_y'] = cy

        # 更新左側矩形
        left_x = cx - self.bl / 2 + self.tw / 2
        left_y = cy + self.sh / 2 - self.tw / 2
        self.rect_left.options['pos_x'] = left_x
        self.rect_left.options['pos_y'] = left_y

        # 更新右側矩形
        right_x = cx + self.bl / 2 - self.tw / 2
        right_y = cy + self.sh / 2 - self.tw / 2
        self.rect_right.options['pos_x'] = right_x
        self.rect_right.options['pos_y'] = right_y

    def update_dimensions(self, bl=None, sh=None, tw=None):
        """
        更新 U 形元件尺寸

        Args:
            bl: 底部寬度 (可選)
            sh: 側邊高度 (可選)
            tw: 線條厚度 (可選)
        """
        if not self.rect_bottom:
            raise ValueError("請先使用 create() 方法創建元件")

        # 更新參數
        if bl is not None:
            self.bl = bl
        if sh is not None:
            self.sh = sh
        if tw is not None:
            self.tw = tw

        # 獲取當前中心位置
        cx = self.rect_bottom.options['pos_x']
        cy = self.rect_bottom.options['pos_y']

        # 重新計算位置和尺寸
        self.update_position(cx, cy)

        # 更新尺寸
        self.rect_bottom.options['width'] = self.bl
        self.rect_bottom.options['height'] = self.tw

        self.rect_left.options['width'] = self.tw
        self.rect_left.options['height'] = self.sh

        self.rect_right.options['width'] = self.tw
        self.rect_right.options['height'] = self.sh

    def get_components(self):
        """
        取得所有矩形元件

        Returns:
            tuple: (底部矩形, 左側矩形, 右側矩形)
        """
        return (self.rect_bottom, self.rect_left, self.rect_right)

    def delete(self):
        """
        刪除 U 形元件的所有矩形
        """
        components = [self.rect_bottom, self.rect_left, self.rect_right]
        for component in components:
            if component:
                try:
                    component.delete()
                except:
                    pass

        self.rect_bottom = None
        self.rect_left = None
        self.rect_right = None


def create_u_shape(design, cx, cy, name='u_shape', bl=0.3, sh=0.1, tw=0.01):
    """
    快速創建 U 形元件的便利函數
    """
    u_shape = UShapeComponent(design, name, bl, sh, tw)
    u_shape.create(cx, cy)
    return u_shape


class VirtualJunction(QComponent):
    """
    用來作為 TreeRoute / GraphRoute 分岔點的隱形元件。

    可以根據輸入動態產生任意數量的 pins，
    讓 RouteAnchors / RouteStraight 附著。

    本身不產生任何金屬圖形，只提供連接點。
    """

    default_options = dict(pins={})

    def make(self):
        for pin_name, pinfo in self.p.pins.items():
            self.add_pin(
                pin_name,
                pinfo['points'],
                pinfo['width'],
                input_as_norm=True
            )


class TreeRoute:
    """
    直覺路徑線路管理器 (Path-based Route Manager)。

    功能：
    --------------------------------------------------
    1. 使用者直接定義走線的完整路徑 (`path`)，包含頭尾與中間折點。
    2. 自動比對節點座標，當多條走線在某個座標相交重疊且未連接外部元件時，自動建立 `VirtualJunction`。
    3. 若相交座標有走線連接至外部元件或屬於既有走線上的點，自動在該走線上 `add_pin` 作為分支走線的起終點。
    4. 當走線端點設定為 short (或寫 'short')，自動推算向度並建立 `ShortToGround` (命名為 `{route_name}__stg`)。
    5. 自動從完整 `path` 中抽離中間折點作為 `RouteAnchors` 的 `anchors`。
    6. 無折點時使用 `RouteStraight`。
    """

    def __init__(
        self,
        design,
        name,
        tree_config,
        trace_width=config.cpw_width,
        trace_gap=config.cpw_gap,
        fillet='0',
        lead_in='0mm',
        lead_out='0mm'
    ):
        self.design = design
        self.name = name
        self.tree_config = tree_config

        self.trace_width = design.parse_value(trace_width)
        self.trace_gap = design.parse_value(trace_gap)

        self.fillet = fillet

        self.lead_in = lead_in
        self.lead_out = lead_out

        self.routes = {}
        self.junctions = {}
        self.shorts = {}

        self._build_tree()

    def _get_pin_coord(self, pin_dict):
        comp = self.design.components[pin_dict['component']]
        return np.asarray(comp.pins[pin_dict['pin']]['middle'], dtype=float)

    def _make_pin_points(self, jx, jy, toward_x, toward_y, step=0.01):
        dx = toward_x - jx
        dy = toward_y - jy
        mag = np.hypot(dx, dy)
        ux = dx / mag if mag != 0 else 1.0
        uy = dy / mag if mag != 0 else 0.0
        return [
            [jx - ux * step, jy - uy * step],
            [jx, jy]
        ]

    def _calc_short_orientation(self, v_in):
        orient = math.degrees(math.atan2(v_in[1], v_in[0])) % 360
        return orient

    def _normalize_config(self):
        if isinstance(self.tree_config, list):
            return self.tree_config
        elif isinstance(self.tree_config, dict):
            if 'routes' in self.tree_config:
                return self.tree_config['routes']
            return self._flatten_legacy_config(self.tree_config)
        return []

    def _flatten_legacy_config(self, node, parent_pin=None):
        routes = []
        name = node.get('name', 'node')
        start_pin = node.get('start_pin', parent_pin)
        anchors_dict = node.get('anchors', OrderedDict())
        anchors = [list(v) for v in anchors_dict.values()]

        if 'end_pin' in node:
            path = []
            if start_pin:
                path.append(start_pin)
            path.extend(anchors)
            path.append(node['end_pin'])
            routes.append({'name': name, 'path': path})
        elif 'junction_coord' in node:
            j_coord = node['junction_coord']
            path = []
            if start_pin:
                path.append(start_pin)
            path.extend(anchors)
            path.append(j_coord)
            routes.append({'name': name, 'path': path})

            branches = node.get('branches', [])
            for branch in branches:
                routes.extend(self._flatten_legacy_config(branch, j_coord))
        return routes

    def _parse_endpoint(self, ep_spec, default_coord=None):
        if ep_spec == 'short' or (isinstance(ep_spec, dict) and ep_spec.get('short')):
            coord = None
            if isinstance(ep_spec, dict) and 'coord' in ep_spec:
                coord = np.asarray(ep_spec['coord'], dtype=float)
            elif default_coord is not None:
                coord = np.asarray(default_coord, dtype=float)
            return 'short', coord
        elif isinstance(ep_spec, dict) and 'component' in ep_spec and 'pin' in ep_spec:
            coord = self._get_pin_coord(ep_spec)
            return 'component', {'spec': ep_spec, 'coord': coord}
        elif ep_spec is not None:
            coord = np.asarray(ep_spec, dtype=float)
            return 'coord', coord
        return None, None

    def _build_tree(self):
        route_list = self._normalize_config()
        if not route_list:
            return

        parsed_routes = []
        endpoint_coord_usage = {}
        comp_pin_coords = set()

        for idx, r_spec in enumerate(route_list):
            r_name = r_spec.get('name', f"route_{idx}")
            raw_path = list(r_spec.get('path', []))

            start_spec = r_spec.get('start') or r_spec.get('start_pin')
            end_spec = r_spec.get('end') or r_spec.get('end_pin')

            if start_spec is None and len(raw_path) > 0:
                start_spec = raw_path[0]
                raw_path = raw_path[1:]

            if end_spec is None and len(raw_path) > 0:
                end_spec = raw_path[-1]
                raw_path = raw_path[:-1]

            middle_coords = []
            for item in raw_path:
                if isinstance(item, (list, tuple, np.ndarray)):
                    middle_coords.append(np.asarray(item, dtype=float))

            default_start_coord = middle_coords[0] if middle_coords else None
            start_type, start_data = self._parse_endpoint(start_spec, default_start_coord)

            default_end_coord = middle_coords[-1] if middle_coords else (start_data if start_type == 'coord' else None)
            end_type, end_data = self._parse_endpoint(end_spec, default_end_coord)

            if start_type in ('component', 'short') and start_data is not None and len(middle_coords) > 0:
                if np.allclose(middle_coords[0], start_data if start_type == 'short' else start_data['coord']):
                    middle_coords = middle_coords[1:]

            if end_type in ('component', 'short') and end_data is not None and len(middle_coords) > 0:
                if np.allclose(middle_coords[-1], end_data if end_type == 'short' else end_data['coord']):
                    middle_coords = middle_coords[:-1]

            full_coords = []
            if start_type == 'component':
                full_coords.append(start_data['coord'])
                comp_pin_coords.add((round(start_data['coord'][0], 6), round(start_data['coord'][1], 6)))
            elif start_type in ('coord', 'short'):
                full_coords.append(start_data)

            full_coords.extend(middle_coords)

            if end_type == 'component':
                full_coords.append(end_data['coord'])
                comp_pin_coords.add((round(end_data['coord'][0], 6), round(end_data['coord'][1], 6)))
            elif end_type in ('coord', 'short'):
                full_coords.append(end_data)

            parsed_routes.append({
                'name': r_name,
                'full_name': f"{self.name}_{r_name}",
                'start_type': start_type,
                'start_data': start_data,
                'end_type': end_type,
                'end_data': end_data,
                'coords': full_coords
            })

            start_coord = full_coords[0]
            start_key = (round(start_coord[0], 6), round(start_coord[1], 6))
            if start_type not in ('component', 'short'):
                next_pt = full_coords[1] if len(full_coords) > 1 else start_coord
                if start_key not in endpoint_coord_usage:
                    endpoint_coord_usage[start_key] = []
                endpoint_coord_usage[start_key].append((idx, 'start', next_pt, start_coord))

            end_coord = full_coords[-1]
            end_key = (round(end_coord[0], 6), round(end_coord[1], 6))
            if end_type not in ('component', 'short'):
                prev_pt = full_coords[-2] if len(full_coords) > 1 else end_coord
                if end_key not in endpoint_coord_usage:
                    endpoint_coord_usage[end_key] = []
                endpoint_coord_usage[end_key].append((idx, 'end', prev_pt, end_coord))

        # 1. Create VirtualJunctions for shared coordinates where NO route connects to an external component
        for coord_key, connections in endpoint_coord_usage.items():
            if len(connections) >= 2 and coord_key not in comp_pin_coords:
                jx, jy = connections[0][3]
                j_base_name = f"{self.name}_junc_{len(self.junctions) + 1}"

                pins_config = {}
                for route_idx, role, pt, _ in connections:
                    r_item = parsed_routes[route_idx]
                    pin_name = f"pin_{r_item['name']}"
                    in_pts = self._make_pin_points(jx, jy, pt[0], pt[1])
                    pins_config[pin_name] = {
                        'points': in_pts,
                        'width': self.trace_width
                    }

                vj = VirtualJunction(
                    self.design,
                    j_base_name,
                    options=dict(pins=pins_config)
                )
                self.junctions[j_base_name] = vj

                for route_idx, role, _, _ in connections:
                    r_item = parsed_routes[route_idx]
                    pin_name = f"pin_{r_item['name']}"
                    if role == 'start':
                        r_item['start_type'] = 'junction'
                        r_item['start_data'] = {'component': j_base_name, 'pin': pin_name}
                    else:
                        r_item['end_type'] = 'junction'
                        r_item['end_data'] = {'component': j_base_name, 'pin': pin_name}

        # 2. Create ShortToGround components for 'short' endpoints
        for r_item in parsed_routes:
            full_name = r_item['full_name']
            coords = r_item['coords']

            if r_item['start_type'] == 'short':
                stg_coord = coords[0]
                next_pt = coords[1] if len(coords) > 1 else stg_coord
                v_in = stg_coord - next_pt
                orient = self._calc_short_orientation(v_in)
                stg_name = f"{full_name}__stg"
                stg = ShortToGround(
                    self.design,
                    stg_name,
                    options=dict(
                        pos_x=f"{stg_coord[0]}mm",
                        pos_y=f"{stg_coord[1]}mm",
                        orientation=orient,
                        width=self.trace_width
                    )
                )
                self.shorts[stg_name] = stg
                r_item['start_type'] = 'short_obj'
                r_item['start_data'] = {'component': stg_name, 'pin': 'short'}

            if r_item['end_type'] == 'short':
                stg_coord = coords[-1]
                prev_pt = coords[-2] if len(coords) > 1 else stg_coord
                v_in = stg_coord - prev_pt
                orient = self._calc_short_orientation(v_in)
                stg_name = f"{full_name}__stg"
                stg = ShortToGround(
                    self.design,
                    stg_name,
                    options=dict(
                        pos_x=f"{stg_coord[0]}mm",
                        pos_y=f"{stg_coord[1]}mm",
                        orientation=orient,
                        width=self.trace_width
                    )
                )
                self.shorts[stg_name] = stg
                r_item['end_type'] = 'short_obj'
                r_item['end_data'] = {'component': stg_name, 'pin': 'short'}

        # 3. Create Routes in topological/dependency order so parent routes exist before branch routes attach to them
        # Primary routes (connected to external components or junctions at both ends) are created first.
        created_route_objs = {}  # full_name -> route object

        def instantiate_route(r_item):
            full_name = r_item['full_name']
            coords = r_item['coords']

            # Resolve start pin if it's still 'coord'
            if r_item['start_type'] == 'coord':
                start_pt = coords[0]
                start_key = (round(start_pt[0], 6), round(start_pt[1], 6))
                # Find a parent route containing this coord
                parent_info = self._find_parent_route_for_coord(parsed_routes, start_key, exclude_name=r_item['name'])
                if parent_info:
                    parent_item, toward_pt = parent_info
                    parent_obj = created_route_objs[parent_item['full_name']]
                    pin_name = f"pin_{r_item['name']}_start"
                    in_pts = self._make_pin_points(start_pt[0], start_pt[1], toward_pt[0], toward_pt[1])
                    parent_obj.add_pin(pin_name, in_pts, self.trace_width, input_as_norm=True)
                    r_item['start_type'] = 'added_pin'
                    r_item['start_data'] = {'component': parent_item['full_name'], 'pin': pin_name}

            # Resolve end pin if it's still 'coord'
            if r_item['end_type'] == 'coord':
                end_pt = coords[-1]
                end_key = (round(end_pt[0], 6), round(end_pt[1], 6))
                parent_info = self._find_parent_route_for_coord(parsed_routes, end_key, exclude_name=r_item['name'])
                if parent_info:
                    parent_item, toward_pt = parent_info
                    parent_obj = created_route_objs[parent_item['full_name']]
                    pin_name = f"pin_{r_item['name']}_end"
                    in_pts = self._make_pin_points(end_pt[0], end_pt[1], toward_pt[0], toward_pt[1])
                    parent_obj.add_pin(pin_name, in_pts, self.trace_width, input_as_norm=True)
                    r_item['end_type'] = 'added_pin'
                    r_item['end_data'] = {'component': parent_item['full_name'], 'pin': pin_name}

            if r_item['start_type'] == 'component':
                start_pin = r_item['start_data']['spec']
            elif r_item['start_type'] in ('junction', 'short_obj', 'added_pin'):
                start_pin = r_item['start_data']
            else:
                raise ValueError(
                    f"Route {full_name} has invalid start specification"
                )

            if r_item['end_type'] == 'component':
                end_pin = r_item['end_data']['spec']
            elif r_item['end_type'] in ('junction', 'short_obj', 'added_pin'):
                end_pin = r_item['end_data']
            else:
                raise ValueError(
                    f"Route {full_name} has invalid end specification"
                )

            intermediate_pts = coords[1:-1]

            anchors = OrderedDict(
                (i, np.asarray(pt, dtype=float))
                for i, pt in enumerate(intermediate_pts)
            )

            common_options = dict(
                pin_inputs=dict(
                    start_pin=start_pin,
                    end_pin=end_pin
                ),
                trace_width=self.trace_width,
                trace_gap=self.trace_gap,
                lead=dict(
                    start_straight=self.lead_in,
                    end_straight=self.lead_out
                )
            )

            if len(anchors) == 0:
                route = RouteStraight(
                    self.design,
                    full_name,
                    options=common_options
                )
            else:
                route_options = dict(common_options)
                route_options.update(
                    anchors=anchors,
                    fillet=self.fillet
                )

                route = RouteAnchors(
                    self.design,
                    full_name,
                    options=route_options
                )

            self.routes[full_name] = route
            created_route_objs[full_name] = route

        # Determine creation order: routes with start/end as 'coord' that need parent routes should be built after their parents
        primary_routes = [r for r in parsed_routes if r['start_type'] != 'coord' and r['end_type'] != 'coord']
        secondary_routes = [r for r in parsed_routes if r['start_type'] == 'coord' or r['end_type'] == 'coord']

        for r_item in primary_routes:
            instantiate_route(r_item)

        for r_item in secondary_routes:
            instantiate_route(r_item)

    def _find_parent_route_for_coord(self, parsed_routes, target_key, exclude_name=None):
        """
        Finds a parent route that contains target_key in its coords.
        Returns tuple (parent_route_dict, toward_pt) or None.
        toward_pt is the point on the branch route moving away from target_key or toward the next branch point.
        """
        for r_item in parsed_routes:
            if r_item['name'] == exclude_name:
                continue
            coords = r_item['coords']
            for k, pt in enumerate(coords):
                pt_key = (round(pt[0], 6), round(pt[1], 6))
                if pt_key == target_key:
                    # Find branch's toward_pt from the branch route itself
                    branch_item = next((r for r in parsed_routes if r['name'] == exclude_name), None)
                    toward_pt = None
                    if branch_item:
                        b_coords = branch_item['coords']
                        b_start_key = (round(b_coords[0][0], 6), round(b_coords[0][1], 6))
                        b_end_key = (round(b_coords[-1][0], 6), round(b_coords[-1][1], 6))
                        if b_start_key == target_key and len(b_coords) > 1:
                            toward_pt = b_coords[1]
                        elif b_end_key == target_key and len(b_coords) > 1:
                            toward_pt = b_coords[-2]
                    if toward_pt is None:
                        toward_pt = coords[k+1] if k < len(coords) - 1 else coords[k-1]
                    return r_item, toward_pt
        return None

    def get_total_length(self):
        total = 0.0
        for route in self.routes.values():
            try:
                total += route.length
            except Exception:
                pass
        return total

    def get_route(self, name):
        if name in self.routes:
            return self.routes[name]
        return self.routes.get(f"{self.name}_{name}")

    def get_junction(self, name):
        if name in self.junctions:
            return self.junctions[name]
        for j_name, j_obj in self.junctions.items():
            if name in j_name:
                return j_obj
        return None

    def print_routes(self):
        print("TreeRoute routes:")
        print("-" * 50)
        for name, route in self.routes.items():
            print(f"{name}: {route.__class__.__name__}")

    def print_junctions(self):
        print("TreeRoute junctions:")
        print("-" * 50)
        for name in self.junctions:
            print(name)
