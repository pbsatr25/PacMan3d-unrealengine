"""
Persiapan sistem skin Pac-Man (Classic / Black Monster / Lil Evil).

Yang dikerjakan:
  1. Ganti nama animasi Lil Evil: SK_LilEvil_Anim -> A_LilEvil_Walk.
  2. Buat /Game/ThirdPerson/Blueprints/BP_PacManGameInstance (parent: GameInstance)
     dengan variabel Integer 'SelectedSkin' (0 = Classic, 1 = Black Monster, 2 = Lil Evil).
     Game Instance tetap hidup saat pindah level, jadi pilihan skin ikut terbawa.
  3. Jadikan BP_PacManGameInstance sebagai Game Instance Class proyek
     (Project Settings > Maps & Modes; juga ditulis ke Config/DefaultEngine.ini).
  4. Tambah variabel Boolean 'UsingSkinAnim' di BP_ThirdPersonCharacter.
  5. Duplikat WBP_LevelSelect menjadi /Game/UI/Widgets/WBP_Customize.

Node Blueprint-nya ditempel dari Scripts/blueprint_paste/*.txt (lihat panduan).
Jalankan: Tools > Execute Python Script... > pilih file ini. Aman dijalankan ulang.
"""

import os
import stat

import unreal

EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
log = unreal.log

GI_PATH = "/Game/ThirdPerson/Blueprints/BP_PacManGameInstance"
CHAR_PATH = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
LEVEL_SELECT = "/Game/UI/Widgets/WBP_LevelSelect"
CUSTOMIZE = "/Game/UI/Widgets/WBP_Customize"
LILEVIL_ANIM_OLD = "/Game/PacMan/Skins/LilEvil/SK_LilEvil_Anim"
LILEVIL_ANIM_NEW = "/Game/PacMan/Skins/LilEvil/A_LilEvil_Walk"

PROJECT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())


def make_writable(asset_path):
    """File .uasset dari Git LFS 'lockable' bisa read-only; buka kuncinya sebelum disimpan."""
    rel = asset_path.replace("/Game/", "Content/", 1) + ".uasset"
    full = os.path.join(PROJECT, rel)
    if os.path.isfile(full) and not os.access(full, os.W_OK):
        os.chmod(full, stat.S_IWRITE | stat.S_IREAD)
        log(f"[Skin] Atribut read-only dilepas: {rel}")


def save(asset_path):
    make_writable(asset_path)
    if not EAL.save_asset(asset_path, only_if_is_dirty=False):
        raise RuntimeError(f"Gagal menyimpan {asset_path}")


def add_var(bp, name, type_name, default):
    if BEL.add_member_variable(bp, name, BEL.get_basic_type_by_name(type_name)):
        log(f"[Skin] Variabel {name} ditambahkan ke {bp.get_name()}.")
    BEL.compile_blueprint(bp)
    unreal.get_default_object(bp.generated_class()).set_editor_property(name, default)


def main():
    # 1. nama animasi Lil Evil
    if EAL.does_asset_exist(LILEVIL_ANIM_OLD) and not EAL.does_asset_exist(LILEVIL_ANIM_NEW):
        EAL.rename_asset(LILEVIL_ANIM_OLD, LILEVIL_ANIM_NEW)
        save(LILEVIL_ANIM_NEW)
        log("[Skin] SK_LilEvil_Anim -> A_LilEvil_Walk")

    # 2. Game Instance
    if EAL.does_asset_exist(GI_PATH):
        gi = EAL.load_asset(GI_PATH)
    else:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", unreal.GameInstance)
        folder, name = GI_PATH.rsplit("/", 1)
        gi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Blueprint, factory)
        log(f"[Skin] {GI_PATH} dibuat.")
    add_var(gi, "SelectedSkin", "int", 0)
    save(GI_PATH)

    # 3. Game Instance Class proyek (berlaku langsung + tersimpan di DefaultEngine.ini)
    class_path = f"{GI_PATH}.{GI_PATH.rsplit('/', 1)[1]}_C"
    settings = unreal.get_default_object(unreal.GameMapsSettings)
    settings.set_editor_property("game_instance_class", unreal.SoftClassPath(class_path))
    ini = os.path.join(PROJECT, "Config", "DefaultEngine.ini")
    with open(ini, encoding="utf-8") as f:
        lines = f.read().splitlines()
    lines = [l for l in lines if not l.startswith("GameInstanceClass=")]
    i = lines.index("[/Script/EngineSettings.GameMapsSettings]")
    lines.insert(i + 1, f"GameInstanceClass={class_path}")
    with open(ini, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")
    log(f"[Skin] Game Instance Class = {class_path}")

    # 4. variabel di karakter
    char = EAL.load_asset(CHAR_PATH)
    add_var(char, "UsingSkinAnim", "bool", False)
    save(CHAR_PATH)

    # 5. WBP_Customize
    if not EAL.does_asset_exist(CUSTOMIZE):
        if EAL.duplicate_asset(LEVEL_SELECT, CUSTOMIZE) is None:
            raise RuntimeError(f"Gagal menduplikat {LEVEL_SELECT}")
        save(CUSTOMIZE)
        log(f"[Skin] {CUSTOMIZE} dibuat dari WBP_LevelSelect.")

    log("[Setup] Persiapan skin selesai. Lanjutkan dengan menempel node dari Scripts/blueprint_paste/.")


main()
