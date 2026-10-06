import numpy as np
from scipy.optimize import linprog
from collections import OrderedDict
import config
    
def get_xy_on_folded_path(folded_path, s, r, start_x, start_y, end_x, end_y,a,c):
    """
    給定folded_path (OrderedDict, key為int, value為(x, y)) 和長度s (mm)，
    回傳走s後的(x, y)座標。
    若s超過總長度，則回傳最後一點。
    """
    import numpy as np
    # 取得所有點
    points = list(folded_path.values())
    # 添加初始點
    zero_point = (start_x, start_y)
    points.insert(0, zero_point)
    end_point = (end_x, end_y)
    points.append(end_point)

    # 計算每段長度
    seg_lens = [np.hypot(points[i+1][0]-points[i][0], points[i+1][1]-points[i][1]) for i in range(len(points)-1)]
    # 扣掉轉角補償
    seg_lens = [seg_lens[0] + (-1 + np.pi/2) * r] + [s + (-2 + np.pi/2) * r for s in seg_lens[1:-1]]+ [seg_lens[-1] - r]

    if s == 0:
        return points[0], -1

    total = 0
    for i, seg_len in enumerate(seg_lens):
        if total + seg_len >= s:
            # 在這一段內
            remain = s - total + r
            x0, y0 = points[i]
            x1, y1 = points[i+1]
            raw_len = np.hypot(x1 - x0, y1 - y0)
            ratio = remain / seg_len if seg_len != 0 else 0
            x = x0 + (x1 - x0) * ratio
            y = y0 + (y1 - y0) * ratio
            # 決定標記
            if i == 0:
                tag = -1
            elif i == len(seg_lens) - 1:
                tag = 5
            elif np.isclose(raw_len, a+c):
                tag =4 #向右L型
            elif np.isclose(raw_len, a+2*c) or np.isclose(raw_len, a):
                tag =2 #向左L型
            else:
                print(f"Warning: raw_len={raw_len} does not match expected values (a={a}, c={c}). Using default tag=2.")
                tag = 2
            return (x, y), tag

        total += seg_len
        
        
def is_correct_branches(M, p, a, b, c, d, l0, r):
    # 0=alpha, 1=beta, 2=gamma, 3=delta, 4=epsilon, 5=lambda,
    # 6=zeta, 7=mu, 8=eta, 9=theta_, 10=theta|
    n = M.shape[0]
    corner_fix = 2 * r - np.pi * r / 2
    
    # 修正 1: 補上 2*c 與 2*d 的乘號
    W = np.array([a/2, 5*b + 2*c + 2*d, a, 5*b + 2*c + 2*d, a, b, b, b, a, b, a/2])
    K = np.array([0, 6, 0, 6, 1, 1, 0, 1, 2, 1, 0])
    l = M * (W - corner_fix * K)
    
    H_result = []
    used_deletions = set()  # 記錄已被使用的刪除位置，避免兩個 pt 重複刪同一個結構

    for pt in p:
        total = l0 - corner_fix
        if pt <= total:
            return False  # 分岔點落在 l0 上，不合法
            
        found = False
        for k in range(n):
            for j in range(11):
                if l[k][j] == 0:
                    continue  # 已被刪除的結構長度為 0，直接跳過
                    
                total += l[k][j]
                if pt < total:
                    found = True
                    # 修正 3: 必須落在允許分岔的 5 個鉛直段上
                    if j not in (0, 2, 4, 8, 10):
                        return False
                    
                    # 修正 4: 檢查各操作的邊界條件與對應結構是否已刪除
                    if j == 0:  # m1(k+1)
                        if M[k][5] == 0 or ("lambda", k) in used_deletions:
                            return False
                        used_deletions.add(("lambda", k))
                        H_result.append(f"m1({k+1})")
                        
                    elif j == 2:  # m2(k+1)，需滿足 k >= 1 (1-based >= 2)
                        if k == 0 or M[k-1][7] == 0 or ("mu", k-1) in used_deletions:
                            return False
                        used_deletions.add(("mu", k-1))
                        H_result.append(f"m2({k+1})")
                        
                    elif j == 4:  # m3(k+1)，需滿足 k <= n-2 (1-based <= n-1)
                        if k == n - 1 or M[k][7] == 0 or ("mu", k) in used_deletions:
                            return False
                        used_deletions.add(("mu", k))
                        H_result.append(f"m3({k+1})")
                        
                    elif j == 8:  # m4(k+1)
                        if M[k][5] == 0 or ("lambda", k) in used_deletions:
                            return False
                        used_deletions.add(("lambda", k))
                        H_result.append(f"m4({k+1})")
                        
                    elif j == 10:  # m5(k+1)，需滿足 k <= n-2 (1-based <= n-1)
                        if k == n - 1 or M[k+1][5] == 0 or ("lambda", k+1) in used_deletions:
                            return False
                        used_deletions.add(("lambda", k+1))
                        H_result.append(f"m5({k+1})")
                        
                    break  # 跳出 j 迴圈
            if found:
                break  # 修正 2: 跳出 k 迴圈
                
        if not found:
            return False  # pt 超過全部週期的總長

    # 修正 5: 確認矩陣 M 裡面實際啟用的捷徑數量 (lambda + mu) 剛好等於 p 的數量
    total_shortcuts_in_M = np.sum(M[:, 5]) + np.sum(M[:, 7])
    if total_shortcuts_in_M != len(p):
        return False

    print("合法分岔！對應操作序列 H_result =", H_result)
    return True


def is_correct_length(M, a, b, c, d, l0, ln_1, r):
    n = M.shape[0]
    corner_fix = 2 * r - np.pi * r / 2
    W = np.array([a/2, 5*b + 2*c + 2*d, a, 5*b + 2*c + 2*d, a, b, b, b, a, b, a/2])
    K = np.array([0, 6, 0, 6, 1, 1, 0, 1, 2, 1, 0])
    
    L = l0 + ln_1 - 2 * corner_fix + np.sum(M * (W - corner_fix * K))
    S = l0 + ln_1 + 4 * b * n
    return L, S
    

def build_M(n, ops):
    """
    根據週期數 n 與操作序列 ops (例如 [('m1', 1), ('m3', 2)]) 建立 n x 11 狀態矩陣 M。
    回傳: (是否合法, 矩陣 M, 每個操作對應的鉛直線格位清單 target_cells)
    """
    # 0=alpha, 1=beta, 2=gamma, 3=delta, 4=epsilon, 5=lambda,
    # 6=zeta, 7=mu, 8=eta, 9=theta_, 10=theta|
    M = np.ones((n, 11), dtype=int)
    M[:, 5] = 0  # lambda 初始為 0
    M[:, 7] = 0  # mu 初始為 0
    target_cells = []

    for op_name, k_1based in ops:
        k = k_1based - 1  # 轉為 0-based 索引

        if op_name == "m1":
            if not (0 <= k < n) or M[k, 2] == 0:
                return False, None, None
            M[k, [2, 3, 4]] = 0
            M[k, 5] = 1
            target_cells.append((k, 0))

        elif op_name == "m2":
            if not (1 <= k < n) or M[k-1, 8] == 0:
                return False, None, None
            M[k-1, [8, 9, 10]] = 0
            M[k, 0] = 0
            M[k-1, 7] = 1
            target_cells.append((k, 2))

        elif op_name == "m3":
            if not (0 <= k < n - 1) or M[k, 8] == 0:
                return False, None, None
            M[k, [8, 9, 10]] = 0
            M[k+1, 0] = 0
            M[k, 7] = 1
            target_cells.append((k, 4))

        elif op_name == "m4":
            if not (0 <= k < n) or M[k, 2] == 0:
                return False, None, None
            M[k, [2, 3, 4]] = 0
            M[k, 5] = 1
            target_cells.append((k, 8))

        elif op_name == "m5":
            if not (0 <= k < n - 1) or M[k+1, 2] == 0:
                return False, None, None
            M[k+1, [2, 3, 4]] = 0
            M[k+1, 5] = 1
            target_cells.append((k, 10))
        else:
            return False, None, None

    # 檢查每個分岔點所在的鉛直線本身是否仍保留 (未被其他操作刪除)
    for tk, tj in target_cells:
        if M[tk, tj] == 0:
            return False, None, None

    return True, M, target_cells


def generate_valid_ops(n, T, p=None):
    """
    產生所有長度為 T 且沿著路徑順序遞增的候選操作序列
    使用 itertools.combinations 來極大化效能並避免記憶體爆炸
    """
    candidates = []
    for k in range(1, n + 1):
        candidates.append(("m1", k))
        if k >= 2:
            candidates.append(("m2", k))
        if k <= n - 1:
            candidates.append(("m3", k))
        candidates.append(("m4", k))
        if k <= n - 1:
            candidates.append(("m5", k))

    # 動態範圍過濾 (如果傳入 p)
    if p is not None:
        # 大略估計每個分岔點可能的 period 範圍
        min_k = [max(1, int((pi - 8.0) / 10.0)) for pi in p]
        max_k = [int((pi + 8.0) / 2.7) for pi in p]
    else:
        min_k = [1] * T
        max_k = [n] * T

    import itertools
    for ops in itertools.combinations(candidates, T):
        valid_range = True
        for i in range(T):
            op_k = ops[i][1]
            if op_k < min_k[i] or op_k > max_k[i]:
                valid_range = False
                break
        if not valid_range:
            continue
            
        valid, M, target_cells = build_M(n, ops)
        if valid:
            yield (list(ops), M, target_cells)


# =====================================================================
# 第三部分：線性規劃 (LP) 參數最佳化器 (最大化 b)
# =====================================================================

def optimize_params_for_M(M, target_cells, p, L_target, S_target, r):
    """
    固定狀態矩陣 M 後，利用線性規劃求解最大化 b 的連續參數 x = [a, b, c, d, l0, ln_1]
    """
    n = M.shape[0]
    cf = 2 * r - np.pi * r / 2
    K = np.array([0, 6, 0, 6, 1, 1, 0, 1, 2, 1, 0])

    # 11 個欄位對 [a, b, c, d, l0, ln_1] 的線性係數矩陣
    W_coef = np.array([
        [0.5, 0, 0, 0, 0, 0],  # 0: alpha  = a/2
        [0,   5, 2, 2, 0, 0],  # 1: beta   = 5b + 2c + 2d
        [1.0, 0, 0, 0, 0, 0],  # 2: gamma  = a
        [0,   5, 2, 2, 0, 0],  # 3: delta  = 5b + 2c + 2d
        [1.0, 0, 0, 0, 0, 0],  # 4: epsilon= a
        [0,   1, 0, 0, 0, 0],  # 5: lambda = b
        [0,   1, 0, 0, 0, 0],  # 6: zeta     = b
        [0,   1, 0, 0, 0, 0],  # 7: mu     = b
        [1.0, 0, 0, 0, 0, 0],  # 8: eta    = a
        [0,   1, 0, 0, 0, 0],  # 9: theta_ = b
        [0.5, 0, 0, 0, 0, 0],  # 10:theta| = a/2
    ], dtype=float)

    # 目標：最大化 b (在 linprog 中為最小化 -b)
    c_obj = np.array([0.0, -1.0, 0.0, 0.0, 0.0, 0.0])

    # 1. 等式約束：總路徑長 L 與水平指標 S
    L_coef = np.sum(M[:, :, None] * W_coef[None, :, :], axis=(0, 1))
    L_coef[4] += 1.0  # + l0
    L_coef[5] += 1.0  # + ln_1
    L_const = -2 * cf - np.sum(M * (cf * K))

    S_coef = np.array([0.0, 4.0 * n, 0.0, 0.0, 1.0, 1.0])

    A_eq = np.vstack([L_coef, S_coef])
    b_eq = np.array([L_target - L_const, S_target])

    # 2. 不等式約束
    A_ub = []
    b_ub = []
    eps = 1e-5  # 微小安全邊距，確保嚴格滿足 < 號

    # 加入你指定的幾何高度限制：a/2 + c + d < 0.9
    A_ub.append([0.5, 0.0, 1.0, 1.0, 0.0, 0.0])
    b_ub.append(0.9 - eps)

    # 加入每個分岔點 pt 落在目標鉛直線格位 (tk, tj) 內的區間限制
    branch_margin = 0.2  # 確保岔出點離轉角至少 0.2 mm
    for pt, (tk, tj) in zip(p, target_cells):
        coef_start = np.array([0.0, 0.0, 0.0, 0.0, 1.0, 0.0])  # 起點含 l0
        const_start = -cf

        for k in range(n):
            for j in range(11):
                if k == tk and j == tj:
                    break
                if M[k, j] == 1:
                    coef_start += W_coef[j]
                    const_start -= cf * K[j]
            if k == tk:
                break

        coef_end = coef_start + W_coef[tj]
        const_end = const_start - cf * K[tj]

        # 條件 A: S_start + branch_margin <= pt
        A_ub.append(coef_start)
        b_ub.append(pt - const_start - branch_margin)

        # 條件 B: S_end - branch_margin >= pt  (即 -S_end <= -pt - branch_margin)
        A_ub.append(-coef_end)
        b_ub.append(-(pt - const_end + branch_margin))

    # 3. 參數下界限制 (規格書第 10 節，並確保扣掉圓弧後每段長度皆 > 0)
    bounds = [
        (max(1e-3, 2 * cf + eps), None),  # a > 0 (且需大於 eta 的 2 個圓弧修正)
        (max(0.1, cf + eps), None),       # b >= 0.1
        (0.1, None),                      # c >= 0.1
        (0.3, None),                      # d >= 0.3
        (max(0.2, cf + eps), None),       # l0 >= 0.2
        (max(0.2, cf + eps), None)        # ln_1 >= 0.2
    ]

    res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if res.success:
        return True, res.x
    return False, None


# =====================================================================
# 第四部分：主搜尋程序與規格書第 13 節標準輸出
# =====================================================================

def matrix_to_ten_arrays(M):
    """將 n x 11 矩陣還原為規格書定義的 10 個希臘字母狀態陣列"""
    return {
        "alpha":   M[:, 0].tolist(),
        "beta":    M[:, 1].tolist(),
        "gamma":   M[:, 2].tolist(),
        "delta":   M[:, 3].tolist(),
        "epsilon": M[:, 4].tolist(),
        "zeta":    M[:, 6].tolist(),
        "eta":     M[:, 8].tolist(),
        "theta":   M[:, 9].tolist(),  # theta_ 與 theta| 狀態永遠同步
        "lambda":  M[:, 5].tolist(),
        "mu":      M[:, 7].tolist(),
    }


def solve_circuit(p, L_target, S_target, r, n_min=None, n_max=8):
    """
    自動搜尋正整數 n 與所有合法操作序列，找出最大化 b 的全局最佳解
    """
    p = list(p)
    T = len(p)
    if n_min is None:
        n_min = max(1, (T + 1) // 2)

    # =========================================================
    # 效能優化 1：提早篩選不可能的 n_max，避免無謂的大量運算
    # =========================================================
    cf = 2 * r - np.pi * r / 2
    eps = 1e-5
    a_min = max(1e-3, 2 * cf + eps)
    b_min = max(0.1, cf + eps)
    c_min = 0.1
    d_min = 0.3
    l0_min = max(0.2, cf + eps)
    ln1_min = max(0.2, cf + eps)

    dynamic_n_max_S = int((S_target - l0_min - ln1_min) / (4 * b_min))
    min_period_len = 4*a_min + 12*b_min + 4*c_min + 4*d_min
    dynamic_n_max_L = int((L_target - l0_min - ln1_min + 2*cf) / min_period_len)
    
    n_max = min(n_max, dynamic_n_max_S, dynamic_n_max_L)
    print(f"動態計算的 n_max 上限為: {n_max}")

    # =========================================================
    # 效能優化 2：預先計算最小可能長度，供加速篩選 (Pruning)
    # =========================================================
    W_min = np.array([
        a_min / 2, 5 * b_min + 2 * c_min + 2 * d_min, a_min, 5 * b_min + 2 * c_min + 2 * d_min, a_min,
        b_min, b_min, b_min, a_min, b_min, a_min / 2
    ])
    K = np.array([0, 6, 0, 6, 1, 1, 0, 1, 2, 1, 0])
    eff_W_min = W_min - cf * K

    best_b = -1.0
    best_sol = None

    for n in range(n_min, n_max + 1):
        valid_candidates = generate_valid_ops(n, T, p)
        for ops, M, target_cells in valid_candidates:
            
            # --- 快速過濾 (Pruning)：如果最小長度條件都無法滿足，就跳過耗時的 LP ---
            possible = True
            for pt, (tk, tj) in zip(p, target_cells):
                # 預估從起點到 (tk, tj) 的最小可能長度
                start_len = l0_min - cf
                for k in range(n):
                    for j in range(11):
                        if k == tk and j == tj:
                            break
                        if M[k, j] == 1:
                            start_len += eff_W_min[j]
                    if k == tk:
                        break
                
                if start_len > pt:
                    possible = False
                    break
                
                # 預估從 (tk, tj) 到終點的最小可能長度
                after_len = ln1_min - cf
                for k in range(tk, n):
                    start_j = tj + 1 if k == tk else 0
                    for j in range(start_j, 11):
                        if M[k, j] == 1:
                            after_len += eff_W_min[j]
                            
                if pt + after_len > L_target:
                    possible = False
                    break

            if not possible:
                continue
            # -------------------------------------------------------------------

            ok, params = optimize_params_for_M(M, target_cells, p, L_target, S_target, r)
            if not ok:
                continue

            a, b, c, d, l0, ln_1 = params
            if b > best_b:
                # 雙重確認：丟回兩個驗證函式進行最終核對
                if is_correct_branches(M, p, a, b, c, d, l0, r):
                    L_out, S_out = is_correct_length(M, a, b, c, d, l0, ln_1, r)
                    if np.isclose(L_out, L_target, atol=1e-4) and np.isclose(S_out, S_target, atol=1e-4):
                        best_b = b
                        H_req = [f"{op}({k})" for op, k in ops]
                        best_sol = {
                            "n": n,
                            "b": b,
                            "params": {"a": a, "b": b, "c": c, "d": d, "l0": l0, "ln_1": ln_1},
                            "H_require": H_req,
                            "H_result": list(H_req),
                            "M": M,
                            "ten_arrays": matrix_to_ten_arrays(M),
                            "L_out": L_out,
                            "S_out": S_out
                        }
                        
                        # 每當找到更優解時，即時寫入 best_solution.json，並印出提示
                        import json
                        try:
                            serializable_sol = {
                                "n": int(n),
                                "b": float(b),
                                "params": {k: float(v) for k, v in best_sol["params"].items()},
                                "H_require": best_sol["H_require"],
                                "H_result": best_sol["H_result"],
                                "M": best_sol["M"].tolist() if isinstance(best_sol["M"], np.ndarray) else best_sol["M"],
                                "ten_arrays": {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in best_sol["ten_arrays"].items()},
                                "L_out": float(L_out),
                                "S_out": float(S_out)
                            }
                            with open("best_solution.json", "w", encoding="utf-8") as f:
                                json.dump(serializable_sol, f, indent=4, ensure_ascii=False)
                            print(f"\n[系統提示] 已找到目前最優解 (b={b:.6f})，並暫存至 best_solution.json！")
                            print(f"合法分岔！對應操作序列 H_result = {H_req}\n")
                        except Exception as e:
                            print(f"無法暫存 JSON: {e}")

    return best_sol


def print_solution(sol, p, r):
    """依照規格書第 13 節格式印出完整最佳解"""
    if sol is None:
        print("❌ 在指定的 n_max 範圍內找不到滿足所有限制的可行解。請檢查輸入的 P, L, S 是否合理，或調大 n_max。")
        return

    prm = sol["params"]
    print("=" * 60)
    print("✅ 找到最佳可行解！(Maximize b)")
    print("=" * 60)
    print(f"• 最佳的 b       : {prm['b']:.6f}")
    print(f"• 對應參數       : a = {prm['a']:.6f}, c = {prm['c']:.6f}, d = {prm['d']:.6f}, "
          f"l_0 = {prm['l0']:.6f}, l_{{n+1}} = {prm['ln_1']:.6f}")
    print(f"• 高度條件檢查   : a/2 + c + d = {prm['a']/2 + prm['c'] + prm['d']:.6f} (< 0.9)")
    print(f"• 正整數 n       : {sol['n']}")
    print(f"• 操作序列 H_req : {sol['H_require']}")
    print(f"• f 輸出 H_result: {sol['H_result']}")
    print(f"• g 輸出 (L, S)  : L = {sol['L_out']:.6f}, S = {sol['S_out']:.6f}")
    print("-" * 60)
    print("• 完成全部操作後的十個狀態陣列：")
    for name, arr in sol["ten_arrays"].items():
        print(f"  {name:8s} = {arr}")
    print("-" * 60)
    print("• 分岔點落點明細驗證：")
    is_correct_branches(sol["M"], p, prm["a"], prm["b"], prm["c"], prm["d"], prm["l0"], r)
    print("=" * 60)

def generate_meander_points(start_x, start_y, n, alpha, beta, gamma, delta, epsilon, lamb, zeta, mu, eta, theta, a, b, c, d, l0):
    # 0=alpha, 1=beta, 2=gamma, 3=delta, 4=epsilon, 5=lambda,
    # 6=zeta, 7=mu, 8=eta, 9=theta_, 10=theta|
    from collections import OrderedDict
    folded_path = OrderedDict()
    current_x, current_y = start_x, start_y
    current_x += l0
    folded_path[0] = (current_x, current_y)
    path_index = 1
    for k in range(n):
        if alpha[k] == 1:
            current_y += a / 2.0  # W[0] = a/2
            
        if beta[k] == 1:          # 修正: beta -> beta[k]
            current_y += c
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            current_x += -b
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            current_y += d
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            current_x += 3*b
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            current_y += -d
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            current_x += -b
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            current_y += -c
            
            # lamb 取代 gamma, delta, epsilon
            if lamb[k] == 1:
                folded_path[path_index] = (current_x, current_y)
                path_index += 1
                current_x += b
                
        if gamma[k] == 1:
            current_y += -a
            
        if delta[k] == 1:
            current_y += -c
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            current_x += -b
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            current_y += -d
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            current_x += 3*b
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            current_y += d
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            current_x += -b
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            current_y += c
            
        if epsilon[k] == 1:
            current_y += a        # 修正: 2*a -> a
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            
        if zeta[k] == 1:
            current_x += b
            
        if mu[k] == 1:
            current_x += b
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            
        if eta[k] == 1:
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            current_y += -a       # 修正: -2*a -> -a
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            
        if theta[k] == 1:
            current_x += b
            folded_path[path_index] = (current_x, current_y)
            path_index += 1
            current_y += a / 2.0  # 修正: a -> a/2
            
        folded_path[path_index] = (current_x, current_y)
        
    return folded_path



