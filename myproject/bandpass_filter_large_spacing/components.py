import numpy as np
from qiskit_metal.qlibrary.core import QComponent
from qiskit_metal.qlibrary.sample_shapes.rectangle import Rectangle
from qiskit_metal.qlibrary.tlines.straight_path import RouteStraight
from qiskit_metal.qlibrary.tlines.anchored_path import RouteAnchors
from qiskit_metal.qlibrary.terminations.short_to_ground import ShortToGround
import config
import utils
'''
class LShapedCPW:
    """
    通用的 L 型 CPW 走线类，支持以下六种类型：
      - initial_L: 向下 vertical，再向右剩余 horizontal
      - right_L: 向右 small (0.05)，再向下剩余 (total_length - small)
      - left_L: 向左 small (0.05)，再向下剩余
      - bottom_L: 向下 small (0.2)，再向右剩余
      - top: 向下 entire total_length（直线）
      - end_L: 向下 0.6，再向左剩余
    """
    TYPES = ("initial_L", "right_L", "left_L", "bottom_L", "top", "end_L")

    def __init__(self, design, name,
                 start_x, start_y,
                 total_length,
                 trace_width=config.cpw_width, trace_gap=config.cpw_gap, fillet=None,
                 trace_type=None,
                 folded_path=None, s=None, downlimit=1.1,a=0.1,b=0.1,c=0.1):
        self.design = design
        self.name = name
        if 'port_L4' in design.components: port_L4 = design.components['port_L4']
        if 'port_R4' in design.components: port_R4 = design.components['port_R4']
        (self.start_x, self.start_y), self.tag = utils.get_xy_on_folded_path(folded_path, s, config.cpw_width/2 + config.cpw_gap + 0.006, port_L4.pins['tie']['middle'][0], port_L4.pins['tie']['middle'][1], port_R4.pins['tie']['middle'][0], port_R4.pins['tie']['middle'][1],a,c)
        self.total = total_length
        self.start_component = self.design.components['folded_TL'].name
        self.trace_width = trace_width
        self.trace_gap = trace_gap
        self.fillet = config.cpw_width/2 + config.cpw_gap + 0.006
        self.start_pin = "bottom"  # 默认起始 pin
        self.folded_path = folded_path
        self.s = s
        self.downlimit = downlimit
        self.b = b

        # 决定类型
        self.trace_type = trace_type or self._determine_type()
        if self.trace_type not in self.TYPES:
            raise ValueError(f"未知类型 {self.trace_type}")

        # 调用对应的 builder
        getattr(self, f"_build_{self.trace_type}")()

    def _determine_type(self):
            print(f"Determining type based on tag: {self.tag}")
            if self.tag == 0:
                return "right_L"
            elif self.tag == 1:
                return "top"
            elif self.tag == 2:
                return "left_L"
            elif self.tag == 3:
                return "bottom_L"
            elif self.tag == 4:
                return "right_L"
            elif self.tag == -1:
                return "initial_L"
            elif self.tag == 5:
                return "end_L"

    def _build_initial_L(self):
        # 向下 self.vertical，再向右剩余
        down = self.downlimit
        #down = 1.6
        sx, sy = self.start_x, self.start_y
        if down > self.total:
            sx, sy = self.start_x, self.start_y
            short_x = sx
            short_y = sy - self.total
            self._add_short(short_x, short_y, orientation="270")
            self.design.components['folded_TL'].add_pin(f"{self.name}_start", points = [[sx,sy],[sx,sy-0.0000001]],width = config.cpw_width, input_as_norm=True)
            self.start_pin = f"{self.name}_start"
            RouteStraight(self.design, self.name, options=dict(
                pin_inputs=dict(
                    start_pin=dict(component="folded_TL", pin=f"{self.name}_start"),
                    end_pin=dict(component=self.short_name, pin="short")
                ),
                trace_width=config.cpw_width, trace_gap=config.cpw_gap
            ))
            return

        short_x = sx + (self.total - down) + (2 - np.pi/2) * self.fillet
        short_y = sy - down
        self._add_short(short_x, short_y, orientation="0")
        self.design.components['folded_TL'].add_pin(f"{self.name}_start", points = [[sx,sy],[sx,sy-0.0000001]],width = config.cpw_width, input_as_norm=True)
        self.start_pin = f"{self.name}_start"
        anchors = {
            "0": (sx, short_y)
        }
        self._add_route(anchors)


    def _build_right_L(self):
        # 先向右 small，再向下 total-small
        small = 1.5*self.b
        #small = 0.14
        sx, sy = self.start_x, self.start_y
        if small > self.total:
            sx, sy = self.start_x, self.start_y
            short_x = sx + self.total
            short_y = sy
            self._add_short(short_x, short_y, orientation="0")
            self.design.components['folded_TL'].add_pin(f"{self.name}_start", points = [[sx,sy],[sx+0.0000001,sy]],width = config.cpw_width, input_as_norm=True)
            self.start_pin = f"{self.name}_start"
            RouteStraight(self.design, self.name, options=dict(
                pin_inputs=dict(
                    start_pin=dict(component="folded_TL", pin=f"{self.name}_start"),
                    end_pin=dict(component=self.short_name, pin="short")
                ),
                trace_width=config.cpw_width, trace_gap=config.cpw_gap
            ))
            return
        mid_x = sx + small
        mid_y = sy
        short_x = mid_x
        short_y = sy - (self.total - small + (2 - np.pi/2) * self.fillet)

        self.design.components['folded_TL'].add_pin(f"{self.name}_start", points = [[sx,sy],[sx+0.0000001,sy]],width = config.cpw_width, input_as_norm=True)
        self.start_pin = f"{self.name}_start"

        # 判斷是否需要再折一次
        port4y = self.design.components['port_R4'].options.pos_y
        ######################################################################################
        if short_y < port4y - self.downlimit:
            fold_x = mid_x
            fold_y = port4y - self.downlimit
            short_x = fold_x + (self.total - (mid_x - sx +  mid_y-fold_y) + (2 - np.pi/2) * self.fillet*2)
            short_y = fold_y

            # 最後 short
            self._add_short(short_x, short_y, orientation="0")
            anchors = {
                "0": (mid_x, mid_y),
                "1": (fold_x, fold_y)
            }
            self._add_route(anchors)


        else:
            # 原本的兩段
            self._add_short(short_x, short_y, orientation="270")

            anchors = {
                "0": (mid_x, mid_y),
            }
            self._add_route(anchors)

    def _build_left_L(self):
        # 向左 0.05，再向下剩余
        small = 1.5*self.b
        sx, sy = self.start_x, self.start_y
        if small > self.total:
            sx, sy = self.start_x, self.start_y
            short_x = sx - self.total
            short_y = sy
            self._add_short(short_x, short_y, orientation="180")
            self.design.components['folded_TL'].add_pin(f"{self.name}_start", points = [[sx,sy],[sx-0.0000001,sy]],width = config.cpw_width, input_as_norm=True)
            self.start_pin = f"{self.name}_start"
            RouteStraight(self.design, self.name, options=dict(
                pin_inputs=dict(
                    start_pin=dict(component="folded_TL", pin=f"{self.name}_start"),
                    end_pin=dict(component=self.short_name, pin="short")
                ),
                trace_width=config.cpw_width, trace_gap=config.cpw_gap
            ))
            return
        mid_x = sx - small
        mid_y = sy
        short_x = mid_x
        short_y = sy - (self.total - small + (2 - np.pi/2) * self.fillet)
        self.design.components['folded_TL'].add_pin(f"{self.name}_start", points = [[sx,sy],[sx-0.0000001,sy]],width = config.cpw_width, input_as_norm=True)
        self.start_pin = f"{self.name}_start"

        port4y = self.design.components['port_R4'].options.pos_y
        if short_y < port4y - self.downlimit:
            fold_x = mid_x
            fold_y = port4y - self.downlimit
            short_x = fold_x + (self.total - (sx - mid_x +  mid_y-fold_y) + (2 - np.pi/2) * self.fillet*2)
            short_y = fold_y

            # 最後 short
            self._add_short(short_x, short_y, orientation="0")
            anchors = {
                "0": (mid_x, mid_y),
                "1": (fold_x, fold_y)
            }
            self._add_route(anchors)

        else:
            self._add_short(short_x, short_y, orientation="270")
            anchors = {
                    "0": (mid_x, mid_y)
                }
            self._add_route(anchors)


    def _build_bottom_L(self):
        # 向下 0.2，再向右剩余
        down = 0.2
        sx, sy = self.start_x, self.start_y
        mid_x = sx
        mid_y = sy - down
        short_x = sx + (self.total - down + (2 - np.pi/2) * self.fillet)
        short_y = sy - down
        self._add_short(short_x, short_y, orientation="0")
        self.design.components['folded_TL'].add_pin(f"{self.name}_start", points = [[sx,sy],[sx,sy-0.0000001]],width = config.cpw_width, input_as_norm=True)
        self.start_pin = f"{self.name}_start"
        anchors = {
                "0": (mid_x, mid_y)
            }
        self._add_route(anchors)

    def _build_top(self):
        # 向下 entire total_length（直线）
        sx, sy = self.start_x, self.start_y
        short_x = sx
        short_y = sy - self.total
        self._add_short(short_x, short_y, orientation="270")
        self.design.components['folded_TL'].add_pin(f"{self.name}_start", points = [[sx,sy],[sx,sy-0.0000001]],width = config.cpw_width, input_as_norm=True)
        self.start_pin = f"{self.name}_start"
        RouteStraight(self.design, self.name, options=dict(
            pin_inputs=dict(
                start_pin=dict(component="folded_TL", pin=f"{self.name}_start"),
                end_pin=dict(component=self.short_name, pin="short")
            ),
            trace_width=config.cpw_width, trace_gap=config.cpw_gap
        ))

    def _build_end_L(self):
        down = self.downlimit
        #down = 1.6
        sx, sy = self.start_x, self.start_y
        if down > self.total:
            sx, sy = self.start_x, self.start_y
            short_x = sx
            short_y = sy - self.total
            self._add_short(short_x, short_y, orientation="270")
            self.design.components['folded_TL'].add_pin(f"{self.name}_start", points = [[sx,sy],[sx,sy-0.0000001]],width = config.cpw_width, input_as_norm=True)
            self.start_pin = f"{self.name}_start"
            RouteStraight(self.design, self.name, options=dict(
                pin_inputs=dict(
                    start_pin=dict(component="folded_TL", pin=f"{self.name}_start"),
                    end_pin=dict(component=self.short_name, pin="short")
                ),
                trace_width=config.cpw_width, trace_gap=config.cpw_gap
            ))
            return
        mid_x = sx
        mid_y = sy - down
        short_x = mid_x - (self.total - down + (2 - np.pi/2) * self.fillet)
        short_y = mid_y
        self._add_short(short_x, short_y, orientation="180")
        self.design.components['folded_TL'].add_pin(f"{self.name}_start", points = [[sx,sy],[sx,sy-0.0000001]],width = config.cpw_width, input_as_norm=True)
        self.start_component = 'folded_TL'
        self.start_pin = f"{self.name}_start"
        anchors = {
            "0": (mid_x, mid_y)
        }
        self._add_route(anchors, leading=0.200)


    def _add_short(self, x, y, orientation):
        stg_name = f"{self.name}_stg"
        ShortToGround(self.design, stg_name,
                      options=dict(
                          pos_x=x,
                          pos_y=y,
                          orientation=orientation
                      ))
        self.short_name = stg_name

    def _add_route(self, anchors, leading=0.050):
        RouteAnchors(self.design, self.name,
            options=dict(
                pin_inputs=dict(
                    start_pin=dict(component=self.start_component, pin=self.start_pin),
                    end_pin=dict(component=self.short_name, pin="short")
                ),
                trace_width=self.trace_width,
                trace_gap=self.trace_gap,
                fillet=self.fillet,
                anchors=anchors,
                lead = dict(start_straight=leading)
            )
        )
'''

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


# === 使用範例 ===
def example_usage():
    """
    使用範例
    """
    # 創建 U 形元件
    u_shape = UShapeComponent(design, 'my_u_shape')

    # 在指定位置創建
    cx, cy = 0, 0  # 輸入你的座標
    u_shape.create(cx, cy)

    # 重建和顯示
    gui.rebuild()
    gui.autoscale()
    gui.screenshot()

    # 可選：更新位置
    # u_shape.update_position(1, 1)

    # 可選：更新尺寸
    # u_shape.update_dimensions(bl=0.5, sh=0.2, tw=0.01)

    return u_shape


# === 快速創建函數 ===
def create_u_shape(design, cx, cy, name='u_shape', bl=0.3, sh=0.1, tw=0.01):
    """
    快速創建 U 形元件的便利函數

    Args:
        design: 設計物件
        cx, cy: 中心座標
        name: 元件名稱
        bl: 底部寬度
        sh: 側邊高度  
        tw: 線條厚度

    Returns:
        UShapeComponent: U 形元件實例
    """
    u_shape = UShapeComponent(design, name, bl, sh, tw)
    u_shape.create(cx, cy)
    return u_shape
    
import numpy as np

from collections import OrderedDict

from qiskit_metal import QComponent

from qiskit_metal.qlibrary.tlines.anchored_path import RouteAnchors
from qiskit_metal.qlibrary.tlines.straight_path import RouteStraight


class VirtualJunction(QComponent):
    """
    用來作為 TreeRoute 分岔點的隱形元件。

    可以根據輸入動態產生任意數量的 pins，
    讓 RouteAnchors / RouteStraight 附著。

    本身不產生任何金屬圖形，只提供連接點。
    """

    default_options = dict(
        # dict of:
        # pin_name: {
        #     'points': [[x1, y1], [x2, y2]],
        #     'width': 10
        # }
        pins={}
    )

    def make(self):
        for pin_name, pinfo in self.p.pins.items():

            # input_as_norm=True:
            #
            # points[0] -> points[1] 的方向會被當成 normal
            #
            # 注意：
            # 實際 middle 的定義依 Qiskit Metal add_pin()
            # 的處理方式而定。
            self.add_pin(
                pin_name,
                pinfo['points'],
                pinfo['width'],
                input_as_norm=True
            )


class TreeRoute:
    """
    將多個 RouteAnchors / RouteStraight
    組合成樹狀結構的管理器。

    功能：
    --------------------------------------------------
    1. 自動建立 VirtualJunction
    2. 自動建立各段 route
    3. 有 anchors -> RouteAnchors
    4. 無 anchors -> RouteStraight
    5. 支援任意層數的 branch
    6. 提供 route / junction 存取
    7. 提供總長度計算


    tree_config 範例
    --------------------------------------------------

    {
        'name': 'root',

        'start_pin': {
            'component': 'port1',
            'pin': 'tie'
        },

        'anchors': OrderedDict({
            1: [0, 1]
        }),

        'junction_coord': [0, 2],

        'branches': [
            {
                'name': 'branchA',

                'anchors': OrderedDict({
                    1: [1, 2]
                }),

                'end_pin': {
                    'component': 'short1',
                    'pin': 'short'
                }
            },

            {
                'name': 'branchB',

                'anchors': OrderedDict(),

                'junction_coord': [-1, 3],

                'branches': [
                    ...
                ]
            }
        ]
    }


    Route 選擇：
    --------------------------------------------------

    anchors != empty
        -> RouteAnchors

    anchors == empty
        -> RouteStraight

    這樣可以避免 RouteAnchors 在 anchors 為空時，
    某些幾何條件造成：

        np.concatenate([])

    的錯誤。
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

        self.trace_width = trace_width
        self.trace_gap = trace_gap

        self.fillet = fillet

        self.lead_in = lead_in
        self.lead_out = lead_out

        # 保存所有產生的：
        #
        # RouteAnchors
        # RouteStraight
        #
        # 格式：
        #
        # {
        #     'tree_root': instance,
        #     'tree_branchA': instance,
        #     ...
        # }
        self.routes = {}

        # 保存所有 VirtualJunction
        #
        # {
        #     'tree_root_junc': instance,
        #     ...
        # }
        self.junctions = {}

        # 建立整棵 routing tree
        self._build_tree(self.tree_config)


    # =========================================================
    # Utility
    # =========================================================

    def _get_coord(self, pin_dict):
        """
        根據：

        {
            'component': component_name,
            'pin': pin_name
        }

        取得 pin 的 middle coordinate。
        """

        comp = self.design.components[
            pin_dict['component']
        ]

        return comp.pins[
            pin_dict['pin']
        ]['middle']


    def _make_pin_points(
        self,
        jx,
        jy,
        toward_x,
        toward_y,
        step=0.01
    ):
        """
        建立 VirtualJunction pin 所需的兩個點。

        In Qiskit Metal `QComponent.add_pin(..., input_as_norm=True)`:
            points[1] is assigned as the pin's `middle` position,
            and (points[1] - points[0]) / norm is assigned as the outward `normal` vector.

        For an output pin pointing towards (toward_x, toward_y):
            - `middle` must be exactly [jx, jy].
            - `normal` vector points towards (toward_x, toward_y).
            - points[0] = [jx - ux * step, jy - uy * step]
            - points[1] = [jx, jy]
        """

        dx = toward_x - jx
        dy = toward_y - jy

        mag = np.hypot(dx, dy)

        if mag == 0:
            ux = 1.0
            uy = 0.0

        else:
            ux = dx / mag
            uy = dy / mag

        return [
            [
                jx - ux * step,
                jy - uy * step
            ],
            [jx, jy]
        ]


    # =========================================================
    # Tree Builder
    # =========================================================

    def _build_tree(
        self,
        node_config,
        parent_pin=None
    ):
        """
        遞迴建立 routing tree。
        """

        # -----------------------------------------------------
        # Route name
        # -----------------------------------------------------

        node_name = node_config.get(
            'name',
            str(len(self.routes))
        )

        route_name = f"{self.name}_{node_name}"


        # -----------------------------------------------------
        # Start pin
        # -----------------------------------------------------

        start_pin = node_config.get(
            'start_pin',
            parent_pin
        )


        # -----------------------------------------------------
        # Anchors
        # -----------------------------------------------------

        anchors_dict = node_config.get(
            'anchors',
            OrderedDict()
        )

        anchors = OrderedDict()

        for k, v in anchors_dict.items():
            anchors[k] = np.array(
                v,
                dtype=float
            )


        # -----------------------------------------------------
        # End pin
        # -----------------------------------------------------

        end_pin = None


        # =====================================================
        # Case 1
        #
        # Leaf node：
        # 已經有真正的 end_pin
        # =====================================================

        if 'end_pin' in node_config:

            end_pin = node_config['end_pin']


        # =====================================================
        # Case 2
        #
        # Junction node
        # =====================================================

        elif 'junction_coord' in node_config:

            jx, jy = node_config[
                'junction_coord'
            ]

            j_name = f"{route_name}_junc"


            # -------------------------------------------------
            # 找 junction 的來源方向
            # -------------------------------------------------

            if len(anchors) > 0:

                # 最後一個 anchor
                prev_pt = list(
                    anchors.values()
                )[-1]

            else:

                # 沒有 anchor
                # 直接看 start pin
                prev_pt = self._get_coord(
                    start_pin
                )


            # -------------------------------------------------
            # Junction input pin
            #
            # normal 朝來源方向
            # -------------------------------------------------

            in_pts = self._make_pin_points(
                jx,
                jy,
                prev_pt[0],
                prev_pt[1]
            )


            pins_config = {

                'in': {
                    'points': in_pts,
                    'width': self.trace_width
                }

            }


            # -------------------------------------------------
            # Branches
            # -------------------------------------------------

            branches = node_config.get(
                'branches',
                []
            )


            # -------------------------------------------------
            # 建立所有 output pins
            # -------------------------------------------------

            for idx, branch in enumerate(
                branches
            ):

                pin_name = f'out_{idx}'

                b_anchors = branch.get(
                    'anchors',
                    OrderedDict()
                )


                # ---------------------------------------------
                # Branch 有 anchor
                # ---------------------------------------------

                if len(b_anchors) > 0:

                    next_pt = list(
                        b_anchors.values()
                    )[0]


                # ---------------------------------------------
                # Branch 無 anchor
                # ---------------------------------------------

                else:

                    if 'end_pin' in branch:

                        next_pt = self._get_coord(
                            branch['end_pin']
                        )

                    elif 'junction_coord' in branch:

                        next_pt = branch[
                            'junction_coord'
                        ]

                    else:

                        # fallback
                        next_pt = [
                            jx,
                            jy - 1
                        ]


                # ---------------------------------------------
                # Output pin normal 朝 branch 方向
                # ---------------------------------------------

                out_pts = self._make_pin_points(
                    jx,
                    jy,
                    next_pt[0],
                    next_pt[1]
                )


                pins_config[
                    pin_name
                ] = {

                    'points': out_pts,

                    'width':
                        self.trace_width

                }


            # =================================================
            # 建立 Virtual Junction
            # =================================================

            junction = VirtualJunction(
                self.design,
                j_name,
                options=dict(
                    pins=pins_config
                )
            )


            self.junctions[
                j_name
            ] = junction


            # -------------------------------------------------
            # Parent route 的終點
            # -------------------------------------------------

            end_pin = {
                'component': j_name,
                'pin': 'in'
            }


        # =====================================================
        # 建立目前這一段 Route
        # =====================================================

        if start_pin is not None and end_pin is not None:

            # 所有 route 共用設定
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


            # =================================================
            # 沒有 Anchors
            #
            # 使用 RouteStraight
            # =================================================

            if len(anchors) == 0:

                route = RouteStraight(
                    self.design,
                    route_name,
                    options=common_options
                )


            # =================================================
            # 有 Anchors
            #
            # 使用 RouteAnchors
            # =================================================

            else:

                route_options = dict(
                    common_options
                )

                route_options.update(
                    anchors=anchors,
                    fillet=self.fillet
                )

                route = RouteAnchors(
                    self.design,
                    route_name,
                    options=route_options
                )


            # 保存 route instance
            self.routes[
                route_name
            ] = route


        # =====================================================
        # 建立 Child Routes
        #
        # 注意：
        #
        # 這裡刻意放在目前 route 建立完成之後。
        #
        # 順序：
        #
        # VirtualJunction
        #       ↓
        # Parent Route
        #       ↓
        # Child Routes
        #
        # dependency 比較清楚。
        # =====================================================

        if (
            'junction_coord' in node_config
            and 'end_pin' not in node_config
        ):

            j_name = f"{route_name}_junc"

            branches = node_config.get(
                'branches',
                []
            )

            for idx, branch in enumerate(
                branches
            ):

                child_start_pin = {

                    'component':
                        j_name,

                    'pin':
                        f'out_{idx}'

                }

                self._build_tree(
                    branch,
                    child_start_pin
                )


    # =========================================================
    # Length
    # =========================================================

    def get_total_length(self):
        """
        計算所有 route 的幾何總長度。

        包含：

        - RouteAnchors
        - RouteStraight

        如果某個 route 尚未 build 或 length 無法讀取，
        則跳過該 route。
        """

        total = 0.0

        for route in self.routes.values():

            try:

                total += route.length

            except Exception:

                pass

        return total


    # =========================================================
    # Route Access
    # =========================================================

    def get_route(self, name):
        """
        取得指定名稱的 route。

        例如：

            tree.get_route('branchA')

        實際尋找：

            <tree_name>_branchA

        回傳可能為：

            RouteAnchors

        或：

            RouteStraight
        """

        return self.routes.get(
            f"{self.name}_{name}"
        )


    # =========================================================
    # Junction Access
    # =========================================================

    def get_junction(self, name):
        """
        取得某個 node 所建立的 VirtualJunction。

        例如：

            tree.get_junction('root')

        實際尋找：

            <tree_name>_root_junc
        """

        return self.junctions.get(
            f"{self.name}_{name}_junc"
        )


    # =========================================================
    # Debug
    # =========================================================

    def print_routes(self):
        """
        印出所有 route 與實際使用的 route type。
        """

        print("TreeRoute routes:")
        print("-" * 50)

        for name, route in self.routes.items():

            print(
                f"{name}: "
                f"{route.__class__.__name__}"
            )


    def print_junctions(self):
        """
        印出所有 VirtualJunction。
        """

        print("TreeRoute junctions:")
        print("-" * 50)

        for name in self.junctions:

            print(name)
