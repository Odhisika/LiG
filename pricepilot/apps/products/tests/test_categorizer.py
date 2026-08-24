import pytest

from apps.products.categorizer import CANONICAL_CATEGORIES, categorize_product


@pytest.mark.parametrize(
    "name,category",
    [
        ("HP EliteBook 640 G11 16GB RAM 1TB SSD", "Laptops"),
        ("DELL LATITUDE 5440 I5-1335U 8GB 512GB 14INCH LAPTOP", "Laptops"),
        ("HP 240 14 G10 i3-1315U 8GB RAM 512GB SSD", "Laptops"),
        ("Lenovo ThinkPad X1 Carbon Gen 12", "Laptops"),
        ("HP Pro Tower 290 G9 Desktop PC i5 8GB RAM", "Desktops"),
        ("Dell Poweredge T150 Xeon E-2314 16GB RAM", "Desktops"),
        ("HP All-in-One 24-cr1021nh Ultra 5 16GB RAM", "Desktops"),
        ("TOP EDGE POS MACHINE i5 6TH GEN 8GB RAM", "Desktops"),
        ("HP P24v G5 FHD Monitor", "Monitors"),
        ("Dell P2422H 24 inch IPS LCD Monitor", "Monitors"),
        ("Samsung 24 LF24T350FHN LED Monitor", "Monitors"),
        ("D-Link DIR-825M AC1200 Gigabit Wi-Fi Router", "Routers & Modems"),
        ("TP-Link TL-SG1008P 8-Port Gigabit PoE Switch", "Switches"),
        ("TP-LINK LS1005 5-Port 10/100Mbps Desktop Network Switch", "Switches"),
        ("TP-LINK TL-SG1016D 16-Port Gigabit Desktop/Rackmount Switch", "Switches"),
        ("MikroTik hEX S 5-Port Ethernet Router", "Routers & Modems"),
        ("BAOFENG BF-888S TWO-WAY RADIO WALKIE TALKIE", "Networking"),
        ("HIKSEMI 16GB DDR4 HIKER RAM DIMM 3200MHZ", "Components"),
        ("HIKSEMI DDR4 8GB SODIMM 3200MHz Hiker Laptop", "Components"),
        ("Canon C-EXV 60 Genuine Toner Cartridge", "Accessories"),
        ("HDMI Cable 1.5m", "Accessories"),
        ("Adjustable Laptop Stand v3.1", "Accessories"),
        ("CCTV Junction Box 85 X 85 Waterproof", "Accessories"),
        ("WD Purple 2TB Surveillance Hard Disk Drive", "Storage"),
        ("SanDisk 64GB micro SDHC UHS-I Card", "Storage"),
        ("Seagate External 4TB Expansion Portable", "Storage"),
        ("Hikvision DS-2CD2043G2-I 4MP IP Camera", "Security Cameras"),
        ("Hikvision DS-KIS603-P(C) IP Video Intercom Kit", "Security & CCTV"),
        ("Kaspersky Plus Internet Security 1 Year License", "Software"),
        ("Microsoft Office 2021 Pro Plus", "Software"),
        ("Windows 11 Pro Product Key", "Software"),
        ("Canon imageRUNNER 2425i A3 MFP", "Printers"),
        ("Epson L3251 EcoTank Inkjet Printer", "Printers"),
        ("DYMO Label Manager 160 Label Maker", "Printers"),
        ("APC 1200VA Back-UPS AVR", "UPS"),
        ("Logitech MK270 Wireless Keyboard and Mouse", "Peripherals"),
        ("ACER X1226 DLP SVGA PROJECTOR", "Peripherals"),
        ("Cisco Catalyst 2960 24-Port Managed Switch", "Switches"),
        ("Cisco Catalyst 2960 24-Port Switch", "Switches"),
        ("TP-LINK TL-SG1024D 24-Port Gigabit Switch", "Switches"),
        ("TP-Link Archer AX3000 WiFi 6 Router", "Routers & Modems"),
        ("Huawei HG8245H Fiber Modem", "Routers & Modems"),
        ("TP-Link EAP225 AC1350 Wireless Access Point", "Networking"),
        ("Dahua 2MP HD Dome CCTV Camera", "Security Cameras"),
        ("Hikvision DS-7608NI NVR 8 Channel", "Security & CCTV"),
        ("WD Red 4TB NAS Internal Hard Drive", "Storage"),
        ("HP All-in-One 24-cr1044nh 8GB DDR5 RAM 512GB NVMe SSD", "Desktops"),
        ("HP OmniBook 5 Flip 14 16GB LPDDR5 RAM 512GB SSD", "Laptops"),
        ("HIKVISION DS-7632NXI-K216P 32-ch PoE 1U AcuSense 4K NVR", "Security & CCTV"),
        ("Hikvision DS-2FA1225-D4 4 Channel CCTV Power Supply Unit", "Security & CCTV"),
        ("HIKVISION DS-2FA1208-C16 Multi-channel SMPS 16 Channel", "Security & CCTV"),
        ("Hikvision DS-K1T321MFWX Value Series Face Access Terminal", "Security & CCTV"),
        ("V380 PRO Q16S Bulb WiFi Wireless CCTV Camera 360", "Security Cameras"),
        ("Ubiquiti U6-PLUS (U6+) UniFi WiFi 6 Access Point", "Networking"),
        ("TP-LINK TL-WN823N Wi-Fi dongle USB A 300 MBPS", "Networking"),
        ("Microsoft Windows 11 Pro", "Software"),
        ("Ubuntu 24.04 LTS", "Software"),
        ("Fedora Workstation 40", "Software"),
        ("Bitdefender Total Security", "Software"),
        ("Avast Free Antivirus", "Software"),
        ("ClamAV", "Software"),
        ("Nmap", "Software"),
        ("Docker Desktop", "Software"),
        ("Square POS", "Software"),
        ("MariaDB", "Software"),
        ("Visual Studio Code", "Software"),
    ],
)
def test_categorizes_by_title(name, category):
    assert categorize_product(name) == category


@pytest.mark.parametrize(
    "name",
    [
        "Samsung Galaxy S24 128GB 8GB RAM",
        "Mystery Gadget 2000",
        "",
    ],
)
def test_returns_empty_when_unknown(name):
    assert categorize_product(name) == ""


def test_uses_description_when_title_is_vague():
    assert categorize_product("HP 24", description="Full HD IPS LCD Monitor") == "Monitors"


def test_title_beats_description_keywords():
    assert (
        categorize_product(
            "Microsoft Windows 11 Pro",
            description="Includes BitLocker, Remote Desktop and Hyper-V",
        )
        == "Software"
    )


def test_accessory_keyword_beats_bundled_device():
    assert categorize_product("Adjustable Laptop Stand") == "Accessories"


def test_canonical_categories_all_sync_friendly():
    assert "Monitors" in CANONICAL_CATEGORIES
    assert "Printers" in CANONICAL_CATEGORIES
    assert "Storage" in CANONICAL_CATEGORIES
    assert "Switches" in CANONICAL_CATEGORIES
    assert "Routers & Modems" in CANONICAL_CATEGORIES
    assert "Security Cameras" in CANONICAL_CATEGORIES
    assert all(c == c.strip() and not c.islower() for c in CANONICAL_CATEGORIES)
