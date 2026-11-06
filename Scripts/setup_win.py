"""
Setup otomatis bagian 7 (kondisi menang / You Win) untuk PacMan3D.

Yang dikerjakan script ini:
  - Tahap 1 : variabel Integer "PelletsRemaining" (default 0) di BP_ThirdPersonGameMode.
  - Tahap 4 : menduplikat /Game/UI/WBP_YouDied menjadi WBP_YouWin
              (teks, warna, dan animasi WinFlash tetap diubah manual).
  - Audit level LVL_PacMan: menghitung BP_Food & BP_PowerPellet dan
    memberi peringatan untuk pellet yang posisinya mencurigakan
    (tertanam di bawah lantai / jauh lebih rendah-tinggi dari pellet lain).
    Ini untuk mencegah masalah "You Win tidak muncul" yang disebut di video.

Yang TIDAK dikerjakan (node graph, lihat panduan):
  - BeginPlay hitung pellet, event PelletCollected, Branch, Create Widget,
    Set Game Paused, pemanggilan PelletCollected di pellet.

Jalankan: Tools > Execute Python Script... > pilih file ini.
Aman dijalankan ulang.
"""

import statistics
import unreal

GAME_MODE_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode"
YOU_DIED = "/Game/UI/WBP_YouDied"
YOU_WIN = "/Game/UI/WBP_YouWin"
PELLET_BPS = ["/Game/PelletPickUps/BP_Food", "/Game/PelletPickUps/BP_PowerPellet"]
LEVEL_PATH = "/Game/LVL_PacMan"
Z_TOLERANCE = 30.0   # selisih tinggi (cm) dari mayoritas pellet yang dianggap aneh

EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
log = unreal.log
warn = unreal.log_warning


def setup_pellets_remaining():
    bp = EAL.load_asset(GAME_MODE_BP)
    if BEL.add_member_variable(bp, "PelletsRemaining", BEL.get_basic_type_by_name("int")):
        log("[Win] Variabel PelletsRemaining ditambahkan.")
    else:
        log("[Win] Variabel PelletsRemaining sudah ada.")
    BEL.compile_blueprint(bp)
    EAL.save_loaded_asset(bp, only_if_is_dirty=False)


def setup_you_win_widget():
    if EAL.does_asset_exist(YOU_WIN):
        log(f"[Win] {YOU_WIN} sudah ada.")
        return
    if not EAL.does_asset_exist(YOU_DIED):
        warn(f"[Win] {YOU_DIED} tidak ada, WBP_YouWin tidak dibuat.")
        return
    EAL.duplicate_asset(YOU_DIED, YOU_WIN)
    EAL.save_asset(YOU_WIN, only_if_is_dirty=False)
    log(f"[Win] {YOU_WIN} dibuat dari WBP_YouDied.")


def audit_pellets():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les.load_level(LEVEL_PATH)
    actors = eas.get_all_level_actors()

    pellets = []
    for path in PELLET_BPS:
        if not EAL.does_asset_exist(path):
            log(f"[Audit] {path.split('/')[-1]} belum ada, dilewati.")
            continue
        cls = EAL.load_asset(path).generated_class()
        found = [a for a in actors if a.get_class() == cls]
        log(f"[Audit] {path.split('/')[-1]}: {len(found)} buah di level")
        pellets += found

    if not pellets:
        warn("[Audit] Tidak ada pellet di level!")
        return
    log(f"[Audit] TOTAL pellet (nilai awal PelletsRemaining) = {len(pellets)}")

    median_z = statistics.median(a.get_actor_location().z for a in pellets)
    odd = [a for a in pellets if abs(a.get_actor_location().z - median_z) > Z_TOLERANCE]
    for a in odd:
        loc = a.get_actor_location()
        warn(f"[Audit] Pellet mencurigakan: {a.get_actor_label()} di "
             f"({loc.x:.0f}, {loc.y:.0f}, {loc.z:.0f}); tinggi normal sekitar z={median_z:.0f}")
    if odd:
        eas.set_selected_level_actors(odd)
        warn(f"[Audit] {len(odd)} pellet mencurigakan sudah DIPILIH di Outliner. "
             "Periksa / pindahkan / hapus.")
    else:
        log("[Audit] Semua pellet berada di ketinggian yang wajar.")


def main():
    setup_pellets_remaining()
    setup_you_win_widget()
    audit_pellets()
    log("[Setup] Bagian 7 selesai. Lanjutkan node graph secara manual (lihat panduan).")


main()
