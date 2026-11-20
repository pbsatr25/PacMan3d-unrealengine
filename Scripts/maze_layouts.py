"""
Denah labirin untuk level 2 dan 3 (dipakai oleh setup_levels.py).

Ukuran grid 20 kolom x 10 baris, 1 sel = 200 unit, sehingga labirin
seluas 4000 x 2000 unit -- sama dengan LVL_PacMan (level 1), jadi
NavMeshBoundsVolume bawaan level 1 tetap pas.

Simbol:
  #  dinding
  .  jalan + pellet (BP_Food)
  o  jalan + power pellet (BP_PowerPellet)
  P  posisi awal Pac-Man (jalan, tanpa pellet)
  G  posisi hantu di kandang (tanpa pellet)
  _  jalan tanpa pellet (pintu kandang / bagian dalam kandang)

File ini murni Python (tanpa modul unreal) supaya bisa dicek di luar editor:
  python Scripts/maze_layouts.py
"""

LEVELS = {
    # Level 2 - "Medium": lebih banyak persimpangan pendek, kandang di tengah,
    # 4 power pellet di sudut.
    "LVL_PacMan_02": {
        "title": "Level 2 - Neon Green",
        "wall_color": (0.05, 1.0, 0.25),     # hijau neon
        "floor_color": (0.004, 0.012, 0.006),
        "ghost_speed": 480.0,
        "grid": [
            "####################",
            "#o.......##.......o#",
            "#.###.##.##.##.###.#",
            "#..................#",
            "#.##.#.##__##.#.##.#",
            "#.##.#.#____#.#.##.#",
            "#....#.#GGGG#.#....#",
            "#.##.#.######.#.##.#",
            "#o.......P........o#",
            "####################",
        ],
    },
    # Level 3 - "Hard": lebih banyak jalan buntu dan lorong sempit yang panjang,
    # hanya 2 jalur utama melewati sisi kiri/kanan, hantu lebih cepat.
    "LVL_PacMan_03": {
        "title": "Level 3 - Neon Red",
        "wall_color": (1.0, 0.03, 0.03),     # merah neon
        "floor_color": (0.012, 0.003, 0.003),
        "ghost_speed": 520.0,
        "grid": [
            "####################",
            "#o...#...#..#...#.o#",
            "#.#.##.#.##.#.##.#.#",
            "#.#................#",
            "#.#.##.##__##.##.#.#",
            "#...#..#____#..#...#",
            "###.#.##GGGG##.#.###",
            "#...#..######..#...#",
            "#o#.......P......#o#",
            "####################",
        ],
    },
}

CELL = 200.0
ORIGIN_X = -2000.0   # sisi kiri labirin level 1
ORIGIN_Y = -1000.0   # sisi atas labirin level 1
WALKABLE = set(".oPG_")


def cell_center(col, row):
    return (ORIGIN_X + (col + 0.5) * CELL, ORIGIN_Y + (row + 0.5) * CELL)


def wall_runs(grid):
    """Gabungkan sel dinding berurutan per baris -> (col_awal, row, panjang)."""
    runs = []
    for r, line in enumerate(grid):
        c = 0
        while c < len(line):
            if line[c] == "#":
                start = c
                while c < len(line) and line[c] == "#":
                    c += 1
                runs.append((start, r, c - start))
            else:
                c += 1
    return runs


def cells(grid, symbols):
    return [(c, r) for r, line in enumerate(grid) for c, ch in enumerate(line) if ch in symbols]


def validate(name, grid):
    errors = []
    rows, cols = len(grid), len(grid[0])
    if any(len(line) != cols for line in grid):
        errors.append("panjang baris tidak sama")
    if any(ch != "#" for ch in grid[0] + grid[-1]) or any(l[0] != "#" or l[-1] != "#" for l in grid):
        errors.append("tepi labirin harus dinding")
    if len(cells(grid, "P")) != 1:
        errors.append("harus ada tepat 1 'P'")

    # Semua jalan harus terhubung (tidak ada pellet yang tidak terjangkau)
    open_cells = set(cells(grid, WALKABLE))
    start = cells(grid, "P")[0] if cells(grid, "P") else next(iter(open_cells))
    seen, stack = {start}, [start]
    while stack:
        c, r = stack.pop()
        for nc, nr in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
            if (nc, nr) in open_cells and (nc, nr) not in seen:
                seen.add((nc, nr))
                stack.append((nc, nr))
    unreachable = open_cells - seen
    if unreachable:
        errors.append(f"sel tidak terjangkau: {sorted(unreachable)}")

    dead_ends = [
        (c, r) for (c, r) in open_cells
        if sum((n in open_cells) for n in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1))) == 1
    ]
    return {
        "name": name,
        "size": f"{cols}x{rows}",
        "pellets": len(cells(grid, ".")),
        "power": len(cells(grid, "o")),
        "ghost_spots": len(cells(grid, "G")),
        "wall_actors": len(wall_runs(grid)),
        "dead_ends": len(dead_ends),
        "errors": errors,
    }


if __name__ == "__main__":
    for name, cfg in LEVELS.items():
        print(validate(name, cfg["grid"]))
