#!/usr/bin/env python3
"""九子棋 (Nine Men's Morris) —— 纯标准库实现.

规则:
  1. 摆子阶段: 双方轮流在 24 个空点上各摆 9 枚棋子.
  2. 走子阶段: 沿线走到相邻空点; 只剩 3 枚时可以"飞"(走到任意空点).
  3. 成"磨"(三子连线)即可吃掉对方一枚棋子(优先吃不在磨中的子;
     对方所有子都在磨中时才能吃磨中子).
  4. 对方只剩 2 枚,或走子阶段无棋可走,即判负.
"""

import argparse
import random
import sys

# 24 个点,编号 0-23. 三个同心方框 + 十字连线.
# 布局(行):
#   0 -------- 1 -------- 2
#   |          |          |
#   |  3 ----- 4 ----- 5  |
#   |  |       |       |  |
#   |  |  6 -- 7 -- 8  |  |
#   |  |  |         |  |  |
#   9 10 11       12 13 14
#   |  |  |         |  |  |
#   |  | 15 - 16 - 17 |  |
#   |  |       |       |  |
#   | 18 ---- 19 ---- 20  |
#   |          |          |
#  21 ------- 22 ------- 23

MILLS = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (9, 10, 11), (12, 13, 14),
    (15, 16, 17), (18, 19, 20), (21, 22, 23),
    (0, 9, 21), (3, 10, 18), (6, 11, 15),
    (1, 4, 7), (16, 19, 22),
    (8, 12, 17), (5, 13, 20), (2, 14, 23),
]

ADJ = {
    0: (1, 9), 1: (0, 2, 4), 2: (1, 14),
    3: (4, 10), 4: (1, 3, 5, 7), 5: (4, 13),
    6: (7, 11), 7: (4, 6, 8), 8: (7, 12),
    9: (0, 10, 21), 10: (3, 9, 11, 18), 11: (6, 10, 15),
    12: (8, 13, 17), 13: (5, 12, 14, 20), 14: (2, 13, 23),
    15: (11, 16), 16: (15, 17, 19), 17: (12, 16),
    18: (10, 19), 19: (16, 18, 20, 22), 20: (13, 19),
    21: (9, 22), 22: (19, 21, 23), 23: (14, 22),
}

assert set(ADJ) == set(range(24))
for p, qs in ADJ.items():  # 邻接必须对称
    for q in qs:
        assert p in ADJ[q], f"asymmetric adjacency {p}-{q}"

PIECES = 9
MAX_MOVES = 400  # 走子阶段上限,防 AI 对局无限循环


class Morris:
    def __init__(self):
        self.board = [None] * 24
        self.placed = [0, 0]
        self.to_move = 0

    # ---------- 基础 ----------
    def count(self, player):
        return sum(1 for x in self.board if x == player)

    def in_mill(self, point, player=None):
        """point 上的棋子是否在磨中."""
        player = self.board[point] if player is None else player
        if player is None:
            return False
        return any(
            point in m and all(self.board[q] == player for q in m)
            for m in MILLS
        )

    def closes_mill(self, point, player):
        """假设在 point 放上 player 的子,是否成磨(调用前 point 必须为空)."""
        assert self.board[point] is None
        self.board[point] = player
        ok = self.in_mill(point, player)
        self.board[point] = None
        return ok

    def placement_phase(self):
        return self.placed[0] < PIECES or self.placed[1] < PIECES

    def flying(self, player):
        return self.count(player) == 3

    # ---------- 走法 ----------
    def legal_placements(self):
        return [p for p in range(24) if self.board[p] is None]

    def place(self, player, point):
        if player != self.to_move:
            raise ValueError("还没轮到你")
        if not self.placement_phase():
            raise ValueError("摆子阶段已结束")
        if not (0 <= point < 24):
            raise ValueError(f"点位越界: {point}")
        if self.board[point] is not None:
            raise ValueError(f"点位已被占: {point}")
        mill = self.closes_mill(point, player)
        self.board[point] = player
        self.placed[player] += 1
        self.to_move = 1 - player
        return mill

    def removable(self, player):
        """player 成磨后可吃掉的对方棋子点位."""
        foe = 1 - player
        pts = [p for p in range(24) if self.board[p] == foe]
        free = [p for p in pts if not self.in_mill(p, foe)]
        return free or pts  # 对方全在磨中时才能吃磨中子

    def remove(self, player, point):
        foe = 1 - player
        if self.board[point] != foe:
            raise ValueError(f"该点不是对方棋子: {point}")
        if point not in self.removable(player):
            raise ValueError(f"该子在磨中且对方还有磨外子,不能吃: {point}")
        self.board[point] = None

    def legal_moves(self, player):
        moves = []
        if self.flying(player):
            empties = [p for p in range(24) if self.board[p] is None]
            for s in range(24):
                if self.board[s] == player:
                    for d in empties:
                        moves.append((s, d))
        else:
            for s in range(24):
                if self.board[s] == player:
                    for d in ADJ[s]:
                        if self.board[d] is None:
                            moves.append((s, d))
        return moves

    def move(self, player, src, dst):
        if player != self.to_move:
            raise ValueError("还没轮到你")
        if self.placement_phase():
            raise ValueError("还在摆子阶段")
        if self.board[src] != player:
            raise ValueError(f"起点不是你的棋子: {src}")
        if not (0 <= dst < 24) or self.board[dst] is not None:
            raise ValueError(f"终点非法: {dst}")
        if not self.flying(player) and dst not in ADJ[src]:
            raise ValueError(f"只能走到相邻空点: {src}->{dst}")
        self.board[src] = None
        mill = self.closes_mill(dst, player)
        self.board[dst] = player
        self.to_move = 1 - player
        return mill

    def winner(self):
        """返回胜者 0/1,无胜者返回 None."""
        if self.placement_phase():
            return None
        for p in (0, 1):
            foe = 1 - p
            if self.count(foe) < 3:
                return p
            if not self.flying(foe) and not self.legal_moves(foe):
                return p
        return None

    # ---------- 显示 ----------
    def render(self):
        b = ["·" if x is None else ("●" if x == 0 else "○") for x in self.board]
        L = []
        L.append(f"{b[0]:>2}-----------{b[1]:>2}-----------{b[2]:>2}")
        L.append(" |            |            |")
        L.append(f" |   {b[3]:>2}------{b[4]:>2}------{b[5]:>2}   |")
        L.append(" |    |       |       |    |")
        L.append(f" |    |  {b[6]:>2}--{b[7]:>2}--{b[8]:>2}  |    |")
        L.append(" |    |  |         |  |    |")
        L.append(f"{b[9]:>2}  {b[10]:>2} {b[11]:>2}       {b[12]:>2} {b[13]:>2}  {b[14]:>2}")
        L.append(" |    |  |         |  |    |")
        L.append(f" |    | {b[15]:>2}-{b[16]:>2}-{b[17]:>2}  |    |")
        L.append(" |    |       |       |    |")
        L.append(f" |   {b[18]:>2}-----{b[19]:>2}-----{b[20]:>2}   |")
        L.append(" |            |            |")
        L.append(f"{b[21]:>2}----------{b[22]:>2}----------{b[23]:>2}")
        L.append("点位编号 0-23, ●=先手 ○=后手")
        return "\n".join(L)


# ---------- AI ----------
def ai_place(g, player, rng):
    """贪心摆子: 成磨 > 堵对方成磨 > 随机."""
    foe = 1 - player
    best, best_score = None, -1
    for p in g.legal_placements():
        score = rng.random()
        if g.closes_mill(p, player):
            score += 100
        elif g.closes_mill(p, foe):
            score += 60  # 堵
        if score > best_score:
            best, best_score = p, score
    return best


def ai_move(g, player, rng):
    """贪心走子: 成磨 > 堵 > 随机."""
    foe = 1 - player
    moves = g.legal_moves(player)
    best, best_score = None, -1
    for s, d in moves:
        g.board[s] = None
        mill_me = g.closes_mill(d, player)
        mill_foe = g.closes_mill(d, foe)
        g.board[s] = player
        score = rng.random() + (100 if mill_me else 0) + (60 if mill_foe else 0)
        if score > best_score:
            best, best_score = (s, d), score
    return best


def ai_remove(g, player, rng):
    """吃子: 优先吃最接近成磨的对方子."""
    foe = 1 - player
    cands = g.removable(player)
    def danger(p):
        return sum(
            1 for m in MILLS if p in m
            and sum(1 for q in m if g.board[q] == foe) == 2
            and all(g.board[q] in (foe, None) for q in m)
        )
    return max(cands, key=lambda p: (danger(p), rng.random()))


def auto_game(seed):
    rng = random.Random(seed)
    g = Morris()
    moves = 0
    while g.placement_phase():
        p = g.to_move
        if g.place(p, ai_place(g, p, rng)):
            g.remove(p, ai_remove(g, p, rng))
    while g.winner() is None and moves < MAX_MOVES:
        p = g.to_move
        mv = ai_move(g, p, rng)
        if mv is None:  # 无棋可走
            break
        if g.move(p, *mv):
            g.remove(p, ai_remove(g, p, rng))
        moves += 1
    w = g.winner()
    if w is None:  # 走子阶段无棋可走
        w = 1 - g.to_move if not g.legal_moves(g.to_move) else None
    return w, moves  # w 为 None 表示和棋(撞上限)


def play_interactive():
    g = Morris()
    print("九子棋!你是 ●(先手),AI 是 ○.摆子输入点位编号,走子输入 起点 终点,吃子输入点位.")
    print(g.render())
    while True:
        if g.placement_phase():
            s = input(f"[摆子 {g.placed[0]}/9 vs {g.placed[1]}/9] 你的点位> ").strip()
            try:
                mill = g.place(0, int(s))
            except (ValueError, IndexError) as e:
                print("非法:", e); continue
            if mill:
                r = input("成磨!吃掉对方哪个点位> ").strip()
                try:
                    g.remove(0, int(r))
                except (ValueError, IndexError) as e:
                    print("非法:", e); continue
            # AI
            p = ai_place(g, 1, random)
            if g.place(1, p):
                g.remove(1, ai_remove(g, 1, random))
            print(g.render())
        else:
            s = input("[走子] 起点 终点> ").strip().split()
            try:
                mill = g.move(0, int(s[0]), int(s[1]))
            except (ValueError, IndexError) as e:
                print("非法:", e); continue
            if mill:
                r = input("成磨!吃掉对方哪个点位> ").strip()
                try:
                    g.remove(0, int(r))
                except (ValueError, IndexError) as e:
                    print("非法:", e); continue
            w = g.winner()
            if w is not None:
                print(g.render()); print("你赢了!" if w == 0 else "AI 赢了!")
                return
            mv = ai_move(g, 1, random)
            if mv is None:
                print("AI 无棋可走,你赢了!"); return
            if g.move(1, *mv):
                g.remove(1, ai_remove(g, 1, random))
            print(g.render())
            w = g.winner()
            if w is not None:
                print("你赢了!" if w == 0 else "AI 赢了!")
                return


def main(argv=None):
    ap = argparse.ArgumentParser(description="九子棋 (Nine Men's Morris)")
    ap.add_argument("--auto", action="store_true", help="AI 对 AI 自动演示")
    ap.add_argument("--games", type=int, default=10, help="自动演示局数")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    if args.auto:
        w0 = w1 = dr = 0
        for i in range(args.games):
            w, mv = auto_game(args.seed + i)
            if w == 0: w0 += 1
            elif w == 1: w1 += 1
            else: dr += 1
            print(f"第 {i+1}/{args.games} 局: "
                  f"{'先手胜' if w == 0 else '后手胜' if w == 1 else '和棋'} (走子 {mv} 步)")
        print(f"总计: 先手胜 {w0}, 后手胜 {w1}, 和棋 {dr}")
    else:
        if not sys.stdin.isatty():
            print("交互模式需要终端;无头演示请用 --auto", file=sys.stderr)
            sys.exit(2)
        play_interactive()


if __name__ == "__main__":
    main()
