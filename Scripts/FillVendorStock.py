# Fills each vendor placed in the open level with its stock.
# Run AFTER CreateHeroItems.py, with your test map open: Tools > Execute Python Script.
# Missing vendor Blueprints are created (child of BP_MyVendor) and placed in the level.
import unreal

SHOP = "/Game/StudentWork/Shop/"
ITEMS = "/Game/StudentWork/Items/"
SLOTS = 20

STOCK = {
    "Medic": [("Medic/BP_ProteinBar", 20), ("Medic/BP_NanoHealStim", 20),
              ("Medic/BP_AdrenalineShot", 20), ("Medic/BP_PowerCell", 20)],
    "SuitEngineer": [("SuitEngineer/" + n, 3) for n in (
        "BP_UtilityBelt", "BP_LegPlating", "BP_GripGauntlets", "BP_TitanPauldrons",
        "BP_KevlarChestRig", "BP_GravBoots", "BP_ArcBracers", "BP_TacticalVisor",
        "BP_StealthCape", "BP_EmblemPendant", "BP_PowerRing")],
    "Gadgeteer": [("Weapons/" + n, 3) for n in (
        "BP_BowArrow", "BP_Hammer", "BP_IronShield", "BP_PlasmaBlade", "BP_PulseBlaster")],
    "Craftsman": [("Craftsman/" + n, 50) for n in (
        "BP_NanoFibre", "BP_SynthWeave", "BP_CarbonStrut", "BP_BioSample",
        "BP_TitanAlloy", "BP_MeteorFragment", "BP_CreditChip")],
}

ITEM_CLASS = "ItemClass_2_A14892004C77EC1DDECCE087D008F8B6"
AMOUNT = "Amount_5_733C94724FF1FE15333C4EBE43064E7E"

lib = unreal.EditorAssetLibrary
shop_cls = lib.load_blueprint_class("/Game/Framework/Blueprints/Components/BPC_Shop")

# Get the Struct_ItemSlotData type from the framework NPC's default stock.
npc_cdo = unreal.get_default_object(lib.load_blueprint_class("/Game/Framework/Blueprints/Shop/BP_ShopNPC"))
sample = npc_cdo.get_editor_property("ShopInventory")
SlotType = type(sample[0]) if len(sample) else None


def make_slot(rel, amount):
    path = ITEMS + rel
    name = rel.split("/")[-1]
    if not lib.does_asset_exist(path):
        unreal.log_warning("Missing item (run CreateHeroItems.py first): " + path)
        return None
    s = SlotType()
    s.import_text("(%s=\"/Script/Engine.BlueprintGeneratedClass'%s.%s_C'\",%s=%d)"
                  % (ITEM_CLASS, path, name, AMOUNT, amount))
    if name not in s.export_text():
        unreal.log_warning("Could not set item " + name)
        return None
    return s


actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_actors = actors.get_all_level_actors()
tools = unreal.AssetToolsHelpers.get_asset_tools()
offset = 0

if SlotType is None:
    unreal.log_error("Could not read slot type from BP_ShopNPC. Nothing changed.")
else:
    for vendor, items in STOCK.items():
        bp_path = SHOP + "BP_MyVendor_" + vendor
        if not lib.does_asset_exist(bp_path):
            f = unreal.BlueprintFactory()
            f.set_editor_property("parent_class", lib.load_blueprint_class(SHOP + "BP_MyVendor"))
            tools.create_asset("BP_MyVendor_" + vendor, SHOP[:-1], unreal.Blueprint, f)
            lib.save_asset(bp_path)
        cls = lib.load_blueprint_class(bp_path)
        placed = [a for a in level_actors if a.get_class() == cls]
        if not placed:
            offset += 600
            placed = [actors.spawn_actor_from_class(cls, unreal.Vector(offset, 1500, 100))]
            unreal.log("Placed " + vendor + " vendor in level (move it where you like).")
        slots = [s for s in (make_slot(r, a) for r, a in items) if s]
        for actor in placed:
            comp = actor.get_component_by_class(shop_cls)
            if not comp:
                unreal.log_warning(vendor + ": no BPC_Shop component found")
                continue
            comp.set_editor_property("ShopInventory", slots)
            data = comp.get_editor_property("ShopInventoryData")
            t = data.export_text()
            import re
            t = re.sub(r"(AmountOfSlots_\d+_[0-9A-F]{32}=)\d+", r"\g<1>%d" % SLOTS, t)
            data.import_text(t)
            comp.set_editor_property("ShopInventoryData", data)
            unreal.log("%s: %d items stocked." % (vendor, len(slots)))

    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.log("Vendor stock done.")
