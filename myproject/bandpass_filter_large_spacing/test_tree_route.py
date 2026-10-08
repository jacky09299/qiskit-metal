import qiskit_metal as metal
from qiskit_metal import designs
try:
    from qiskit_metal import MetalGUI
except ImportError:
    MetalGUI = None
from qiskit_metal.qlibrary.terminations.open_to_ground import OpenToGround
from qiskit_metal.qlibrary.terminations.short_to_ground import ShortToGround
from collections import OrderedDict
from components import TreeRoute


def run_test():
    # 建立設計與 GUI
    design = designs.DesignPlanar()
    gui = MetalGUI(design) if MetalGUI is not None else None


    # port1 在左邊，開口朝右 (orientation=180 → normal=[1,0])
    port1 = OpenToGround(design, 'port1', options=dict(
        pos_x='-2mm', pos_y='0mm', orientation='180'
    ))
    # port2 在右邊，開口朝左 (orientation=0 → normal=[-1,0])
    port2 = OpenToGround(design, 'port2', options=dict(
        pos_x='2mm', pos_y='0mm', orientation='0'
    ))
    # short 在下方，開口朝上 (orientation=90 → normal=[0,1])
    short1 = ShortToGround(design, 'short1', options=dict(
        pos_x='0mm', pos_y='-1.5mm', orientation='90',
        width='10um'
    ))


    # 結構：port1 → 往右走到 [0, 0] 分岔
    #   分支 A：往右繼續接 port2
    #   分支 B：往下接 short1
    tree_config = {
        'name': 'root',
        'start_pin': {'component': 'port1', 'pin': 'open'},
        'anchors': OrderedDict(),          # 從 port1 直接走到分岔點
        'junction_coord': [0, 0],          # 分岔點在原點


        'branches': [
            {
                # 分支 A：往右接 port2
                'name': 'to_port2',
                'anchors': OrderedDict(),  # 直線，無中繼點
                'end_pin': {'component': 'port2', 'pin': 'open'}
            },
            {
                # 分支 B：往下接 short1
                'name': 'to_short',
                'anchors': OrderedDict(),  # 直線，無中繼點
                'end_pin': {'component': 'short1', 'pin': 'short'}
            }
        ]
    }


    my_tree = TreeRoute(
        design=design,
        name='simple_test',
        tree_config=tree_config,
        trace_width='10um',
        trace_gap='6um',
        fillet='0'   # 直線測試先不加 fillet
    )


    if gui:
        gui.rebuild()
        gui.autoscale()


    print("==== 測試結果 ====")
    r_root   = my_tree.get_route('root')
    r_port2  = my_tree.get_route('to_port2')
    r_short  = my_tree.get_route('to_short')


    if r_root:  print(f"Root (port1→分岔)  .length = {r_root.length:.4f} mm")
    if r_port2: print(f"Branch A (→port2)  .length = {r_port2.length:.4f} mm")
    if r_short: print(f"Branch B (→short)  .length = {r_short.length:.4f} mm")
    print(f"總長度 = {my_tree.get_total_length():.4f} mm")


    if gui and hasattr(gui, 'main_window') and gui.main_window:
        gui.main_window.show()
        gui.qApp.exec_()


if __name__ == '__main__':
    run_test()
