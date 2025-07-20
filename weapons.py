weapon_stats = {
    "Ancient_Bow": {
        "Abso": 192,
        "Arcane": 276,
        "Genesis": 318,
        },
    "Arm_Cannon": {
        "Abso": 154,
        "Arcane": 221,
        "Genesis": 255
        },
    "Bladecaster": {
        "Abso": 205,
        "Arcane": 295,
        "Genesis": 340
        },
    "Bow": {
        "Abso": 192,
        "Arcane": 276,
        "Genesis": 318
        },
    "Cane": {
        "Abso": 197,
        "Arcane": 283,
        "Genesis": 326
        },
    "Chain": {
        "Abso": 192,
        "Arcane": 276,
        "Genesis": 318
        },
    "Chakram": {
        "Abso": 192,
        "Arcane": 276,
        "Genesis": 318
        },
    "Claw": {
        "Abso": 103,
        "Arcane": 149,
        "Genesis": 172
        },
    "Crossbow": {
        "Abso": 197,
        "Arcane": 283,
        "Genesis": 326
        },
    "Dagger": {
        "Abso": 192,
        "Arcane": 276,
        "Genesis": 318
        },
    "Desperado": {
        "Abso": 205,
        "Arcane": 295,
        "Genesis": 340
        },
    "Dual_Bowgun": {
        "Abso": 192,
        "Arcane": 276,
        "Genesis": 318
        },
    "Fan": {
        "Abso": 241,
        "Arcane": 347,
        "Genesis": 400
        },
    "Gun": {
        "Abso": 150,
        "Arcane": 216,
        "Genesis": 249
        },
    "Hand_Cannon": {
        "Abso": 210,
        "Arcane": 302,
        "Genesis": 348
        },
    "Heavy_Sword": {
        "Abso": 207,
        "Arcane": 297,
        "Genesis": 342
        },
    "Katana": {
        "Abso": 197,
        "Arcane": 283,
        "Genesis": 326
        },
    "Knuckle": {
        "Abso": 154,
        "Arcane": 221,
        "Genesis": 255
        },
    "Long_Sword": {
        "Abso": 203,
        "Arcane": 293,
        "Genesis": 337
        },
    "Lucent_Gauntlet": {
        "Abso": 241,
        "Arcane": 347,
        "Genesis": 400
        },
    "1H_Axe": {
        "Abso": 197,
        "Arcane": 283,
        "Genesis": 326
        },
    "1H_Blunt": {
        "Abso": 197,
        "Arcane": 283,
        "Genesis": 326
        },
    "1H_Sword": {
        "Abso": 197,
        "Arcane": 283,
        "Genesis": 326
        },
    "Polearm": {
        "Abso": 184,
        "Arcane": 264,
        "Genesis": 304
        },
    "Psy-limiter": {
        "Abso": 241,
        "Arcane": 347,
        "Genesis": 400
        },
    "Ritual_Fan": {
        "Abso": 192,
        "Arcane": 276,
        "Genesis": 318
        },
    "Scepter": {
        "Abso": 241,
        "Arcane": 347,
        "Genesis": 400
        },
    "Shining_Rod": {
        "Abso": 241,
        "Arcane": 347,
        "Genesis": 400
        },
    "Soul_Shooter": {
        "Abso": 154,
        "Arcane": 221,
        "Genesis": 255
        },
    "Spear": {
        "Abso": 205,
        "Arcane": 295,
        "Genesis": 340
        },
    "Staff": {
        "Abso": 245,
        "Arcane": 353,
        "Genesis": 406
        },
    "2H_Axe": {
        "Abso": 205,
        "Arcane": 295,
        "Genesis": 340
        },
    "2H_Blunt": {
        "Abso": 205,
        "Arcane": 295,
        "Genesis": 340
        },
    "2H_Sword": {
        "Abso": 205,
        "Arcane": 295,
        "Genesis": 340
        },
    "Wand": {
        "Abso": 241,
        "Arcane": 347,
        "Genesis": 400
        },
    "Whip_Blade": {
        "Abso": 154,
        "Arcane": 221,
        "Genesis": 255
        },
    "Whispershot": {
        "Abso": 192,
        "Arcane": 276,
        "Genesis": 318
        },
    "Martial_Brace": {
        "Abso": 154,
        "Arcane": 221,
        "Genesis": 255
        },
    "Celestial_Light": {
        "Abso": 241,
        "Arcane": 347,
        "Genesis": 400
        },
}

# A mapping of weapon types to the classes and aliases that use them.
# This is much easier to read and maintain than a flat alias dictionary.
CLASS_WEAPONS_MAP = {
    "Ancient_Bow": ["Pathfinder", "pf"],
    "Arm_Cannon": ["Blaster"],
    "Bladecaster": ["Adele"],
    "Bow": ["Bowmaster", "bm", "WindArcher", "wa"],
    "Cane": ["Phantom"],
    "Chain": ["Cadena"],
    "Chakram": ["Khali"],
    "Claw": ["NightLord", "nl", "NightWalker", "nw"],
    "Crossbow": ["Marksman", "mm", "WildHunter", "wh"],
    "Dagger": ["Shadower", "shad", "DualBlade", "db"],
    "Desperado": ["DemonAvenger", "da"],
    "Dual_Bowgun": ["Mercedes", "merc"],
    "Fan": ["Kanna"],
    "Gun": ["Corsair", "Mechanic", "mech"],
    "Hand_Cannon": ["Cannoneer"],
    "Katana": ["Hayato"],
    "Knuckle": ["Shade", "ThunderBreaker", "tb", "Buccaneer", "bucc", "Ark"],
    "Lucent_Gauntlet": ["Illium"],
    "Polearm": ["Aran"],
    "Psy-limiter": ["Kinesis"],
    "Ritual_Fan": ["Hoyoung", "hy"],
    "Scepter": ["Lynn"],
    "Shining_Rod": ["Luminous", "lumi"],
    "Soul_Shooter": ["AngelicBuster", "ab"],
    "Spear": ["DarkKnight", "dk"],
    "Staff": ["I/L", "F/P", "Bishop", "Evan", "BlazeWizard", "bw", "BattleMage", "bam"],
    "2H_Blunt": ["DemonSlayer", "ds", "Paladin", "pally"],
    "2H_Axe": ["Hero"],
    "2H_Sword": ["DawnWarrior", "dw"],
    "Wand": ["Lara"],
    "Whip_Blade": ["Xenon"],
    "Whispershot": ["Kain"],
    "Martial_Brace": ["MoXuan", "mx"],
    "Celestial_Light": ["Sia"],
}

weapon_flame = {"Abso": {"T3": .15, "T4": .22, "T5": .3025, "T6": .3993, "T7": .512435},
         "Arcane": {"T3": .18, "T4": .264, "T5": .363, "T6": .47916, "T7": .614922},
         "Genesis": {"T3": .18, "T4": .264, "T5": .363, "T6": .47916, "T7": .614922}}
import math

def _create_weapon_lookup():
    """Generates a unified, case-insensitive lookup dictionary for weapons and classes."""
    lookup = {}
    # Add direct weapon stats (e.g., "bow", "staff")
    for weapon, stats in weapon_stats.items():
        lookup[weapon.lower()] = stats

    # Add class aliases from the map
    for weapon, aliases in CLASS_WEAPONS_MAP.items():
        if weapon in weapon_stats:
            stats = weapon_stats[weapon]
            for alias in aliases:
                lookup[alias.lower()] = stats
    return lookup

# A unified, case-insensitive dictionary for easy lookups from bot commands.
# Maps all weapon names, class names, and aliases to their stat dictionaries.
WEAPON_LOOKUP = _create_weapon_lookup()

def weapon_calc(attack: int, weapon_type: str) -> str:
    """
    Calculates the flame attack values for a given base attack and weapon tier.

    Args:
        attack: The base attack of the weapon.
        weapon_type: The type of the weapon ('Abso', 'Arcane', 'Genesis').

    Returns:
        A formatted string of flame tiers and their corresponding attack values,
        or an error message if the weapon type is invalid.
    """
    if weapon_type in weapon_flame:
        calc = {tier: math.ceil(attack * flame) for tier, flame in weapon_flame[weapon_type].items()}
        return(", ".join(f"{k} = {v}" for k, v in calc.items()))
    else:
        return "Invalid Weapon Type"
