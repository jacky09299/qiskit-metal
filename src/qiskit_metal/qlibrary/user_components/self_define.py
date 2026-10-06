from qiskit_metal.qlibrary.core import QComponent
from qiskit_metal import draw
from shapely.geometry import box

class Cross(QComponent):
    """十字交叉形狀，用於標記或對位用途"""

    default_options = dict(
        pos_x='0um',
        pos_y='0um',
        width='0.04mm',
        height='0.04mm',
        trace_width='0.005mm',
        layer='1',
        subtract=False
    )

    def make(self):
        p = self.parse_options()

        cx, cy = float(p.pos_x), float(p.pos_y)
        w, h = float(p.width)/2, float(p.height)/2
        t = float(p.trace_width)/2

        # 畫水平長條
        h_rect = box(cx - w, cy - t, cx + w, cy + t)
        # 畫垂直長條
        v_rect = box(cx - t, cy - h, cx + t, cy + h)
        # 合併成十字
        cross_shape = h_rect.union(v_rect)

        self.add_qgeometry('poly', {'cross': cross_shape}, layer=p.layer, subtract=p.subtract)
