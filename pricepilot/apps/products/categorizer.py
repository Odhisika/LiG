"""Automatic product categorization.

Products imported from a supplier only carry a raw title (and sometimes a
description) — they almost never carry a real category. This module turns
that free text into one of the merchant store's (LiG's) category names so
new imports land in a sensible department instead of piling up in
Uncategorized.

Canonical category names deliberately match the categories already present
in the merchant store (LiG's `category_category` table, case-insensitive) so
the store sync resolves them exactly and never has to invent a new one.
Matching is fine-grained: a router goes to "Routers & Modems", a switch to
"Switches", a camera to "Security Cameras", a hard drive to "Storage", and
so on — mirroring the departments the store actually uses.
"""

import re

CANONICAL_CATEGORIES = frozenset(
    {
        "UPS",
        "Accessories",
        "Components",
        "Desktops",
        "Laptops",
        "Monitors",
        "Networking",
        "Peripherals",
        "Printers",
        "Routers & Modems",
        "Security & CCTV",
        "Security Cameras",
        "Software",
        "Storage",
        "Switches",
        "Projectors & Screens",
        "CCTV Accessories",
        "POS Equipment",
        "HDMI & AV Cables",
        "Networking Cables",
        "Toner & Ink",
    }
)

# Empty string = "no confident match", which the store sync maps to the
# configured Uncategorized category.
UNCATEGORIZED = ""


def _rule(category, pattern):
    return (category, re.compile(pattern, re.IGNORECASE))


# Rules run in order; the first hit wins. The title is matched first, alone;
# the description is only consulted when the title alone matches nothing.
# The ordering matters:
#   - The title-first pass matters for software: a bare "Microsoft Windows 11
#     Pro" name must reach the Software rule even though its generated
#     description says "Remote Desktop", "Wi-Fi security scanner" or "storage
#     engines". Hardware products keep winning because their device keywords
#     are earlier in the list than Software ("HP ... Windows 11 Home Laptop"
#     is still a laptop).
#   - Accessories go early because a "stand", "cable" or "box" keyword is
#     more specific than the device it might be bundled with.
#   - Standalone DIMM/SODIMM memory modules come before the laptop/desktop
#     rules, because a module's title often ends with "Hiker Laptop". The
#     remaining component keywords (DDR4/CPU/motherboard/...) come AFTER
#     Desktops/Laptops, so a complete system named "HP All-in-One ... 8GB
#     DDR5 RAM" isn't read as a bare component.
#   - Switches beat Desktops, since a "Desktop Network Switch" is a switch —
#     but the Switches rule never matches bare "PoE", or an "8 PoE NVR"
#     would be read as a switch.
#   - Desktops beat the generic laptop pattern, since "Desktop PC" names
#     also carry "Core i5" + "8GB RAM". The generic laptop pattern (CPU +
#     memory/storage words) sits before Storage so "i5 ... 1TB SSD" doesn't
#     fall into Storage.
#   - Storage beats Security & CCTV so "Surveillance Hard Disk Drive" stays
#     storage; Security & CCTV then beats the late Components rule so CCTV
#     power supplies (SMPS) aren't read as PC components.
#   - Routers & Modems and Networking never match bare "wifi"/"wi-fi"/
#     "wireless" — those words appear on cameras, printers, laptops, dongles
#     and access points. Routers are caught by "router"/"modem"; adapters,
#     dongles, hotspots and access points resolve via their own Networking
#     keywords.
#   - Non-camera CCTV gear (NVRs, intercoms, alarms, access terminals)
#     resolves to Security & CCTV before the camera keywords, so a
#     "Hikvision IP Video Intercom Kit" isn't misread as a camera — then
#     cameras land in the finer "Security Cameras" department.
#   - Peripherals sit before Routers & Modems/Networking so "Wireless
#     Keyboard and Mouse" stays a peripheral.
_RULES = [
    _rule(
        "UPS",
        r"\bups\b|uninterruptible|power\s+back|\bavr\b|"
        r"\bautomatic\s+voltage\s+regulator\b|\bvoltage\s+regulator\b|"
        r"\bstabilizer\b|\bpower\s+conditioner\b",
    ),
    _rule(
        "Toner & Ink",
        r"\btoner\b|\bink\s+(?:cartridge|bottle|tank|refill)\b|"
        r"\bcartridges?\b|\bprint\s+head\b|\bdrum\s+unit\b|"
        r"\b(hp|canon|brother|epson|starink|star\s+ink)\b.*\b(toner|cartridge|ink)\b|"
        r"\b(top\s+edge|compatible)\b.*\b(toner|cartridge)\b|"
        r"\b\d+[a-z]\b.*\b(?:cartridge|toner)\b",
    ),
    _rule(
        "Networking Cables",
        r"\bcat[5-8]\s+(?:cable|patch|utp|ftp|stp)\b|"
        r"\bpatch\s+cord\b|\bnetwork\s+cable\b|"
        r"\bcable\s+roll\b|\b\d+\s?m\b.*\b(?:cat[5-8]|utp|patch)\b|"
        r"\b305\s?m\b.*\b(?:cable|cat|utp)\b|\b100\s?m\b.*\b(?:cable|utp|cat)\b|"
        r"\brj45\s+(?:connector|crimp)\b|\bmodular\s+plug\b|"
        r"\b\d+\s?pcs?\b.*\b(?:rj45|connector|plug)\b|"
        r"\bcat[5-8]\b.*\b(?:cable|roll|drum|305|utp|ftp)\b|"
        r"\b(?:cable|roll|drum)\b.*\bcat[5-8]\b|"
        r"\bncb-[a-z0-9]+\b.*\b(?:cat[5-8]|utp|patch)\b",
    ),
    _rule(
        "HDMI & AV Cables",
        r"\bhdmi\b.*\b(?:cable|wire|cord|extender|splitter|switch|matrix|signal)\b|"
        r"\b(?:cable|wire|cord|extender|splitter)\b.*\bhdmi\b|"
        r"\bhdmi\s+\d+\.\d\b|"
        r"\b4k\s+(?:hdmi|splitter|extender|matrix)\b|"
        r"\bav\s+(?:cable|switch|splitter|matrix)\b|"
        r"\bvga\b.*\b(?:cable|splitter|switch)\b|"
        r"\bdisplay\s*port\b.*\b(?:cable|splitter|switch)\b|"
        r"\bcomposite\s+(?:cable|video)\b|\bcomponent\s+(?:cable|video)\b|"
        r"\baudio\s+(?:cable|splitter)\b|\b3.5\s?mm\b.*\b(?:cable|audio)\b|"
        r"\bwireless\s+(?:hdmi|video)\s+extender\b|\bhdcp\b|"
        r"\bhdtv\s+wireless\b|\bwireless\s+(?:transmitter|receiver)\b.*\b(?:1080|4k|hdmi)\b",
    ),
    _rule(
        "CCTV Accessories",
        r"\bbnc\b|\brg59\b|\brg6\b|\bcoaxial\b|\bpigtail\b|\bbalun\b|"
        r"\bbackbox(?:es)?|\bcable\s+(?:management|clip|tie)|"
        r"\bbrush\s+panel\b|\bbrush\s+wall\s+plate\b|"
        r"\bfiber\s+optic\b|\bfibre\s+optic\b|\bconduit\b|"
        r"\bcctv\s+(?:cable|bnc|power|supply|connector|accessories)\b|"
        r"\bsurveillance\s+(?:cable|bnc|connector)\b|"
        r"\bsmps\b|\bcctv\s+power\b|\bpower\s+supply.*\bcctv\b|"
        r"\b\d+(?:\.\d+)?\s?ft\b.*\b(?:bnc|cctv|coax)\b",
    ),
    _rule(
        "Accessories",
        r"\b(cables?|adapters?|chargers?|splitters?|converters?|"
        r"extenders?|hubs?|couplers?|plugs?|jacks?|brackets?|stands?|"
        r"holders?|cradles?|docks?|docking\s+station|cases?|covers?|sleeves?|bags?|"
        r"backpacks?|mats?|plates?|faceplates?|racks?|rollers?|screws?|keycaps?|"
        r"tempered\s+glass|screen\s+protector|masts?|"
        r"clips?|ties?|grommets?|kvms?|box(?:es)?|pens?|sockets?|"
        r"mousepads?|desk\s+pads?|panels?|brush(?:es)?|cabinets?|"
        r"extensions?|pdu|power\s+distribution|surge\s+protector|"
        r"power\s+strip|power\s+board|tool\s+kit|cleaning\s+agent|foam\s+cleaning|"
        r"flat\s+pack|(?:av|kvm)\s+switch|"
        r"shredders?|paper\s+shredder|\ba4\s+paper\b|"
        r"galaxy\s+s\d+\b|iphone\b|\bphone\b|\bmobile\s+phone\b|\bsmartphone\b)\b",
    ),
    _rule(
        "Components",
        r"\bsodimm\b|\bdimm\b",
    ),
    _rule(
        "Switches",
        r"\bswitch(?:es)?\b|\bgigabit\s+switch\b|\b(?:network|managed|unmanaged)\s+switch\b",
    ),
    _rule(
        "Desktops",
        r"(?<!docker\s)(?<!remote\s)(?<!ubuntu\s)(?<!fedora\s)\bdesktop\b|"
        r"\btowers?\b|\ball-in-one\b|\ball-ino\b|\baio\b|\bmini\s+pc\b|"
        r"\bsff\b|(?<!fedora\s)(?<!ubuntu\s)\bworkstations?\b|\bthinkcentre\b|"
        r"\bprodesk\b|\belitedesk\b|\bproone\b|\bpoweredge\b|\bproliant\b|\bxeon\b|"
        r"\bnuc\b|\bv\d{2}t\b",
    ),
    _rule(
        "Laptops",
        r"\blaptops?\b|\bnotebooks?\b|\bthinkpad\b|\bthinkbook\b|\bchromebook\b|"
        r"\bmacbooks?\b|\bprobook\b|\belitebook\b|\bzenbook\b|\bvivobook\b|"
        r"\bomnibook\b|\benvy\s+x360\b|\bx360\b|\b2-in-1\b|\bconvertibles?\b|"
        r"\bvostro\b|\blatitude\b|\binspiron\b|\bsurface\s+(?:laptop|book)\b",
    ),
    _rule(
        "Laptops",
        r"\b(core|i3|i5|i7|i9|ryzen|pentium|celeron|atom|ultra)\b.*"
        r"\b(ram|ssd|hdd|hard\s+drive|storage)\b",
    ),
    _rule(
        "Storage",
        r"\bssd\b|\bhdd\b|\bhard\s+disk\b|\bhard\s+drive\b|\bsolid\s+state\b|"
        r"\bnvme\b|\bm\.2\b|\bflash\s+drive\b|\busb\s+flash\b|\bpendrive\b|"
        r"\bthumb\s+drive\b|\bmemory\s+card\b|\bsd\s+card\b|\bsdhc\b|\buhs\b|"
        r"\bdata\s+traveler\b|\bcruzer\b|\bnas\b|\bstorage\b|"
        r"\bexternal\s+(?:drive|disk|portable)\b|\bexternal\b.*\b\d+\s?tb\b|"
        r"\bdata\s+center\s+drive\b|\bportable\s+hard\b",
    ),
    _rule(
        "Security & CCTV",
        r"\bnvr\b|\bdvr\b|\bsurveillance\b|\bintercom\b|\baccess\s+control\b|"
        r"\baccess\s+terminal\b|\balarms?\b|\bsensors?\b|\bturnstiles?\b|"
        r"\bbell\s+box\b|\bmotion\s+detector\b",
    ),
    _rule(
        "Components",
        r"\bddr[345]\b|\bprocessors?\b|\bcpu\b|\bmotherboards?\b|\bgpu\b|"
        r"\bgraphics\s+card\b|\bvideo\s+card\b|\bvga\s+card\b|"
        r"\bpcie\s+card\b|\bexpansion\s+card\b|\bpower\s+supply\b|\bpsu\b|"
        r"\bsound\s+card\b|\briser\b|\bbackplane\b",
    ),
    _rule(
        "Monitors",
        r"\bmonitors?\b|\blcd\b|\bdisplays?\b|\bscreens?\b|\buhd\b",
    ),
    _rule(
        "Projectors & Screens",
        r"\bprojectors?\b|\bpresenters?\b|\bwhiteboards?\b|"
        r"\bprojector\s+screen\b|\btripod\s+screen\b|\bflat\s+panel\s+display\b|"
        r"\blaser\s+projector\b|\bshort\s+throw\b|\blumen\b",
    ),
    _rule(
        "Printers",
        r"\bprinters?\b|\bmfp\b|\bmultifunction\b|\blaserjets?\b|\bdeskjets?\b|"
        r"\binkjets?\b|\bcopiers?\b|\bimagerunner\b|\bplotter\b|"
        r"\bthermal\s+printers?\b|\blabel\s+(?:printers?|makers?)\b|\bpos\s+printers?\b|"
        r"\breceipt\s+printers?\b",
    ),
    _rule(
        "POS Equipment",
        r"\bpos\s+(?:machine|terminal|system|device|unit)\b|"
        r"\bpoint\s+of\s+sale\b|\bcash\s+(?:drawer|register)\b|"
        r"\bthermal\s+paper\b|\bpos\s+paper\b|\breceipt\s+paper\b|"
        r"\bbarcode\s+(?:scanner|printer)\b|\bscanner\s+gun\b|"
        r"\bpos\s+(?:stand|mount|holder)\b|\bcustomer\s+display\b|"
        r"\bcash\s+drawer\s+(?:connector|cable)\b",
    ),
    _rule(
        "Peripherals",
        r"\bkeyboards?\b|\bmice\b|\bmouses?\b|\bwebcams?\b|\bspeakers?\b|\bheadsets?\b|"
        r"\bmicrophones?\b|\bheadphones?\b|\bscanners?\b|\bscanjet\b|\bscanning\b|"
        r"\btablets?\b|\bdrawing\s+pad\b|\bdrawing\s+tablet\b|\bpen\s+tablet\b|"
        r"\blaminat\w*\b|\bbinding\s+machines?\b|"
        r"\b(?:cash|bill|money)\s+counting\b|\bcounters?\b|"
        r"\bchromecast\b|\bstreaming\s+device\b|\btvs?\b|\bled\s+tv\b|\bsmart\s+tv\b",
    ),
    _rule(
        "Routers & Modems",
        r"\brouters?\b|\bmodems?\b|\bgateways?\b|\bwireless\s+router\b|\bcable\s+router\b",
    ),
    _rule(
        "Networking",
        r"\baccess\s+point\b|\bhotspots?\b|\bethernet\b|\bfirewalls?\b|"
        r"\bnic\b|\b4g\b|\b5g\b|\bgrandstream\b|\byealink\b|\bvoip\b|\bgigabit\b|"
        r"\bcpe\b|\bwalkie\s*talkie\b|\btwo-way\s+radio\b|\b\d+(?:\.\d+)?\s?ghz\b|"
        r"\b\d+mbps\b|\bmikrotik\b|\bubiquiti\b|\bunifi\b|"
        r"\b(?:wifi|wi-fi)\s+(?:dongle|adapter|card|receiver|stick)\b|"
        r"\bwireless\s+(?:adapter|card|dongle)\b|"
        r"\bextender\b|\bextenders?\b",
    ),
    _rule(
        "Security Cameras",
        r"\bcctv\b|\bcameras?\b|\bhikvision\b|\bhiksemi\b|\bbullet\s+camera\b|"
        r"\bdome\s+camera\b|\bip\s+camera\b|\bsurveillance\s+camera\b",
    ),
    _rule(
        "Software",
        r"\bwindows\b|\bmicrosoft\s+office\b|office\s+20[12]\d\b|office\s+365\b|"
        r"\bmicrosoft\s+365\b|\bpower\s+bi\b|\b365\s+apps\b|\bkaspersky\b|"
        r"\bantivirus\b|\blicense\b|\bproduct\s+key\b|\bactivation\s+key\b|"
        r"\bperpetual\b|\badobe\b|\blibreoffice\b|\bopenoffice\b|\bfedora\b|"
        r"\bubuntu\b|\bdebian\b|\blinux\b|\bserver\s+20[12]\d\b|\bdigital\s+download\b|"
        r"\be-learning\b|\bonline\s+course\b|\bvideo\s+course\b|\btutorial\b|"
        r"\bbitdefender\b|\bavast\b|\bclamav\b|\bmalwarebytes\b|\bsymantec\b|"
        r"\bnorton\b|\bmcafee\b|\btotal\s+security\b|\bdocker\b|\bteamviewer\b|"
        r"\banydesk\b|\bveeam\b|\bacronis\b|\bnmap\b|\bmariadb\b|\bmysql\b|"
        r"\bpostgres(?:ql)?\b|\bsql\s+server\b|\bduplicati\b|\bvisual\s+studio\b|"
        r"\bsquare\s+pos\b",
    ),
]


def categorize_product(name: str, description: str | None = None) -> str:
    """Map a product title/description to a canonical LiG category name.

    The title is matched first, alone: a product whose name clearly says
    "Windows 11 Pro" or "HP ... Laptop" is classified by that name even when
    its description buries unrelated hardware words ("Remote Desktop",
    "Wi-Fi security scanner", auto-generated spec labels). The description is
    only consulted when the title alone matches nothing.

    Returns "" when nothing matches confidently, so the caller can keep the
    product uncategorized and let the store sync fall back to Uncategorized.
    """
    name_text = (name or "").strip()
    for category, pattern in _RULES:
        if pattern.search(name_text):
            return category
    text = f"{name_text} {description or ''}"
    for category, pattern in _RULES:
        if pattern.search(text):
            return category
    return UNCATEGORIZED
