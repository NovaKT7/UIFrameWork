# Puts stock + NPC names straight into each vendor Blueprint (BP_MyVendor_*).
# Run AFTER CreateHeroItems.py. Close the vendor Blueprint tabs first.
# Tools > Execute Python Script > SetupVendors.py
import re
import unreal

SHOP = "/Game/StudentWork/Shop/BP_MyVendor_"
ITEMS = "/Game/StudentWork/Items/"
SLOTS = 20

VENDORS = {
    "Medic": ("Dr. Vera Patch", [("Medic/" + n, 20) for n in (
        "BP_ProteinBar", "BP_NanoHealStim", "BP_AdrenalineShot", "BP_PowerCell")]),
    "SuitEngineer": ("Rivet", [("SuitEngineer/" + n, 3) for n in (
        "BP_UtilityBelt", "BP_LegPlating", "BP_GripGauntlets", "BP_TitanPauldrons",
        "BP_KevlarChestRig", "BP_GravBoots", "BP_ArcBracers", "BP_TacticalVisor",
        "BP_StealthCape", "BP_EmblemPendant", "BP_PowerRing")]),
    "Gadgeteer": ("Sprocket", [("Weapons/" + n, 3) for n in (
        "BP_BowArrow", "BP_Hammer", "BP_IronShield", "BP_PlasmaBlade", "BP_PulseBlaster")]),
    "Craftsman": ("Tinker Jax", [("Craftsman/" + n, 50) for n in (
        "BP_NanoFibre", "BP_SynthWeave", "BP_CarbonStrut", "BP_BioSample",
        "BP_TitanAlloy", "BP_MeteorFragment", "BP_CreditChip")]),
}

ITEM_CLASS = "ItemClass_2_A14892004C77EC1DDECCE087D008F8B6"
AMOUNT = "Amount_5_733C94724FF1FE15333C4EBE43064E7E"

lib = unreal.EditorAssetLibrary
shop_cls = lib.load_blueprint_class("/Game/Framework/Blueprints/Components/BPC_Shop")
npc_cdo = unreal.get_default_object(lib.load_blueprint_class("/Game/Framework/Blueprints/Shop/BP_ShopNPC"))
SlotType = type(npc_cdo.get_editor_property("ShopInventory")[0])
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
SDL = unreal.SubobjectDataBlueprintFunctionLibrary


def make_slots(items):
    out = []
    for rel, amount in items:
        path = ITEMS + rel
        name = rel.split("/")[-1]
        if not lib.does_asset_exist(path):
            unreal.log_warning("Missing item (run CreateHeroItems.py first): " + path)
            continue
        s = SlotType()
        s.import_text("(%s=\"/Script/Engine.BlueprintGeneratedClass'%s.%s_C'\",%s=%d)"
                      % (ITEM_CLASS, path, name, AMOUNT, amount))
        out.append(s)
    return out


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


for key, (npc_name, items) in VENDORS.items():
    bp_path = SHOP + key
    if not lib.does_asset_exist(bp_path):
        unreal.log_warning("Vendor not found: " + bp_path)
        continue
    bp = lib.load_asset(bp_path)
    slots = make_slots(items)
    cdo = unreal.get_default_object(bp.generated_class())

    for prop, val in (("ShopInventory", slots), ("NameText", unreal.Text(npc_name))):
        try:
            cdo.set_editor_property(prop, val)
        except Exception:
            pass

    shop_done = text_done = False
    for obj in templates(bp):
        if obj.get_class() == shop_cls:
            obj.set_editor_property("ShopInventory", slots)
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
        key, npc_name, len(slots), "OK" if shop_done else "NOT SET - see note",
        "OK" if text_done else "NOT SET - see note"))

unreal.log("Vendor setup done.")
