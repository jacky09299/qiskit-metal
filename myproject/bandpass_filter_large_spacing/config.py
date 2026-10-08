from qiskit_metal import Dict
from qiskit_metal.toolbox_metal.parsing import parse_value

# 定義所有版本的完整參數
# 每個 Key (如 '3-1') 裡面都要包含「所有」需要的變數
configs = {
    "2": {
        "draw_L1": True,
        "draw_L2": True,
        "draw_L3": True,
        "draw_L4": True,
        "draw_R1": True,
        "draw_R2": True,
        "draw_R3": True,
        "draw_R4": True,
        "reso_freq": 5,
        "draw_TL_anchors": True,
        "draw_pocket_1": True,
        "draw_pocket_2": True,
        "draw_qubit_1": True,
        "draw_qubit_2": True,
        "draw_reso_1": True,
        "draw_reso_2": True,
        "draw_fl_1": True,
        "draw_fl_2": True,
        "draw_cl_1": True,
        "draw_cl_2": True,
        "draw_folded_TL": True,
        "draw_coupling_pad_1": True,
        "draw_coupling_pad_2": True,
        "draw_couple_line_1": True,
        "draw_couple_line_2": True,
    },
    "3-1": {
        "draw_L1": True,
        "draw_L2": True,
        "draw_L3": True,
        "draw_L4": True,
        "draw_R1": True,
        "draw_R2": True,
        "draw_R3": True,
        "draw_R4": True,
        "reso_freq": 7,
        "draw_TL_anchors": True,
        "draw_pocket_1": True,
        "draw_pocket_2": True,
        "draw_qubit_1": False,
        "draw_qubit_2": False,
        "draw_reso_1": True,
        "draw_reso_2": True,
        "draw_fl_1": True,
        "draw_fl_2": True,
        "draw_cl_1": True,
        "draw_cl_2": True,
        "draw_folded_TL": True,
        "draw_coupling_pad_1": True,
        "draw_coupling_pad_2": True,
        "draw_couple_line_1": True,
        "draw_couple_line_2": True,
    },
    "3-2": {
        "draw_L1": True,
        "draw_L2": True,
        "draw_L3": True,
        "draw_L4": True,
        "draw_R1": True,
        "draw_R2": True,
        "draw_R3": True,
        "draw_R4": True,
        "reso_freq": 5,
        "draw_TL_anchors": True,
        "draw_pocket_1": True,
        "draw_pocket_2": True,
        "draw_qubit_1": False,
        "draw_qubit_2": False,
        "draw_reso_1": True,
        "draw_reso_2": True,
        "draw_fl_1": True,
        "draw_fl_2": True,
        "draw_cl_1": True,
        "draw_cl_2": True,
        "draw_folded_TL": True,
        "draw_coupling_pad_1": True,
        "draw_coupling_pad_2": True,
        "draw_couple_line_1": True,
        "draw_couple_line_2": True,
    },
    "4-1": {
        "draw_L1": True,
        "draw_L2": True,
        "draw_L3": True,
        "draw_L4": True,
        "draw_R1": True,
        "draw_R2": False,
        "draw_R3": False,
        "draw_R4": True,
        "reso_freq": 5,
        "draw_TL_anchors": True,
        "draw_pocket_1": True,
        "draw_pocket_2": False,
        "draw_qubit_1": False,
        "draw_qubit_2": False,
        "draw_reso_1": True,
        "draw_reso_2": False,
        "draw_fl_1": True,
        "draw_fl_2": False,
        "draw_cl_1": True,
        "draw_cl_2": False,
        "draw_folded_TL": True,
        "draw_coupling_pad_1": True,
        "draw_coupling_pad_2": False,
        "draw_couple_line_1": True,
        "draw_couple_line_2": False,
    },
    "4-2": {
        "draw_L1": True,
        "draw_L2": True,
        "draw_L3": True,
        "draw_L4": True,
        "draw_R1": True,
        "draw_R2": False,
        "draw_R3": False,
        "draw_R4": True,
        "reso_freq": 7,
        "draw_TL_anchors": True,
        "draw_pocket_1": True,
        "draw_pocket_2": False,
        "draw_qubit_1": False,
        "draw_qubit_2": False,
        "draw_reso_1": True,
        "draw_reso_2": False,
        "draw_fl_1": True,
        "draw_fl_2": False,
        "draw_cl_1": True,
        "draw_cl_2": False,
        "draw_folded_TL": True,
        "draw_coupling_pad_1": True,
        "draw_coupling_pad_2": False,
        "draw_couple_line_1": True,
        "draw_couple_line_2": False,
    },
    "onlyBPF": {
        "draw_L1": False,
        "draw_L2": False,
        "draw_L3": False,
        "draw_L4": True,
        "draw_R1": False,
        "draw_R2": False,
        "draw_R3": False,
        "draw_R4": True,
        "reso_freq": 5,
        "draw_TL_anchors": False,
        "draw_pocket_1": False,
        "draw_pocket_2": False,
        "draw_qubit_1": False,
        "draw_qubit_2": False,
        "draw_reso_1": False,
        "draw_reso_2": False,
        "draw_fl_1": False,
        "draw_fl_2": False,
        "draw_cl_1": False,
        "draw_cl_2": False,
        "draw_folded_TL": True,
        "draw_coupling_pad_1": False,
        "draw_coupling_pad_2": False,
        "draw_couple_line_1": False,
        "draw_couple_line_2": False,
    }
}    

# In[3]:


target_version = "onlyBPF" 
data = configs[target_version]

# 左邊(L)與右邊(R)結構
draw_L1 = data["draw_L1"]
draw_L2 = data["draw_L2"]
draw_L3 = data["draw_L3"]
draw_L4 = data["draw_L4"]

draw_R1 = data["draw_R1"]
draw_R2 = data["draw_R2"]
draw_R3 = data["draw_R3"]
draw_R4 = data["draw_R4"]

# 核心參數
reso_freq = data["reso_freq"]
draw_TL_anchors = data["draw_TL_anchors"]

# Pocket 與 Qubit
draw_pocket_1 = data["draw_pocket_1"]
draw_pocket_2 = data["draw_pocket_2"]
draw_qubit_1 = data["draw_qubit_1"]
draw_qubit_2 = data["draw_qubit_2"]

# Resonator (Reso)
draw_reso_1 = data["draw_reso_1"]
draw_reso_2 = data["draw_reso_2"]

# Flux Line (fl)
draw_fl_1 = data["draw_fl_1"]
draw_fl_2 = data["draw_fl_2"]

# Charge Line (cl)
draw_cl_1 = data["draw_cl_1"]
draw_cl_2 = data["draw_cl_2"]

# Transmission Line (TL)
draw_folded_TL = data["draw_folded_TL"]

# Coupling Pad
draw_coupling_pad_1 = data["draw_coupling_pad_1"]
draw_coupling_pad_2 = data["draw_coupling_pad_2"]

# Coupling Line
draw_couple_line_1 = data["draw_couple_line_1"]
draw_couple_line_2 = data["draw_couple_line_2"]

# 最後自動產生檔名
save_file_name = f'Fluxonium_readout_cl_fl_filtter_{target_version}.gds'


if reso_freq ==7:
    TL_mid_y2 = 1.0
if reso_freq == 5:
    TL_mid_y2 = 2.0
draw_TL_straight = False


qubit_1_posx = 0.05
qubit_1_posy = -2
qubit_2_posx = 1.350
qubit_2_posy = -2


cpw_width = 0.01
cpw_gap = 0.006
