import qiskit_metal as metal
from qiskit_metal import designs, draw
from qiskit_metal import MetalGUI

import config
import layout_builder

def main():
    print(f"正在建立 {config.target_version} 版本的晶片佈局...")
    
    # ==========================================
    # 1. 初始化 Design 與 GUI
    # ==========================================
    design = designs.DesignPlanar()
    gui = MetalGUI(design)
    design.overwrite_enabled = True
    design.chips.main.size.size_x = '10 mm'
    #design.chips.main.size.size_x = '8.8 mm'
    design.chips.main.size.size_y = '10 mm'
    #design.chips.main.size.size_y = '4 mm'#
    #design.chips.main.size.center_y = '-3 mm'#
    design.chips.main.size.size_z = '-650 um'
    design.chips.main.material = 'sapphire'

    # ==========================================
    # 2. 放置元件 (依序呼叫 layout_builder 函式)
    # ==========================================
    r = config.cpw_width/2 + config.cpw_gap + 0.006                     # 轉角圓弧半徑 Fillet R
    

    # 只需要在這裡輸入各段距離和對應的長度
    segments = [8333.2, 9610.17, 9888.05, 9888.05, 9610.17, 8333.2]
    length_p = [1955.08, 513.076, 262.567, 224.401, 262.567, 513.076, 1955.08]
    
    # 自動計算其他所有需要的參數
    segments = [x / 1000 for x in segments]
    length_p = [x / 1000 for x in length_p] # 轉換單位
    import os
    import json
    import utils
    
    layout_builder.build_ports(design, config)
    if 'port_L4' in design.components: port_L4 = design.components['port_L4']
    if 'port_R4' in design.components: port_R4 = design.components['port_R4']
    S_target = abs(port_R4.pins['tie']['middle'][0] - port_L4.pins['tie']['middle'][0])  # 目標水平總跨距 S
    print("S_target: ", S_target)
    a1, a2, a3, b, c, d, delta, n = utils.get_filter_geometry_parameter(segments, S=S_target, b0=0.4, c=0.4, d=0.2, bound=1.2)
    print(a1, a2, a3, b, c, d, delta, n)
    layout_builder.build_tree(design, config, a1, a2, a3, b, c, d, delta, n, length_p)
    #layout_builder.build_transmission_lines(design, config)
    #layout_builder.build_qubits(design, config)
    #layout_builder.build_resonators(design, config)
    #layout_builder.build_bias_lines(design, config)
    #layout_builder.build_coupling_pad(design, config, folded_path, n_folds, folded_TL)
    #layout_builder.build_markers(design, config)

    # ==========================================
    # 3. 刷新 GUI 並截圖
    # ==========================================
    gui.rebuild()
    gui.autoscale()
    gui.screenshot()

    design.components.keys()
    
    # ==========================================
    # 4. GDS 導出設定
    # ==========================================
    gds_render = design.renderers.gds
    gds_render.options
    
    gds_render.options.fabricate = True
    gds_render.options.negative_mask = dict(main=[2])
    gds_render.options.no_cheese['view_in_file']['main']={1: False, 2: False}
    gds_render.options.no_cheese['buffer']='20um'
    gds_render.options.cheese['edge_nocheese']='0.9mm'
    #gds_render.options.cheese['edge_nocheese']='4.9mm'
    #gds_render.options.cheese['view_in_file']['main']={1: True, 2:False}
    gds_render.options.cheese['view_in_file']['main']={1: False, 2: False}
    gds_render.options.cheese.update(dict(cheese_0_x=0.005, cheese_0_y=0.005, delta_x=0.05, delta_y=0.05))
    
    design.qgeometry.tables['junction']

    #design.renderers.gds.options['precision'] = '1e-9'
    design.renderers.gds.options['precision'] = '1e-9'
    #design.renderers.gds.options['tolerance'] = '1e-7'
    design.renderers.gds.options['tolerance'] = '1e-5'
    design.renderers.gds.options['max_points'] = '10000000'
    #design.renderers.gds.options['corners'] = 'circular bend'
    #design.renderers.gds.options['chord_error'] = '1um'

    print("Before export")
    #design.renderers.gds.export_to_gds(config.save_file_name)
    print(f"成功導出 GDS: {config.save_file_name}")
    
    # 保持 GUI 視窗開啟
    print("開啟 GUI... (請手動關閉視窗以結束程式)")
    gui.main_window.show()
    gui.qApp.exec_()

if __name__ == "__main__":
    main()
