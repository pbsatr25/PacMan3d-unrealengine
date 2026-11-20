"""
Generator teks node Blueprint (salin-tempel) untuk kondisi menang + pindah level.

Menghasilkan di Scripts/blueprint_paste/:
  BP_ThirdPersonGameMode_Win.txt -> Event BeginPlay (hitung pellet) + Custom Event PelletCollected
                                    (kurangi sisa; kalau habis: YOU WIN -> tunggu -> level berikutnya)
  BP_Food_PelletCollected.txt    -> Get Game Mode -> Cast -> PelletCollected
                                    (sisipkan sebelum Destroy Actor di BP_Food dan BP_PowerPellet)

Urutan level: LVL_PacMan -> LVL_PacMan_02 -> LVL_PacMan_03 -> L_MainMenu.

Saat menang game TIDAK di-pause (Delay ikut berhenti kalau di-pause). Sebagai gantinya waktu
diperlambat (Global Time Dilation 0.0001): Pac-Man & hantu membeku, lalu Delay 0.0003 detik
game = 3 detik nyata. Level baru otomatis kembali ke kecepatan normal.

Jalankan: python Scripts/make_win_paste.py
"""

from make_level_select_paste import (CLS, GAMEPLAY_STATICS, Node, call, exec_pins,
                                     get_player_controller, link, open_level, write)
from make_skin_paste import branch, event, q

GM_TYPE = "/Script/Engine.BlueprintGeneratedClass'/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode.BP_ThirdPersonGameMode_C'"
GM_CAST_PIN = "AsBP Third Person Game Mode"
FOOD_CLASS = "/Game/PelletPickUps/BP_Food.BP_Food_C"
POWER_CLASS = "/Game/PelletPickUps/BP_PowerPellet.BP_PowerPellet_C"
YOU_WIN_CLASS = "/Game/UI/WBP_YouWin.WBP_YouWin_C"
KML = CLS.format("/Script/Engine.KismetMathLibrary")
KSL = CLS.format("/Script/Engine.KismetSystemLibrary")
KSTR = CLS.format("/Script/Engine.KismetStringLibrary")
KARR = CLS.format("/Script/Engine.KismetArrayLibrary")
ACTOR = q(CLS.format("/Script/Engine.Actor"))

NEXT_LEVEL = [  # (level sekarang, level berikutnya)
    ("LVL_PacMan", "/Game/LVL_PacMan_02.LVL_PacMan_02"),
    ("LVL_PacMan_02", "/Game/LVL_PacMan_03.LVL_PacMan_03"),
]
AFTER_LAST = "/Game/UI/L_MainMenu.L_MainMenu"
TIME_DILATION = 0.0001
WAIT_REAL_SECONDS = 3.0


def lib_self(node, lib, default):
    node.pin("self", "object", sub_obj=q(lib), extra=f'DefaultObject="{default}"', hidden=True)


def world_ctx(node):
    node.pin("WorldContextObject", "object", sub_obj=q(CLS.format("/Script/CoreUObject.Object")), hidden=True)


def math_int(member, b_value, x, y):
    n = call(KML, member, x, y, pure=True)
    lib_self(n, KML, "/Script/Engine.Default__KismetMathLibrary")
    a = n.pin("A", "int", extra='DefaultValue="0"')
    b = n.pin("B", "int", extra=f'DefaultValue="{b_value}"')
    ret_cat = "bool" if member.startswith(("Less", "Equal", "Greater")) else "int"
    ret = n.pin("ReturnValue", ret_cat, "out")
    return n, a, b, ret


def var_get(name, cat, x, y):
    n = Node("K2Node_VariableGet", x, y, [f'VariableReference=(MemberName="{name}",bSelfContext=True)'])
    return n, n.pin(name, cat, "out")


def var_set(name, cat, x, y):
    n = Node("K2Node_VariableSet", x, y, [f'VariableReference=(MemberName="{name}",bSelfContext=True)'])
    exe, then = exec_pins(n)
    val = n.pin(name, cat, extra='DefaultValue="0"')
    n.pin("Output_Get", cat, "out")
    return n, exe, then, val


def get_all_actors(cls_path, x, y):
    n = call(GAMEPLAY_STATICS, "GetAllActorsOfClass", x, y)
    exe, then = exec_pins(n)
    lib_self(n, GAMEPLAY_STATICS, "/Script/Engine.Default__GameplayStatics")
    world_ctx(n)
    n.pin("ActorClass", "class", sub_obj=ACTOR, extra=f'DefaultObject="{cls_path}"')
    out = n.pin("OutActors", "object", "out", sub_obj=ACTOR, extra="PinType.ContainerType=Array")
    return n, exe, then, out


def array_length(x, y):
    n = Node("K2Node_CallArrayFunction", x, y, [
        f'FunctionReference=(MemberParent="{KARR}",MemberName="Array_Length")', "bIsPureFunc=True"])
    lib_self(n, KARR, "/Script/Engine.Default__KismetArrayLibrary")
    arr = n.pin("TargetArray", "object", sub_obj=ACTOR, extra="PinType.ContainerType=Array")
    ret = n.pin("ReturnValue", "int", "out")
    return n, arr, ret


def create_you_win(x, y):
    create = Node("K2Node_CreateWidget", x, y, [])
    exe, then = exec_pins(create)
    create.pin("Class", "class", sub_obj=q(CLS.format("/Script/UMG.UserWidget")),
               extra=f'DefaultObject="{YOU_WIN_CLASS}"')
    owner = create.pin("OwningPlayer", "object", sub_obj=q(CLS.format("/Script/Engine.PlayerController")))
    ret = create.pin("ReturnValue", "object", "out", sub_obj=q(CLS.format("/Script/UMG.UserWidget")))
    pc, pc_ret = get_player_controller(x + 20, y + 180)
    link(pc_ret, owner)

    add = call(CLS.format("/Script/UMG.UserWidget"), "AddToViewport", x + 330, y)
    a_exe, a_then = exec_pins(add)
    a_self = add.pin("self", "object", sub_obj=q(CLS.format("/Script/UMG.UserWidget")))
    add.pin("ZOrder", "int", extra='DefaultValue="10"')
    link(then, a_exe)
    link(ret, a_self)
    return [create, pc, add], exe, a_then


def time_dilation(value, x, y):
    n = call(GAMEPLAY_STATICS, "SetGlobalTimeDilation", x, y)
    exe, then = exec_pins(n)
    lib_self(n, GAMEPLAY_STATICS, "/Script/Engine.Default__GameplayStatics")
    world_ctx(n)
    n.pin("TimeDilation", "real", subcat="float", extra=f'DefaultValue="{value}"')
    return n, exe, then


def delay(seconds, x, y):
    n = call(KSL, "Delay", x, y)
    exe, then = exec_pins(n)
    lib_self(n, KSL, "/Script/Engine.Default__KismetSystemLibrary")
    world_ctx(n)
    n.pin("Duration", "real", subcat="float", extra=f'DefaultValue="{seconds}"')
    n.pin("LatentInfo", "struct", sub_obj=q("/Script/CoreUObject.ScriptStruct'/Script/Engine.LatentActionInfo'"),
          hidden=True)
    return n, exe, then


def level_name(x, y):
    # Di UE 5.8 GetCurrentLevelName = BlueprintCallable (punya pin exec), BUKAN pure.
    n = call(GAMEPLAY_STATICS, "GetCurrentLevelName", x, y)
    exe, then = exec_pins(n)
    lib_self(n, GAMEPLAY_STATICS, "/Script/Engine.Default__GameplayStatics")
    world_ctx(n)
    n.pin("bRemovePrefixString", "bool", extra='DefaultValue="true"')
    return n, exe, then, n.pin("ReturnValue", "string", "out")


def str_equals(value, x, y):
    n = call(KSTR, "EqualEqual_StrStr", x, y, pure=True)
    lib_self(n, KSTR, "/Script/Engine.Default__KismetStringLibrary")
    a = n.pin("A", "string")
    n.pin("B", "string", extra=f'DefaultValue="{value}"')
    return n, a, n.pin("ReturnValue", "bool", "out")


# ---------------------------------------------------------------- BP_ThirdPersonGameMode
def game_mode_graph():
    Node.counter = {}
    nodes = []

    # Event BeginPlay: PelletsRemaining = jumlah BP_Food + jumlah BP_PowerPellet
    bp, bp_then = event("ReceiveBeginPlay", 0, 0)
    g1, g1_exe, g1_then, g1_out = get_all_actors(FOOD_CLASS, 250, 0)
    g2, g2_exe, g2_then, g2_out = get_all_actors(POWER_CLASS, 600, 0)
    l1, l1_arr, l1_ret = array_length(650, 200)
    l2, l2_arr, l2_ret = array_length(950, 200)
    add, add_a, add_b, add_ret = math_int("Add_IntInt", 0, 1150, 200)
    st, st_exe, _, st_val = var_set("PelletsRemaining", "int", 1350, 0)
    link(bp_then, g1_exe)
    link(g1_then, g2_exe)
    link(g2_then, st_exe)
    link(g1_out, l1_arr)
    link(g2_out, l2_arr)
    link(l1_ret, add_a)
    link(l2_ret, add_b)
    link(add_ret, st_val)
    nodes += [bp, g1, g2, l1, l2, add, st]

    # Custom Event PelletCollected
    y = 450
    ce = Node("K2Node_CustomEvent", 0, y, ['CustomFunctionName="PelletCollected"'])
    ce.pin("OutputDelegate", "delegate", "out")
    ce_then = ce.pin("then", "exec", "out")
    get_r, get_r_out = var_get("PelletsRemaining", "int", 0, y + 180)
    sub, sub_a, _, sub_ret = math_int("Subtract_IntInt", 1, 220, y + 180)
    st2, st2_exe, st2_then, st2_val = var_set("PelletsRemaining", "int", 450, y)
    st2_out = st2.pins[3]  # Output_Get
    le, le_a, _, le_ret = math_int("LessEqual_IntInt", 0, 700, y + 180)
    br, br_exe, br_cond, br_t, _ = branch(900, y)
    link(ce_then, st2_exe)
    link(get_r_out, sub_a)
    link(sub_ret, st2_val)
    link(st2_then, br_exe)
    link(st2_out, le_a)
    link(le_ret, br_cond)
    nodes += [ce, get_r, sub, st2, le, br]

    # Menang: YOU WIN -> bekukan waktu -> tunggu -> level berikutnya
    win_nodes, win_exe, win_then = create_you_win(1150, y)
    td, td_exe, td_then = time_dilation(TIME_DILATION, 1550, y)
    dl, dl_exe, dl_then = delay(round(WAIT_REAL_SECONDS * TIME_DILATION, 6), 1800, y)
    ln, ln_exe, ln_then, ln_out = level_name(2050, y)
    link(br_t, win_exe)
    link(win_then, td_exe)
    link(td_then, dl_exe)
    link(dl_then, ln_exe)
    nodes += win_nodes + [td, dl, ln]

    prev = ln_then
    x = 2350
    for current, nxt in NEXT_LEVEL:
        eq, eq_a, eq_ret = str_equals(current, x, y + 200)
        link(ln_out, eq_a)
        b, b_exe, b_cond, b_t, b_f = branch(x + 250, y)
        link(prev, b_exe)
        link(eq_ret, b_cond)
        ol, ol_exe = open_level(nxt, x + 500, y - 220)
        link(b_t, ol_exe)
        nodes += [eq, b, ol]
        prev = b_f
        x += 700
    last, last_exe = open_level(AFTER_LAST, x, y)
    link(prev, last_exe)
    nodes.append(last)
    write("BP_ThirdPersonGameMode_Win.txt", nodes)


# ---------------------------------------------------------------- BP_Food / BP_PowerPellet
def pellet_graph():
    Node.counter = {}
    gm = call(GAMEPLAY_STATICS, "GetGameMode", 0, 160, pure=True)
    lib_self(gm, GAMEPLAY_STATICS, "/Script/Engine.Default__GameplayStatics")
    world_ctx(gm)
    gm_ret = gm.pin("ReturnValue", "object", "out", sub_obj=q(CLS.format("/Script/Engine.GameModeBase")))

    cast = Node("K2Node_DynamicCast", 250, 0, [f'TargetType="{GM_TYPE}"'])
    c_exe, c_then = exec_pins(cast)
    cast.pin("CastFailed", "exec", "out")
    obj = cast.pin("Object", "object", sub_obj=q(CLS.format("/Script/CoreUObject.Object")))
    as_gm = cast.pin(GM_CAST_PIN, "object", "out", sub_obj=q(GM_TYPE))
    cast.pin("bSuccess", "bool", "out", hidden=True)

    fn = call(GM_TYPE, "PelletCollected", 600, 0)
    f_exe, _ = exec_pins(fn)
    f_self = fn.pin("self", "object", sub_obj=q(GM_TYPE))
    link(gm_ret, obj)
    link(c_then, f_exe)
    link(as_gm, f_self)
    write("BP_Food_PelletCollected.txt", [gm, cast, fn])


if __name__ == "__main__":
    game_mode_graph()
    pellet_graph()
