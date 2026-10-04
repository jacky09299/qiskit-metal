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
    design.chips.main.size.size_y = '10 mm'
    design.chips.main.size.size_z = '-650 um'
    design.chips.main.material = 'sapphire'

    # ==========================================
    # 2. 放置元件 (依序呼叫 layout_builder 函式)
    # ==========================================
    layout_builder.build_ports(design, config)
    layout_builder.build_transmission_lines(design, config)
    layout_builder.build_qubits(design, config)
    layout_builder.build_resonators(design, config)
    layout_builder.build_bias_lines(design, config)
    folded_path, start_x, start_y, n_folds, folded_TL = layout_builder.build_folded_tl(design, config)
    #layout_builder.build_Lshapecpw(design, config, folded_path, start_x, start_y)
    #layout_builder.build_coupling_pad(design, config, folded_path, n_folds, folded_TL)
    layout_builder.build_markers(design, config)

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
    gds_render.options.cheese['view_in_file']['main']={1: True, 2:False}
    gds_render.options.cheese.update(dict(cheese_0_x=0.005, cheese_0_y=0.005, delta_x=0.05, delta_y=0.05))
    
    design.qgeometry.tables['junction']

    design.renderers.gds.options['precision'] = '1e-9'
    design.renderers.gds.options['tolerance'] = '1e-7'
    design.renderers.gds.options['max_points'] = '10000000'
    #design.renderers.gds.options['corners'] = 'circular bend'
    #design.renderers.gds.options['chord_error'] = '1um'

    print("Before export")
    design.renderers.gds.export_to_gds(config.save_file_name)
    print(f"成功導出 GDS: {config.save_file_name}")

if __name__ == "__main__":
    main()
