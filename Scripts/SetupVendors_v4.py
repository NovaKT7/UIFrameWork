# Puts stock + NPC names straight into each vendor Blueprint (BP_MyVendor_*).
# Run AFTER CreateHeroItems.py. Close the vendor Blueprint tabs first.
# Tools > Execute Python Script > SetupVendors.py
import re
import unreal

SHOP = "/Game/StudentWork/Shop/BP_MyVendor_"
ITEMS = "/Game/StudentWork/Items/"
SLOTS = 20

VENDORS = {
    "Medic": ("Dr. Vera Patch (Medic)", [("Medic/" + n, 20) for n in (
        "BP_ProteinBar", "BP_NanoHealStim", "BP_AdrenalineShot", "BP_PowerCell")]),
    "SuitEngineer": ("Rivet (Suit Engineer)", [("SuitEngineer/" + n, 3) for n in (
        "BP_UtilityBelt", "BP_LegPlating", "BP_GripGauntlets", "BP_TitanPauldrons",
        "BP_KevlarChestRig", "BP_GravBoots", "BP_ArcBracers", "BP_TacticalVisor",
        "BP_StealthCape", "BP_EmblemPendant", "BP_PowerRing")]),
    "Gadgeteer": ("Sprocket (Gadgeteer)", [("Weapons/" + n, 3) for n in (
        "BP_BowArrow", "BP_Hammer", "BP_IronShield", "BP_PlasmaBlade", "BP_PulseBlaster")]),
    "Craftsman": ("Tinker Jax (Craftsman)", [("Craftsman/" + n, 50) for n in (
        "BP_NanoFibre", "BP_SynthWeave", "BP_CarbonStrut", "BP_BioSample",
        "BP_TitanAlloy", "BP_MeteorFragment", "BP_CreditChip")]),
}

ITEM_CLASS = "ItemClass_2_A14892004C77EC1DDECCE087D008F8B6"
AMOUNT = "Amount_5_733C94724FF1FE15333C4EBE43064E7E"

lib = unreal.EditorAssetLibrary
shop_cls = lib.load_blueprint_class("/Game/Framework/Blueprints/Components/BPC_Shop")
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
SDL = unreal.SubobjectDataBlueprintFunctionLibrary
SOURCE = None


def make_slots(items):
    # Copy the existing slot array, resize it, then rewrite each entry.
    valid = []
    for rel, amount in items:
        path = ITEMS + rel
        if lib.does_asset_exist(path):
            valid.append((path, rel.split("/")[-1], amount))
        else:
            unreal.log_warning("Missing item (run CreateHeroItems.py first): " + path)
    arr = SOURCE.get_editor_property("ShopInventory")
    if not valid:
        return None
    while len(arr) < len(valid):
        arr.append(arr[0])
    while len(arr) > len(valid):
        arr.pop()
    for i, (path, name, amount) in enumerate(valid):
        e = arr[i]
        e.import_text("(%s=\"/Script/Engine.BlueprintGeneratedClass'%s.%s_C'\",%s=%d)"
                      % (ITEM_CLASS, path, name, AMOUNT, amount))
        if name not in e.export_text():
            unreal.log_warning("Could not set " + name)
        arr[i] = e
    return arr


def templates(bp):
    """Yield this Blueprint's own (editable) component templates."""
    pkg = bp.get_path_name().split(".")[0]
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        if hasattr(SDL, "get_object_for_blueprint"):
            obj = SDL.get_object_for_blueprint(data, bp)
        else:
            obj = SDL.get_object(data)
        if obj and obj.get_path_name().startswith(pkg):
            yield obj


# Borrow the slot struct type from any vendor whose shop already has an entry.
for key in VENDORS:
    if SOURCE or not lib.does_asset_exist(SHOP + key):
        continue
    for obj in templates(lib.load_asset(SHOP + key)):
        if obj.get_class() == shop_cls:
            inv = obj.get_editor_property("ShopInventory")
            if len(inv):
                SOURCE, SOURCE_KEY = obj, key
                unreal.log("Slot type taken from " + key)
                break

if SOURCE is None:
    raise RuntimeError("Add ONE item to Shop Inventory in any vendor's BPC_Shop, save, and run again.")

# The source vendor's list is reused as scratch space, so do it LAST.
ORDER = [k for k in VENDORS if k != SOURCE_KEY] + [SOURCE_KEY]

for key in ORDER:
    npc_name, items = VENDORS[key]
    bp_path = SHOP + key
    if not lib.does_asset_exist(bp_path):
        unreal.log_warning("Vendor not found: " + bp_path)
        continue
    bp = lib.load_asset(bp_path)
    cdo = unreal.get_default_object(bp.generated_class())

    try:
        cdo.set_editor_property("NameText", unreal.Text(npc_name))
    except Exception:
        pass

    shop_done = text_done = False
    for obj in templates(bp):
        if obj.get_class() == shop_cls:
            slots = make_slots(items)  # build right before use
            if slots is None:
                continue
            obj.set_editor_property("ShopInventory", slots)
            first = items[0][0].split("/")[-1]
            got = obj.get_editor_property("ShopInventory")
            if not len(got) or first not in got[0].export_text():
                unreal.log_warning(key + ": stock check FAILED")
            d = obj.get_editor_property("ShopInventoryData")
            d.import_text(re.sub(r"(AmountOfSlots_\d+_[0-9A-F]{32}=)\d+",
                                 r"\g<1>%d" % SLOTS, d.export_text()))
            obj.set_editor_property("ShopInventoryData", d)
            shop_done = True
        elif isinstance(obj, unreal.TextRenderComponent):
            obj.set_editor_property("text", unreal.Text(npc_name))
            text_done = True

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    lib.save_loaded_asset(bp)
    unreal.log("%s (%s): %d items | shop component %s | name tag %s" % (
        key, npc_name, len(items), "OK" if shop_done else "NOT SET - see note",
        "OK" if text_done else "NOT SET - see note"))

unreal.log("Vendor setup done.")
