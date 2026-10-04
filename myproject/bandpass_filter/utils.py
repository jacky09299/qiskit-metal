import numpy as np
from collections import OrderedDict

def find_bc_solutions(L, delta, max_n=100):
    """
    在 n = 1,2,...,max_n 範圍內搜尋 (b, c) 解。
    條件：
      n = (L - delta) / (2c) 為正整數
      floor((L-b)/(2*(b+c))) == n  == (L-delta)/(2c)
    回傳值：一個 list，每項為 (n, c, b_min, b_max)，
      其中 b_min < b <= b_max。
    """
    solutions = []
    for n in range(1, max_n+1):
        # 計算 c
        c = (L - delta) / (2 * n)
        if c <= 0:
            continue

        # 計算 b 的不等式邊界
        b_min = ((n+1)*delta - L) / (n*(2*n+3))  # 下界 (strict)
        b_max = delta / (2*n+1)                  # 上界 (inclusive)

        # 判斷是否有可行 b
        if b_min < b_max and b_max>0.1:
            solutions.append((n, c, b_min, b_max))
            print(f"n={n}, c={c:.3f}, b_min={b_min:.3f}, b_max={b_max:.3f}")
    return solutions
    
    
    
def get_xy_on_folded_path(folded_path, s):
    """
    給定folded_path (OrderedDict, key為int, value為(x, y)) 和長度s (mm)，
    回傳走s後的(x, y)座標。
    若s超過總長度，則回傳最後一點。
    """
    import numpy as np
    # 取得所有點
    points = list(folded_path.values())
    # 添加初始點
    first_point = points[0]
    zero_point = (first_point[0] -0.248, first_point[1])
    points.insert(0, zero_point)

    last_point = points[-1]
    extra_point = (last_point[0] + 5, last_point[1])
    points.append(extra_point)

    # 計算每段長度
    seg_lens = [np.hypot(points[i+1][0]-points[i][0], points[i+1][1]-points[i][1]) for i in range(len(points)-1)]
    # 扣掉轉角補償
    a = cpw_width # 轉角半徑
    seg_lens = [seg_lens[0] + (-1 + np.pi/2) * a] + [s + (-2 + np.pi/2) * a for s in seg_lens[1:]]

    if s == 0:
        return points[0], -1

    total = 0
    for i, seg_len in enumerate(seg_lens):
        if total + seg_len >= s:
            # 在這一段內
            remain = s - total + a
            x0, y0 = points[i]
            x1, y1 = points[i+1]
            ratio = remain / seg_len if seg_len != 0 else 0
            x = x0 + (x1 - x0) * ratio
            y = y0 + (y1 - y0) * ratio
            # 決定標記
            if i == 0:
                tag = -1
            elif i == len(seg_lens) - 1:
                tag = 5
            else:
                tag = (i - 1) % 5
            return (x, y), tag

        total += seg_len
