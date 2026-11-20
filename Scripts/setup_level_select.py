"""
Menduplikat /Game/UI/Widgets/WBP_MainMenu menjadi WBP_LevelSelect
(latar, font dan gaya tombol ikut sama). Setelah itu ikuti panduan:
ganti nama/teks tombol di Designer, lalu tempel
Scripts/blueprint_paste/WBP_LevelSelect_Graph.txt ke Graph-nya.

Jalankan: Tools > Execute Python Script... > pilih file ini.
"""

import unreal

SRC = "/Game/UI/Widgets/WBP_MainMenu"
DST = "/Game/UI/Widgets/WBP_LevelSelect"
EAL = unreal.EditorAssetLibrary

if EAL.does_asset_exist(DST):
    unreal.log(f"[LevelSelect] {DST} sudah ada, tidak diduplikat lagi.")
elif EAL.duplicate_asset(SRC, DST) is None:
    raise RuntimeError(f"Gagal menduplikat {SRC}")
else:
    EAL.save_asset(DST, only_if_is_dirty=False)
    unreal.log(f"[LevelSelect] {DST} dibuat dari WBP_MainMenu.")
