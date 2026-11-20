"""
Generator teks node Blueprint (format salin-tempel Unreal) untuk Level Selection.

Menghasilkan:
  Scripts/blueprint_paste/WBP_LevelSelect_Graph.txt   -> tempel di Graph WBP_LevelSelect
  Scripts/blueprint_paste/WBP_MainMenu_NewGame.txt    -> tempel di Graph WBP_MainMenu

Jalankan (di luar Unreal, cukup Python biasa):
  python Scripts/make_level_select_paste.py
"""

import os
import uuid

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blueprint_paste")

LEVELS = [  # (nama tombol, map)
    ("ButtonLevel1", "/Game/LVL_PacMan.LVL_PacMan"),
    ("ButtonLevel2", "/Game/LVL_PacMan_02.LVL_PacMan_02"),
    ("ButtonLevel3", "/Game/LVL_PacMan_03.LVL_PacMan_03"),
]
MAIN_MENU_CLASS = "/Game/UI/Widgets/WBP_MainMenu.WBP_MainMenu_C"
LEVEL_SELECT_CLASS = "/Game/UI/Widgets/WBP_LevelSelect.WBP_LevelSelect_C"

CLS = "/Script/CoreUObject.Class'{}'"
GAMEPLAY_STATICS = CLS.format("/Script/Engine.GameplayStatics")


def gid():
    return uuid.uuid4().hex.upper()


class Node:
    counter = {}

    def __init__(self, cls_short, x, y, header_props):
        n = Node.counter.get(cls_short, 0)
        Node.counter[cls_short] = n + 1
        self.cls = f"/Script/{'UMGEditor' if cls_short == 'K2Node_CreateWidget' else 'BlueprintGraph'}.{cls_short}"
        self.name = f"{cls_short}_{n}"
        self.x, self.y = x, y
        self.props = header_props
        self.pins = []  # dict: id, name, dir, type, extra, links

    def pin(self, name, category, direction="in", sub_obj=None, extra="", hidden=False, subcat=""):
        p = {"id": gid(), "name": name, "dir": direction, "cat": category, "subcat": subcat,
             "sub": sub_obj, "extra": extra, "hidden": hidden, "links": [], "node": self}
        self.pins.append(p)
        return p

    def text(self):
        lines = [f'Begin Object Class={self.cls} Name="{self.name}"']
        lines += [f"   {p}" for p in self.props]
        lines += [f"   NodePosX={self.x}", f"   NodePosY={self.y}", f"   NodeGuid={gid()}"]
        for p in self.pins:
            parts = [f"PinId={p['id']}", f'PinName="{p["name"]}"']
            if p["dir"] == "out":
                parts.append('Direction="EGPD_Output"')
            parts.append(f'PinType.PinCategory="{p["cat"]}"')
            parts.append(f'PinType.PinSubCategory="{p["subcat"]}"')
            parts.append(f'PinType.PinSubCategoryObject={p["sub"] if p["sub"] else "None"}')
            if p["extra"]:
                parts.append(p["extra"])
            if p["links"]:
                parts.append("LinkedTo=(" + "".join(f"{q['node'].name} {q['id']}," for q in p["links"]) + ")")
            if p["hidden"]:
                parts.append("bHidden=True")
            lines.append("   CustomProperties Pin (" + ",".join(parts) + ",)")
        lines.append("End Object")
        return "\n".join(lines)


def link(a, b):
    a["links"].append(b)
    b["links"].append(a)


def call(member_parent, member, x, y, pure=False):
    props = [f'FunctionReference=(MemberParent="{member_parent}",MemberName="{member}")']
    if pure:
        props.append("bIsPureFunc=True")
    return Node("K2Node_CallFunction", x, y, props)


def exec_pins(node):
    return node.pin("execute", "exec"), node.pin("then", "exec", "out")


def bound_event(widget_bp, button, x, y):
    n = Node("K2Node_ComponentBoundEvent", x, y, [
        'DelegatePropertyName="OnClicked"',
        f'DelegateOwnerClass="{CLS.format("/Script/UMG.Button")}"',
        f'ComponentPropertyName="{button}"',
        'EventReference=(MemberParent="/Script/CoreUObject.Package\'/Script/UMG\'",'
        'MemberName="OnButtonClickedEvent__DelegateSignature")',
        "bInternalEvent=True",
    ])
    n.props.append(f'CustomFunctionName="BndEvt__{widget_bp}_{button}_{n.name}'
                   '_OnButtonClickedEvent__DelegateSignature"')
    n.pin("OutputDelegate", "delegate", "out")
    then = n.pin("then", "exec", "out")
    return n, then


def open_level(level_path, x, y):
    n = call(GAMEPLAY_STATICS, "OpenLevelBySoftObjectPtr", x, y)
    exe, then = exec_pins(n)
    n.pin("self", "object", sub_obj=f'"{GAMEPLAY_STATICS}"',
          extra='DefaultObject="/Script/Engine.Default__GameplayStatics"', hidden=True)
    n.pin("WorldContextObject", "object", sub_obj=f'"{CLS.format("/Script/CoreUObject.Object")}"', hidden=True)
    n.pin("Level", "softobject", sub_obj=f'"{CLS.format("/Script/Engine.World")}"',
          extra=f'DefaultValue="{level_path}"')
    n.pin("bAbsolute", "bool", extra='DefaultValue="true"')
    n.pin("Options", "string")
    return n, exe


def get_player_controller(x, y):
    pc = call(GAMEPLAY_STATICS, "GetPlayerController", x, y, pure=True)
    pc.pin("self", "object", sub_obj=f'"{GAMEPLAY_STATICS}"',
           extra='DefaultObject="/Script/Engine.Default__GameplayStatics"', hidden=True)
    pc.pin("WorldContextObject", "object", sub_obj=f'"{CLS.format("/Script/CoreUObject.Object")}"', hidden=True)
    pc.pin("PlayerIndex", "int", extra='DefaultValue="0"')
    ret = pc.pin("ReturnValue", "object", "out",
                 sub_obj=f'"{CLS.format("/Script/Engine.PlayerController")}"')
    return pc, ret


def game_input(x, y):
    """Show Mouse Cursor = false -> Set Input Mode Game Only (kembalikan input ke game)."""
    pc_cls = f'"{CLS.format("/Script/Engine.PlayerController")}"'
    pc, pc_ret = get_player_controller(x + 20, y + 170)

    cursor = Node("K2Node_VariableSet", x, y, [
        f'VariableReference=(MemberParent="{CLS.format("/Script/Engine.PlayerController")}",'
        'MemberName="bShowMouseCursor")'])
    c_exe, c_then = exec_pins(cursor)
    cursor.pin("bShowMouseCursor", "bool", extra='DefaultValue="false"')
    cursor.pin("Output_Get", "bool", "out")
    c_self = cursor.pin("self", "object", sub_obj=pc_cls)

    wbl = CLS.format("/Script/UMG.WidgetBlueprintLibrary")
    mode = call(wbl, "SetInputMode_GameOnly", x + 280, y)
    m_exe, m_then = exec_pins(mode)
    mode.pin("self", "object", sub_obj=f'"{wbl}"',
             extra='DefaultObject="/Script/UMG.Default__WidgetBlueprintLibrary"', hidden=True)
    m_pc = mode.pin("PlayerController", "object", sub_obj=pc_cls)
    mode.pin("bFlushInput", "bool", extra='DefaultValue="false"')

    link(pc_ret, c_self)
    link(pc_ret, m_pc)
    link(c_then, m_exe)
    return [pc, cursor, mode], c_exe, m_then


def switch_widget(widget_class, x, y):
    """Remove from Parent -> Create Widget(widget_class) -> Add to Viewport."""
    remove = call(CLS.format("/Script/UMG.Widget"), "RemoveFromParent", x, y)
    r_exe, r_then = exec_pins(remove)
    remove.pin("self", "object", sub_obj=f'"{CLS.format("/Script/UMG.Widget")}"')

    create = Node("K2Node_CreateWidget", x + 300, y, [])
    c_exe, c_then = exec_pins(create)
    create.pin("Class", "class", sub_obj=f'"{CLS.format("/Script/UMG.UserWidget")}"',
               extra=f'DefaultObject="{widget_class}"')
    owner = create.pin("OwningPlayer", "object",
                       sub_obj=f'"{CLS.format("/Script/Engine.PlayerController")}"')
    ret = create.pin("ReturnValue", "object", "out",
                     sub_obj=f'"{CLS.format("/Script/UMG.UserWidget")}"')

    add = call(CLS.format("/Script/UMG.UserWidget"), "AddToViewport", x + 650, y)
    a_exe, _ = exec_pins(add)
    a_self = add.pin("self", "object", sub_obj=f'"{CLS.format("/Script/UMG.UserWidget")}"')
    add.pin("ZOrder", "int", extra='DefaultValue="0"')

    pc = call(GAMEPLAY_STATICS, "GetPlayerController", x + 50, y + 180, pure=True)
    pc.pin("self", "object", sub_obj=f'"{GAMEPLAY_STATICS}"',
           extra='DefaultObject="/Script/Engine.Default__GameplayStatics"', hidden=True)
    pc.pin("WorldContextObject", "object", sub_obj=f'"{CLS.format("/Script/CoreUObject.Object")}"', hidden=True)
    pc.pin("PlayerIndex", "int", extra='DefaultValue="0"')
    pc_ret = pc.pin("ReturnValue", "object", "out",
                    sub_obj=f'"{CLS.format("/Script/Engine.PlayerController")}"')

    link(r_then, c_exe)
    link(c_then, a_exe)
    link(ret, a_self)
    link(pc_ret, owner)
    return [remove, create, add, pc], r_exe


def write(filename, nodes):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(n.text() for n in nodes) + "\n")
    print(f"ditulis: {path} ({len(nodes)} node)")


def main():
    # ---- Graph WBP_LevelSelect: 3 tombol level + tombol Back
    Node.counter = {}
    nodes = []
    row = 320
    for i, (button, level) in enumerate(LEVELS):
        ev, then = bound_event("WBP_LevelSelect", button, 0, i * row)
        inp, inp_exe, inp_then = game_input(400, i * row)
        ol, exe = open_level(level, 1000, i * row)
        link(then, inp_exe)
        link(inp_then, exe)
        nodes += [ev] + inp + [ol]
    ev, then = bound_event("WBP_LevelSelect", "ButtonBack", 0, 3 * row + 60)
    chain, first = switch_widget(MAIN_MENU_CLASS, 400, 3 * row + 60)
    link(then, first)
    nodes += [ev] + chain
    write("WBP_LevelSelect_Graph.txt", nodes)

    # ---- Graph WBP_MainMenu: pengganti Open Level di tombol New Game
    Node.counter = {}
    chain, _ = switch_widget(LEVEL_SELECT_CLASS, 400, 0)
    write("WBP_MainMenu_NewGame.txt", chain)


if __name__ == "__main__":
    main()
