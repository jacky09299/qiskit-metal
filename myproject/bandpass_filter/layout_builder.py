import numpy as np
import json
from collections import OrderedDict
from qiskit_metal import Dict
from qiskit_metal.toolbox_metal.parsing import parse_value

from qiskit_metal.qlibrary.terminations.launchpad_wb import LaunchpadWirebond
from qiskit_metal.qlibrary.tlines.anchored_path import RouteAnchors
from qiskit_metal.qlibrary.tlines.straight_path import RouteStraight
from qiskit_metal.qlibrary.tlines.pathfinder import RoutePathfinder
from qiskit_metal.qlibrary.tlines.meandered import RouteMeander
from qiskit_metal.qlibrary.terminations.short_to_ground import ShortToGround
from qiskit_metal.qlibrary.sample_shapes.rectangle import Rectangle
from qiskit_metal.qlibrary.sample_shapes.right_triangle import RightTriangle

from qiskit_metal.qlibrary.user_components.self_define import Cross
from qiskit_metal.qlibrary.user_components.fillet_q import Fillet_Qubit
from qiskit_metal.qlibrary.user_components.round_tee import Round_Tee

import config
import components
import utils

def build_ports(design, config):
    # 可控制要畫哪些 port
    # True 表示要畫，False 表示不畫


    x_port, y_port = 3.000, 3.000
    TL_width, TL_gap = 0.020, 0.012

    if config.draw_L1:
        port_L1 = LaunchpadWirebond(design, 'port_L1', options = dict(pos_x = -x_port, pos_y =  y_port, orientation = '  0', 
                                                                  pad_width = 0.5, pad_height = 0.25, pad_gap = 0.2, taper_height = 0.5,
                                                                  lead_length = 0.100, trace_width=0.020, trace_gap=0.012))
    if config.draw_L2:
        port_L2 = LaunchpadWirebond(design, 'port_L2', options = dict(pos_x = -x_port, pos_y =  1.0, orientation = '  0', 
                                                                  pad_width = 0.5, pad_height = 0.25, pad_gap = 0.2, taper_height = 0.5,
                                                                  lead_length = 0.100, trace_width=config.cpw_width, trace_gap=config.cpw_gap))
    if config.draw_L3:
        port_L3 = LaunchpadWirebond(design, 'port_L3', options = dict(pos_x = -x_port, pos_y = -1.0, orientation = '  0', 
                                                                  pad_width = 0.5, pad_height = 0.25, pad_gap = 0.2, taper_height = 0.5,
                                                                  lead_length = 0.100, trace_width=config.cpw_width, trace_gap=config.cpw_gap))
    if config.draw_L4:
        port_L4 = LaunchpadWirebond(design, 'port_L4', options = dict(pos_x = -x_port, pos_y = -y_port, orientation = '  0', 
                                                                  pad_width = 0.5, pad_height = 0.25, pad_gap = 0.2, taper_height = 0.5,
                                                                  lead_length = 0.100, trace_width=config.cpw_width, trace_gap=config.cpw_gap))
    if config.draw_R1:
        port_R1 = LaunchpadWirebond(design, 'port_R1', options = dict(pos_x =  x_port, pos_y =  y_port, orientation = '180', 
                                                                  pad_width = 0.5, pad_height = 0.25, pad_gap = 0.2, taper_height = 0.5,
                                                                  lead_length = 0.100, trace_width=0.020, trace_gap=0.012))
    if config.draw_R2:
        port_R2 = LaunchpadWirebond(design, 'port_R2', options = dict(pos_x =  x_port, pos_y =  1.0, orientation = '180', 
                                                                  pad_width = 0.5, pad_height = 0.25, pad_gap = 0.2, taper_height = 0.5,
                                                                  lead_length = 0.100, trace_width=config.cpw_width, trace_gap=config.cpw_gap))
    if config.draw_R3:
        port_R3 = LaunchpadWirebond(design, 'port_R3', options = dict(pos_x =  x_port, pos_y = -1.0, orientation = '180', 
                                                                  pad_width = 0.5, pad_height = 0.25, pad_gap = 0.2, taper_height = 0.5,
                                                                  lead_length = 0.100, trace_width=config.cpw_width, trace_gap=config.cpw_gap))
    if config.draw_R4:
        port_R4 = LaunchpadWirebond(design, 'port_R4', options = dict(pos_x =  x_port, pos_y = -y_port, orientation = '180', 
                                                                  pad_width = 0.5, pad_height = 0.25, pad_gap = 0.2, taper_height = 0.5,
                                                                  lead_length = 0.100, trace_width=config.cpw_width, trace_gap=config.cpw_gap))
        

def build_transmission_lines(design, config):
    if 'port_R1' in design.components: port_R1 = design.components['port_R1']
    if 'port_L1' in design.components: port_L1 = design.components['port_L1']
    """
    Set transmission line (TL).
    """
    # 可控制是否畫 TL

    TL_width, TL_gap = 0.020, 0.012

    if config.draw_TL_anchors:
        port1y = port_R1.options.pos_y
        mid_x1 = -2.0
        mid_y1 = port1y
        mid_x2 = mid_x1
        mid_y2 = config.TL_mid_y2
        mid_x3 = 2.0
        mid_y3 = mid_y2
        mid_x4 = mid_x3
        mid_y4 = mid_y1
        res_start_y = mid_y2

        anchors = {
            "0": (mid_x1, mid_y1),
            "1": (mid_x2, mid_y2),
            "2": (mid_x3, mid_y3),
            "3": (mid_x4, mid_y4),
        }

        bottom_TL = RouteAnchors(
            design, 'bottom_TL',
            dict(
                pin_inputs = dict(
                    start_pin = dict(component = 'port_L1', pin = 'tie'),
                    end_pin = dict(component = 'port_R1', pin = 'tie')
                ),
                anchors = anchors,
                trace_width = TL_width,
                trace_gap = TL_gap,
                fillet = 0.100,  # 摺疊處為平角
                hfss_wire_bonds = True,
                lead = dict(start_straight=0.500, end_straight=0.500)
            )
        )

    if config.draw_TL_straight:
        port1y = port_R1.options.pos_y
        TL_width, TL_gap = 0.020, 0.012
        res_start_y = port_L1.options.pos_y
        TL = RouteStraight(design, 'TL', 
            dict(pin_inputs = dict(start_pin = dict(component = 'port_L1', pin = 'tie'), 
                                     end_pin = dict(component = 'port_R1', pin = 'tie')),
                 trace_width = TL_width, trace_gap = TL_gap, fillet = 0.10, hfss_wire_bonds = True,
                 lead = dict(start_straight=0.500, end_straight=0.500)))

def build_qubits(design, config):
    """
    Set 3 separated fluxonia with rectangles. Make sure the layers of fluxonium components are correct for fabrication process. 
    """
    x_center, y_center = 0.000, 0.000
    x_dis, y_dis = 1.350, 0.000

    q_opt1 = {'pos_x': config.qubit_1_posx, 'pos_y': config.qubit_1_posy, 'orientation': 0, 
             'pad_gap': 0.030, 'arm_width': 0.008, 'arm_length': 0.090, 'arm_fillet': 0.020,
             'pad_width': 0.200, 'pad_height': 0.050, 'pad_fillet': 0.050, 
             'pocket_width': 0.350, 'pocket_height': 0.500, 'pocket_fillet': 0.050, 
             'layer': 1, 'draw_qubit': config.draw_qubit_1}

    q_opt2 = {'pos_x': config.qubit_2_posx, 'pos_y': config.qubit_2_posy, 'orientation': 0, 
             'pad_gap': 0.030, 'arm_width': 0.008, 'arm_length': 0.090, 'arm_fillet': 0.020,
             'pad_width': 0.200, 'pad_height': 0.050, 'pad_fillet': 0.050, 
             'pocket_width': 0.350, 'pocket_height': 0.500, 'pocket_fillet': 0.050, 
             'layer': 1, 'draw_qubit': config.draw_qubit_2}
    if config.draw_pocket_1:
        Q1 = Fillet_Qubit(design, 'Q1', q_opt1)
    if config.draw_pocket_2:
        Q3 = Fillet_Qubit(design, 'Q3', q_opt2)

def build_resonators(design, config):
    if 'Q1' in design.components: Q1 = design.components['Q1']
    if 'Q3' in design.components: Q3 = design.components['Q3']
    TL_width, TL_gap = 0.020, 0.012
    res_start_y = config.TL_mid_y2
    """
    Set resonators.
    """
    # 新增選擇變數
    # 設定 draw_1 或 draw_2 來選擇要畫哪一個
    # 例如 draw_1=True, draw_2=False 只畫1；draw_1=False, draw_2=True 只畫2
    # 兩個都 False 則都不畫

    if config.draw_reso_1:
        res_width, res_gap = 0.015, 0.009
        if config.reso_freq == 7:
            R1_len = 4.000 # ~ 4.2, 4.3, 4.4 #fr=7.67284
            l_couple, grd_gap = 0.500, 0.004
        if config.reso_freq == 5:
            R1_len = 5.300 #fr=6.02265
            l_couple, grd_gap = 0.700 , 0.004
        spacing, fillet = 0.700, 0.050 # fillet > 1.5*(res_width+res_gap*2)
        R_ext, shift_x, shift_y = 0.200, 0, 0.309
        tee_width, tee_length, tee_fillet = 0.050, 0.100, 0.005

        Tee_1 = Round_Tee(design, "Tee_1",
            dict(ref_qc = Q1, rel_ori = "90", shift_x = shift_x, shift_y = shift_y,
                 cpw_width = res_width, cpw_gap = res_gap, ext_len = R_ext, 
                 tee_width = tee_width, tee_length = tee_length, tee_fillet = tee_fillet)
        )

        stg_q1 = ShortToGround(design, 'stg_q1',
            {'pos_x': Q1.options.pos_x, 'pos_y': config.qubit_1_posy + Tee_1.options.shift_y + Tee_1.options.tee_width/2 + Tee_1.options.ext_len, 'orientation': '270'})
        stg_r1 = ShortToGround(design, 'stg_r1',
            {'pos_x': Q1.options.pos_x-(l_couple+fillet), 'pos_y': res_start_y-TL_gap-res_gap-(TL_width+res_width)/2-grd_gap, 'orientation': '180'})
        start_jog = OrderedDict()
        start_jog[0] = ["R", 0.7]
        R1 = RouteMeander(design, 'R1', 
            options = dict(total_length = R1_len-R_ext, fillet=fillet, hfss_wire_bonds = True, 
                           lead = dict(start_straight=l_couple+fillet, end_straight=0.3,
                                       start_jogged_extension = start_jog), 
                           trace_width = res_width, trace_gap = res_gap,
                           meander = dict(
                               spacing=spacing, 
                               asymmetry=0
                           ),
                           pin_inputs = Dict(start_pin = Dict(component = 'stg_r1', pin = 'short'),
                                               end_pin = Dict(component = 'stg_q1', pin = 'short'))))

    if config.draw_reso_2:
        if config.reso_freq == 7:
            R3_len = 4.100 # ~ 4.2, 4.3, 4.4 #fr=7.48581
            l_couple, grd_gap = 0.505, 0.004
        if config.reso_freq == 5:
            R3_len = 5.455 # fr = 5.85143
            l_couple, grd_gap = 0.730, 0.004
        spacing, fillet = 0.700, 0.050 # fillet > 1.5*(res_width+res_gap*2)
        R_ext, shift_x, shift_y = 0.200, 0, 0.309
        tee_width, tee_length, tee_fillet = 0.050, 0.100, 0.005

        Tee_3 = Round_Tee(design, "Tee_3",
            dict(ref_qc = Q3, rel_ori = "90", shift_x = shift_x, shift_y = shift_y,
                 cpw_width = res_width, cpw_gap = res_gap, ext_len = R_ext, 
                 tee_width = tee_width, tee_length = tee_length, tee_fillet = tee_fillet)
        )

        stg_q3 = ShortToGround(design, 'stg_q3',
            {'pos_x': Q3.options.pos_x, 'pos_y': config.qubit_2_posy + Tee_3.options.shift_y + Tee_3.options.tee_width/2 + Tee_3.options.ext_len, 'orientation': '270'})
        stg_r3 = ShortToGround(design, 'stg_r3',
            {'pos_x': Q3.options.pos_x-(l_couple+fillet), 'pos_y': res_start_y-TL_gap-res_gap-(TL_width+res_width)/2-grd_gap, 'orientation': '180'})
        start_jog = OrderedDict()
        start_jog[0] = ["R", 0.7]
        R3 = RouteMeander(design, 'R3', 
            options = dict(total_length = R3_len-R_ext, fillet=fillet, hfss_wire_bonds = True, 
                           lead = dict(start_straight=l_couple+fillet, end_straight=0.3,
                                       start_jogged_extension = start_jog), 
                           trace_width = res_width, trace_gap = res_gap,
                           meander = dict(
                               spacing=spacing, 
                               asymmetry=0
                           ),
                           pin_inputs = Dict(start_pin = Dict(component = 'stg_r3', pin = 'short'),
                                               end_pin = Dict(component = 'stg_q3', pin = 'short'))))

def build_bias_lines(design, config):
    if 'Q1' in design.components: Q1 = design.components['Q1']
    if 'Q3' in design.components: Q3 = design.components['Q3']
    if 'port_L3' in design.components: port_L3 = design.components['port_L3']
    if 'port_R3' in design.components: port_R3 = design.components['port_R3']
    if 'port_L2' in design.components: port_L2 = design.components['port_L2']
    if 'port_R2' in design.components: port_R2 = design.components['port_R2']
    var = design.variables
    """
    Flux bias line for each qubit. 
    """
    # 新增選擇變數
    # 設定 draw_1 或 draw_2 來選擇要畫哪一個
    # 例如 draw_1=True, draw_2=False 只畫Q1；draw_1=False, draw_2=True 只畫Q3
    # 兩個都 True 則都畫

    if config.draw_fl_1:
        q_loop_width, q_loop_height, q_loop_trace = 0.060, 0.010, 0.002
        loop_H, loop_W, loop_wid = 0.050, 0.090, 0.005
        fl_loop_stg_1A = ShortToGround(design, 'fl_loop_stg_1A', 
            dict(pos_x=Q1.options.pos_x-Q1.options.pocket_width/2, pos_y=Q1.options.pos_y-loop_H/2, orientation=180))
        fl_loop_stg_1B = ShortToGround(design, 'fl_loop_stg_1B', 
            dict(pos_x=Q1.options.pos_x-Q1.options.pocket_width/2, pos_y=Q1.options.pos_y+loop_H/2, orientation=180))
        fl_loop_route_1 = RouteStraight(design, 'fl_loop_route_1',
            dict(trace_width=loop_wid, trace_gap=0, fillet=0.010, hfss_wire_bonds=False,
                 lead = dict(start_straight=loop_W, end_straight=loop_W),
                 pin_inputs = Dict(start_pin = Dict(component = 'fl_loop_stg_1A', pin = 'short'),
                                     end_pin = Dict(component = 'fl_loop_stg_1B', pin = 'short'))))
        fl_q_stg_1 = ShortToGround(design, 'fl_q_stg_1', 
            dict(pos_x=Q1.options.pos_x-Q1.options.pocket_width/2, pos_y=Q1.options.pos_y-loop_H/2, orientation=0))
        fl_q_route_1 = RoutePathfinder(design, 'fl_q_route_1', 
            dict(trace_width=config.cpw_width, trace_gap=config.cpw_gap, fillet=0.050, hfss_wire_bonds=True,
                 lead = dict(start_straight=0.300, end_straight=0.900),
                 pin_inputs = Dict(start_pin = Dict(component = 'port_L3', pin = 'tie'),
                                     end_pin = Dict(component = 'fl_q_stg_1', pin = 'short'))))

    if config.draw_fl_2:
        q_loop_width, q_loop_height, q_loop_trace = 0.060, 0.010, 0.002
        loop_H, loop_W, loop_wid = 0.050, 0.090, 0.005
        fl_loop_stg_3A = ShortToGround(design, 'fl_loop_stg_3A', 
            dict(pos_x=Q3.options.pos_x+Q3.options.pocket_width/2, pos_y=Q3.options.pos_y-loop_H/2, orientation=  0))
        fl_loop_stg_3B = ShortToGround(design, 'fl_loop_stg_3B', 
            dict(pos_x=Q3.options.pos_x+Q3.options.pocket_width/2, pos_y=Q3.options.pos_y+loop_H/2, orientation=  0))
        fl_loop_route_3 = RouteStraight(design, 'fl_loop_route_3',
            dict(trace_width=loop_wid, trace_gap=0, fillet=0.010, hfss_wire_bonds=False,
                 lead = dict(start_straight=loop_W, end_straight=loop_W),
                 pin_inputs = Dict(start_pin = Dict(component = 'fl_loop_stg_3A', pin = 'short'),
                                     end_pin = Dict(component = 'fl_loop_stg_3B', pin = 'short'))))
        fl_q_stg_3 = ShortToGround(design, 'fl_q_stg_3', 
            dict(pos_x=Q3.options.pos_x+Q3.options.pocket_width/2, pos_y=Q3.options.pos_y-loop_H/2, orientation=180))
        fl_q_route_3 = RoutePathfinder(design, 'fl_q_route_3', 
            dict(trace_width=config.cpw_width, trace_gap=config.cpw_gap, fillet=0.050, hfss_wire_bonds=True,
                 lead = dict(start_straight=0.300, end_straight=0.900),
                 pin_inputs = Dict(start_pin = Dict(component = 'port_R3', pin = 'tie'),
                                     end_pin = Dict(component = 'fl_q_stg_3', pin = 'short'))))

    """
    Charge line for each qubit. 
    """

    local_cpw_width, local_cpw_gap = parse_value(var.cpw_width, var), parse_value(var.cpw_gap, var)

    if config.draw_cl_1:
        cl_vac, cl_grd, cl_ext = 0.020, 0.010, 0.300
        cl_shifty = 0.13
        cl_q1_gap_1 = Rectangle(design, 'cl_q1_gap_1', 
            dict(pos_x = Q1.options.pos_x-Q1.options.pocket_width/2-cl_grd-cl_ext/2, pos_y = Q1.options.pos_y+cl_shifty, 
                width = cl_ext, height = local_cpw_gap*2+local_cpw_width, subtract=True))
        cl_q1_trace_1 = Rectangle(design, 'cl_q1_trace_1', 
            dict(pos_x = Q1.options.pos_x-Q1.options.pocket_width/2-cl_grd-cl_ext/2, pos_y = Q1.options.pos_y+cl_shifty, 
                width = cl_ext-cl_vac*2, height = local_cpw_width))
        cl_q_stg_1 = ShortToGround(design, 'cl_q_stg_1', 
            dict(pos_x = Q1.options.pos_x-Q1.options.pocket_width/2-cl_grd-cl_ext+cl_vac, pos_y = Q1.options.pos_y+cl_shifty, 
                orientation=0))


        cl_q_route_1 = RoutePathfinder(design, 'cl_q_route_1', 
            dict(trace_width=local_cpw_width, trace_gap=local_cpw_gap, fillet=0.050, hfss_wire_bonds=True,
                lead = dict(start_straight=0.200, end_straight=0.100),
                pin_inputs = Dict(start_pin = Dict(component = 'port_L2', pin = 'tie'),
                                    end_pin = Dict(component = 'cl_q_stg_1', pin = 'short'))))

    if config.draw_cl_2:
        cl_q1_gap_3 = Rectangle(design, 'cl_q1_gap_3', 
            dict(pos_x = Q3.options.pos_x+Q3.options.pocket_width/2+cl_grd+cl_ext/2, pos_y = Q3.options.pos_y+cl_shifty, 
                width = cl_ext, height = local_cpw_gap*2+local_cpw_width, subtract=True))

        cl_q1_trace_3 = Rectangle(design, 'cl_q1_trace_3', 
            dict(pos_x = Q3.options.pos_x+Q3.options.pocket_width/2+cl_grd+cl_ext/2, pos_y = Q3.options.pos_y+cl_shifty, 
                width = cl_ext-cl_vac*2, height = local_cpw_width))

        cl_q_stg_3 = ShortToGround(design, 'cl_q_stg_3', 
            dict(pos_x = Q3.options.pos_x+Q3.options.pocket_width/2+cl_grd+cl_ext-cl_vac, pos_y = Q3.options.pos_y+cl_shifty, 
                orientation=180))

        cl_q_route_3 = RoutePathfinder(design, 'cl_q_route_3', 
            dict(trace_width=local_cpw_width, trace_gap=local_cpw_gap, fillet=0.050, hfss_wire_bonds=True,
                lead = dict(start_straight=0.200, end_straight=0.100),
                pin_inputs = Dict(start_pin = Dict(component = 'port_R2', pin = 'tie'),
                                    end_pin = Dict(component = 'cl_q_stg_3', pin = 'short'))))

def build_folded_tl(design, config, L_target, S_target, p, r, solution):
    if 'port_L4' in design.components: port_L4 = design.components['port_L4']
    if 'port_R4' in design.components: port_R4 = design.components['port_R4']
    find_bc_solutions = utils.find_bc_solutions
    """
    Add folded transmission line between bottom ports (port_L4 and port_R4)
    """

    if config.draw_folded_TL:
        if solution==None:
            solution = utils.solve_circuit(p, L_target, S_target, r, n_min=2, n_max=60)
            utils.print_solution(solution, p, r)
        prm = solution["params"]
        a, b, c, d, l0 = prm["a"], prm["b"], prm["c"], prm["d"], prm["l0"]
        n = solution["n"]
        
        # 2. 取出希臘字母陣列
        arrs = solution["ten_arrays"]
        alpha   = arrs["alpha"]
        beta    = arrs["beta"]
        gamma   = arrs["gamma"]
        delta   = arrs["delta"]
        epsilon = arrs["epsilon"]
        lamb    = arrs["lambda"]
        zeta      = arrs["zeta"]
        mu      = arrs["mu"]
        eta     = arrs["eta"]
        theta   = arrs["theta"]
        
        # 從 port_L4 的 tie pin 取得實際出線位置，而不是元件的中心點 (pos_x, pos_y)
        start_x, start_y = port_L4.pins['tie']['middle']
        folded_path = utils.generate_meander_points(start_x, start_y, n, alpha, beta, gamma, delta, epsilon, lamb, zeta, mu, eta, theta, a, b, c, d, l0)
        
        folded_TL_width, folded_TL_gap = config.cpw_width, config.cpw_gap
        # 使用 RoutePathfinder 來避免 RouteAnchors 的自動連接限制
        folded_TL = RouteAnchors(
            design, 'folded_TL',
            dict(
                pin_inputs = dict(
                    start_pin = dict(component = 'port_L4', pin = 'tie'),
                    end_pin = dict(component = 'port_R4', pin = 'tie')
                ),
                anchors = folded_path,
                trace_width = folded_TL_width,
                trace_gap = folded_TL_gap,
                fillet = r,
                hfss_wire_bonds = True,
                lead = dict(start_straight=0, end_straight=0)
            )
        )
        actual_length = folded_TL.length
        print(f"元件計算後的實際長度是: {actual_length} mm")

    return folded_path, start_x, start_y, n, folded_TL, solution

def build_Lshapecpw(design, config, folded_path, start_x, start_y,s_pre, length_p,solution):
    # 參數設定
    s_list = [sum(s_pre[:i+1]) for i in range(len(s_pre))]
    print("s_list:", s_list)
    prm = solution["params"]
    a, b, c, d, l0 = prm["a"], prm["b"], prm["c"], prm["d"], prm["l0"]

    if config.draw_folded_TL:
        for idx, s_val in enumerate(s_list):
            #if idx==3: continue
            components.LShapedCPW(design, f"cpw_p{idx}",
                start_x, start_y,
                total_length=length_p[idx],folded_path=folded_path, s=s_val, downlimit = a/2+c+d+0.2)

def build_coupling_pad(design, config, folded_path, n_folds, folded_TL):
    if 'Q1' in design.components: Q1 = design.components['Q1']
    if 'Q3' in design.components: Q3 = design.components['Q3']
    create_u_shape = components.create_u_shape
    qubit_couple_gap = 0.06
    if config.draw_coupling_pad_1:
        padbottom_x = Q1.options.pos_x
        padbottom_y = Q1.options.pos_y - Q1.options.pad_gap/2 - Q1.options.pad_height -Q1.options.arm_length - 0.005 - qubit_couple_gap
        coupling_pad1 = create_u_shape(design, cx=padbottom_x, cy=padbottom_y, name='coupling_pad1')   

    if config.draw_coupling_pad_2:
        padbottom_x = Q3.options.pos_x
        padbottom_y = Q3.options.pos_y - Q3.options.pad_gap/2 - Q3.options.pad_height -Q3.options.arm_length - 0.005 - qubit_couple_gap
        coupling_pad3 = create_u_shape(design, cx=padbottom_x, cy=padbottom_y, name='coupling_pad3')  

    for i in range(n_folds):
        if i+1 != 13 and i+1 !=20:
            continue
        idx_start = 1 + i*5
        idx_end = 2 + i*5
        if idx_end >= len(folded_path):
            break
        x0, y0 = folded_path[idx_start]
        x1, y1 = folded_path[idx_end]
        xm = (x0 + x1) / 2
        ym = (y0 + y1) / 2
        
        folded_TL.add_pin(f"couple_point{i+1}", points = [[xm,ym],[xm,ym+0.0000001]],width = config.cpw_width, input_as_norm=True)


    if config.draw_couple_line_1:
        RoutePathfinder(
            design, 'cpw_couple1',
            dict(
                trace_width=config.cpw_width,
                trace_gap=config.cpw_gap,
                fillet=0.01,
                hfss_wire_bonds=True,
                lead=dict(start_straight=0.1, end_straight=0.1),
                pin_inputs=dict(
                    start_pin=dict(component='folded_TL', pin='couple_point13'),
                    end_pin=dict(component='coupling_pad1_bottom', pin='node')
                )
            )
        )

    if config.draw_couple_line_2:
        RoutePathfinder(
            design, 'cpw_couple2',
            dict(
                trace_width=config.cpw_width,
                trace_gap=config.cpw_gap,
                fillet=0.01,
                hfss_wire_bonds=True,
                lead=dict(start_straight=0.1, end_straight=0.1),
                pin_inputs=dict(
                    start_pin=dict(component='folded_TL', pin='couple_point20'),
                    end_pin=dict(component='coupling_pad3_bottom', pin='node')
                )
            )
        )

def build_markers(design, config):
    x_mark, y_mark = 2.5, 4.1
    x_0 , y_0 = x_mark-0.05, y_mark-0.05
    x_cross, y_cross = x_mark-0.05+0.07925, y_mark+0.0025
    mark_pocket_1 = Rectangle(design, 'mark_pocket_1',
        dict(pos_x= x_mark+0.01, pos_y= y_mark, width=0.120, height=0.100, subtract=True))
    mark_cross_1 = Cross(design, 'mark_cross_1', 
        dict(pos_x= x_cross, pos_y= y_cross, layer='2', width=0.040, height=0.040, trace_width=0.005, subtract=True))
    mark_L_v = Rectangle(design, 'mark_L_v',
        dict(pos_x= x_cross + 0.0125, pos_y= y_cross + 0.0175, layer='2', width=0.005, height=0.005, subtract=True))
    mark_L_h = Rectangle(design, 'mark_L_h',
        dict(pos_x= x_cross + 0.015, pos_y= y_cross + 0.0125, layer='2', width=0.01, height=0.005, subtract=True))
    mark_cross_1_b = Cross(design, 'mark_cross_1_b', 
        dict(pos_x= x_0+0.02675, pos_y= y_0+0.0275, layer='2', width=0.020, height=0.020, trace_width=0.003, subtract=True))
    mark_cross_1_t = Cross(design, 'mark_cross_1_t', 
        dict(pos_x= x_0+0.02675, pos_y= y_0+0.0275+0.045, layer='2', width=0.020, height=0.020, trace_width=0.003, subtract=True))
    mark_b_rec1 = Rectangle(design, 'mark_b_rec1',
        dict(pos_x= x_0+0.01775, pos_y= y_0+0.0365, layer='2', width=0.005, height=0.005, subtract=True))
    mark_b_rec2 = Rectangle(design, 'mark_b_rec2',
        dict(pos_x= x_0+0.01775+0.018, pos_y= y_0+0.0365, layer='2', width=0.005, height=0.005, subtract=True))
    mark_b_rec3 = Rectangle(design, 'mark_b_rec3',
        dict(pos_x= x_0+0.01775+0.018, pos_y= y_0+0.0365-0.018, layer='2', width=0.005, height=0.005, subtract=True))
    mark_t_tri = RightTriangle(design, 'mark_t_tri',dict(pos_x= x_0 +0.03325+0.0025, pos_y= y_0+0.079+0.0025, layer='2', width=0.005, height=0.005, subtract=True))

    mark_group_1 = [
        mark_pocket_1,
        mark_cross_1,
        mark_L_v,
        mark_L_h,
        mark_cross_1_b,
        mark_cross_1_t,
        mark_b_rec1,
        mark_b_rec2,
        mark_b_rec3,
        mark_t_tri
    ]
    mark_group_2_names = [
        'mark_pocket_2',
        'mark_cross_2',
        'mark_L_v_2',
        'mark_L_h_2',
        'mark_cross_2_b',
        'mark_cross_2_t',
        'mark_b_rec1_2',
        'mark_b_rec2_2',
        'mark_b_rec3_2',
        'mark_t_tri_2'
    ]

    mark_2 = design.copy_multiple_qcomponents(
        mark_group_1,
        mark_group_2_names,
        [dict(pos_x=-c.options.pos_x, pos_y=c.options.pos_y) for c in mark_group_1]
    )

    mark_group_3_names = [n.replace('_2', '_3') for n in mark_group_2_names]

    mark_3 = design.copy_multiple_qcomponents(
        mark_group_1,
        mark_group_3_names,
        [dict(pos_x=-c.options.pos_x, pos_y=-c.options.pos_y) for c in mark_group_1]
    )

    mark_group_4_names = [n.replace('_2', '_4') for n in mark_group_2_names]

    mark_4 = design.copy_multiple_qcomponents(
        mark_group_1,
        mark_group_4_names,
        [dict(pos_x=c.options.pos_x, pos_y=-c.options.pos_y) for c in mark_group_1]
    )

    mark_2['mark_t_tri_2'].options.orientation = 90
    mark_3['mark_t_tri_3'].options.orientation = 180
    mark_4['mark_t_tri_4'].options.orientation = 270
