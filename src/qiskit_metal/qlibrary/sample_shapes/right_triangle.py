# -*- coding: utf-8 -*-

from qiskit_metal import draw, Dict
from qiskit_metal.qlibrary.core import QComponent

class RightTriangle(QComponent):
    """A right-angle triangle (left and bottom edges) positioned by hypotenuse center."""

    default_options = Dict(
        width='30um',     # x 方向邊長
        height='30um',    # y 方向邊長
        subtract='False',
        helper='False'
    )

    TOOLTIP = """A right-angle triangle with left and bottom edges, positioned by hypotenuse center"""

    def make(self):
        p = self.p

        # 斜邊中心到直角點的向量
        pos_right_angle_x = p.pos_x - p.width / 2
        pos_right_angle_y = p.pos_y - p.height / 2

        # 定義三個點（直角在 pos_right_angle_x, pos_right_angle_y）
        points = [
            (pos_right_angle_x, pos_right_angle_y),             # 左下（直角）
            (pos_right_angle_x + p.width, pos_right_angle_y),   # 右下
            (pos_right_angle_x, pos_right_angle_y + p.height)   # 左上
        ]

        # 建立 polygon
        tri = draw.Polygon(points)

        # 支援旋轉
        tri = draw.rotate(tri, p.orientation)

        # 加入 qgeometry
        self.add_qgeometry(
            'poly',
            {'triangle': tri},
            subtract=p.subtract,
            helper=p.helper,
            layer=p.layer,
            chip=p.chip
        )
