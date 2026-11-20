"""
Generator teks node Blueprint (salin-tempel) untuk sistem skin Pac-Man.

Menghasilkan di Scripts/blueprint_paste/:
  BP_ThirdPersonCharacter_Skin.txt -> Event BeginPlay (pasang skin) + Event Tick (animasi ikut kecepatan)
  WBP_Customize_Graph.txt          -> tombol Classic / Black Monster / Lil Evil / Back
  WBP_MainMenu_Customize.txt       -> buka WBP_Customize dari tombol Customize

Jalankan: python Scripts/make_skin_paste.py
"""

from make_level_select_paste import (CLS, GAMEPLAY_STATICS, Node, bound_event, call, exec_pins,
                                     link, switch_widget, write)

GI_CLASS = "/Game/ThirdPerson/Blueprints/BP_PacManGameInstance.BP_PacManGameInstance_C"
GI_TYPE = f"/Script/Engine.BlueprintGeneratedClass'{GI_CLASS}'"
GI_CAST_PIN = "AsBP Pac Man Game Instance"
MAIN_MENU_CLASS = "/Game/UI/Widgets/WBP_MainMenu.WBP_MainMenu_C"
CUSTOMIZE_CLASS = "/Game/UI/Widgets/WBP_Customize.WBP_Customize_C"
KML = CLS.format("/Script/Engine.KismetMathLibrary")
SKMC = CLS.format("/Script/Engine.SkeletalMeshComponent")

# index SelectedSkin -> (nama tombol, skeletal mesh, animasi jalan); 0 = Classic (tidak diganti)
SKINS = [
    ("ButtonClassic", None, None),
    ("ButtonBlackMonster", "/Game/PacMan/Skins/BlackMonster/SK_BlackMonster.SK_BlackMonster",
     "/Game/PacMan/Skins/BlackMonster/A_BlackMonster_Walk.A_BlackMonster_Walk"),
    ("ButtonLilEvil", "/Game/PacMan/Skins/LilEvil/SK_LilEvil.SK_LilEvil",
     "/Game/PacMan/Skins/LilEvil/A_LilEvil_Walk.A_LilEvil_Walk"),
]


def q(path):
    return f'"{path}"'


# ---------------------------------------------------------------- node kecil
def event(member, x, y, extra_out=None):
    n = Node("K2Node_Event", x, y, [
        f'EventReference=(MemberParent="{CLS.format("/Script/Engine.Actor")}",MemberName="{member}")',
        "bOverrideFunction=True"])
    n.pin("OutputDelegate", "delegate", "out")
    then = n.pin("then", "exec", "out")
    if extra_out:
        n.pin(*extra_out)
    return n, then


def get_game_instance_cast(x, y):
    """Get Game Instance -> Cast To BP_PacManGameInstance (impure). Return (nodes, exe, then, as_pin)."""
    gi = call(GAMEPLAY_STATICS, "GetGameInstance", x, y + 150, pure=True)
    gi.pin("self", "object", sub_obj=q(GAMEPLAY_STATICS),
           extra='DefaultObject="/Script/Engine.Default__GameplayStatics"', hidden=True)
    gi.pin("WorldContextObject", "object", sub_obj=q(CLS.format("/Script/CoreUObject.Object")), hidden=True)
    gi_ret = gi.pin("ReturnValue", "object", "out", sub_obj=q(CLS.format("/Script/Engine.GameInstance")))

    cast = Node("K2Node_DynamicCast", x + 250, y, [f'TargetType="{GI_TYPE}"'])
    exe, then = exec_pins(cast)
    cast.pin("CastFailed", "exec", "out")
    obj = cast.pin("Object", "object", sub_obj=q(CLS.format("/Script/CoreUObject.Object")))
    as_pin = cast.pin(GI_CAST_PIN, "object", "out", sub_obj=q(GI_TYPE))
    cast.pin("bSuccess", "bool", "out", hidden=True)
    link(gi_ret, obj)
    return [gi, cast], exe, then, as_pin


def mesh_get(x, y):
    n = Node("K2Node_VariableGet", x, y, [
        f'VariableReference=(MemberParent="{CLS.format("/Script/Engine.Character")}",MemberName="Mesh",bSelfContext=True)'])
    return n, n.pin("Mesh", "object", "out", sub_obj=q(SKMC))


def branch(x, y):
    n = Node("K2Node_IfThenElse", x, y, [])
    exe = n.pin("execute", "exec")
    cond = n.pin("Condition", "bool", extra='DefaultValue="true"')
    t = n.pin("then", "exec", "out")
    f = n.pin("else", "exec", "out")
    return n, exe, cond, t, f


def int_equals(value, x, y):
    n = call(KML, "EqualEqual_IntInt", x, y, pure=True)
    n.pin("self", "object", sub_obj=q(KML), extra='DefaultObject="/Script/Engine.Default__KismetMathLibrary"', hidden=True)
    a = n.pin("A", "int", extra='DefaultValue="0"')
    n.pin("B", "int", extra=f'DefaultValue="{value}"')
    ret = n.pin("ReturnValue", "bool", "out")
    return n, a, ret


def mesh_call(member, x, y, mesh_out, pins):
    """Fungsi SkeletalMeshComponent dengan Target = Mesh. pins: list (name, category, extra, sub_obj, subcat)."""
    n = call(SKMC, member, x, y)
    exe, then = exec_pins(n)
    tgt = n.pin("self", "object", sub_obj=q(SKMC))
    link(mesh_out, tgt)
    for name, cat, extra, sub, subcat in pins:
        n.pin(name, cat, extra=extra, sub_obj=sub, subcat=subcat)
    return n, exe, then


def set_using_skin(value, x, y):
    n = Node("K2Node_VariableSet", x, y, ['VariableReference=(MemberName="UsingSkinAnim",bSelfContext=True)'])
    exe, then = exec_pins(n)
    n.pin("UsingSkinAnim", "bool", extra=f'DefaultValue="{str(value).lower()}"')
    n.pin("Output_Get", "bool", "out")
    return n, exe, then


def apply_skin_chain(mesh_path, anim_path, x, y):
    nodes = []
    m, m_out = mesh_get(x, y + 200)
    s1, e1, t1 = mesh_call("SetSkeletalMeshAsset", x + 200, y, m_out, [
        ("NewMesh", "object", f'DefaultObject="{mesh_path}"', q(CLS.format("/Script/Engine.SkeletalMesh")), "")])
    s2, e2, t2 = mesh_call("SetAnimationMode", x + 500, y, m_out, [
        ("InAnimationMode", "byte", 'DefaultValue="AnimationSingleNode"',
         q("/Script/CoreUObject.Enum'/Script/Engine.EAnimationMode'"), ""),
        ("bForceInitAnimScriptInstance", "bool", 'DefaultValue="true"', None, "")])
    s3, e3, t3 = mesh_call("PlayAnimation", x + 800, y, m_out, [
        ("NewAnimToPlay", "object", f'DefaultObject="{anim_path}"', q(CLS.format("/Script/Engine.AnimationAsset")), ""),
        ("bLooping", "bool", 'DefaultValue="true"', None, "")])
    s4, e4, _ = set_using_skin(True, x + 1100, y)
    link(t1, e2)
    link(t2, e3)
    link(t3, e4)
    nodes += [m, s1, s2, s3, s4]
    return nodes, e1


def gi_selected_skin_get(as_pin, x, y):
    n = Node("K2Node_VariableGet", x, y, [
        f'VariableReference=(MemberParent="{GI_TYPE}",MemberName="SelectedSkin")'])
    out = n.pin("SelectedSkin", "int", "out")
    s = n.pin("self", "object", sub_obj=q(GI_TYPE))
    link(as_pin, s)
    return n, out


# ---------------------------------------------------------------- BP_ThirdPersonCharacter
def character_graph():
    Node.counter = {}
    nodes = []
    bp, bp_then = event("ReceiveBeginPlay", 0, 0)
    cast_nodes, c_exe, c_then, as_pin = get_game_instance_cast(250, 0)
    link(bp_then, c_exe)
    nodes += [bp] + cast_nodes

    sel, sel_out = gi_selected_skin_get(as_pin, 600, 220)
    nodes.append(sel)

    prev_else = c_then
    y = 0
    for idx, (_, mesh, anim) in enumerate(SKINS):
        if mesh is None:
            continue
        eq, eq_a, eq_ret = int_equals(idx, 850, y + 180)
        link(sel_out, eq_a)
        br, br_exe, br_cond, br_t, br_f = branch(1050, y)
        link(eq_ret, br_cond)
        link(prev_else, br_exe)
        chain, chain_exe = apply_skin_chain(mesh, anim, 1300, y)
        link(br_t, chain_exe)
        nodes += [eq, br] + chain
        prev_else = br_f
        y += 420

    # Event Tick: kecepatan animasi mengikuti kecepatan jalan (diam = mulut berhenti)
    tick, tick_then = event("ReceiveTick", 0, y + 200,
                            ("DeltaSeconds", "real", "out", None, "", False, "float"))
    get_flag = Node("K2Node_VariableGet", 200, y + 380,
                    ['VariableReference=(MemberName="UsingSkinAnim",bSelfContext=True)'])
    flag = get_flag.pin("UsingSkinAnim", "bool", "out")
    br, br_exe, br_cond, br_t, _ = branch(400, y + 200)
    link(tick_then, br_exe)
    link(flag, br_cond)

    vel = call(CLS.format("/Script/Engine.Actor"), "GetVelocity", 450, y + 520, pure=True)
    vel.pin("self", "object", sub_obj=q(CLS.format("/Script/Engine.Actor")))
    vel_ret = vel.pin("ReturnValue", "struct", "out", sub_obj=q("/Script/CoreUObject.ScriptStruct'/Script/CoreUObject.Vector'"))
    vsize = call(KML, "VSize", 700, y + 520, pure=True)
    vsize.pin("self", "object", sub_obj=q(KML), extra='DefaultObject="/Script/Engine.Default__KismetMathLibrary"', hidden=True)
    vs_a = vsize.pin("A", "struct", sub_obj=q("/Script/CoreUObject.ScriptStruct'/Script/CoreUObject.Vector'"))
    vs_ret = vsize.pin("ReturnValue", "real", "out", subcat="double")
    div = call(KML, "Divide_DoubleDouble", 950, y + 520, pure=True)
    div.pin("self", "object", sub_obj=q(KML), extra='DefaultObject="/Script/Engine.Default__KismetMathLibrary"', hidden=True)
    div_a = div.pin("A", "real", subcat="double", extra='DefaultValue="0.0"')
    div.pin("B", "real", subcat="double", extra='DefaultValue="500.0"')
    div_ret = div.pin("ReturnValue", "real", "out", subcat="double")
    link(vel_ret, vs_a)
    link(vs_ret, div_a)

    m, m_out = mesh_get(950, y + 380)
    rate, rate_exe, _ = mesh_call("SetPlayRate", 1200, y + 200, m_out, [])
    rate_pin = rate.pin("Rate", "real", subcat="float", extra='DefaultValue="1.0"')
    link(br_t, rate_exe)
    link(div_ret, rate_pin)
    nodes += [tick, get_flag, br, vel, vsize, div, m, rate]
    write("BP_ThirdPersonCharacter_Skin.txt", nodes)


# ---------------------------------------------------------------- WBP_Customize
def customize_graph():
    Node.counter = {}
    nodes = []
    row = 340
    for idx, (button, _, _) in enumerate(SKINS):
        ev, then = bound_event("WBP_Customize", button, 0, idx * row)
        cast_nodes, c_exe, c_then, as_pin = get_game_instance_cast(300, idx * row)
        setn = Node("K2Node_VariableSet", 800, idx * row, [
            f'VariableReference=(MemberParent="{GI_TYPE}",MemberName="SelectedSkin")'])
        s_exe, s_then = exec_pins(setn)
        setn.pin("SelectedSkin", "int", extra=f'DefaultValue="{idx}"')
        setn.pin("Output_Get", "int", "out")
        s_self = setn.pin("self", "object", sub_obj=q(GI_TYPE))
        chain, first = switch_widget(MAIN_MENU_CLASS, 1100, idx * row)
        link(then, c_exe)
        link(c_then, s_exe)
        link(as_pin, s_self)
        link(s_then, first)
        nodes += [ev] + cast_nodes + [setn] + chain
    ev, then = bound_event("WBP_Customize", "ButtonBack", 0, len(SKINS) * row + 60)
    chain, first = switch_widget(MAIN_MENU_CLASS, 400, len(SKINS) * row + 60)
    link(then, first)
    nodes += [ev] + chain
    write("WBP_Customize_Graph.txt", nodes)

    Node.counter = {}
    chain, _ = switch_widget(CUSTOMIZE_CLASS, 400, 0)
    write("WBP_MainMenu_Customize.txt", chain)


if __name__ == "__main__":
    character_graph()
    customize_graph()
