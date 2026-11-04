#!/usr/bin/env python3
"""Write electronics/kicad/BOM.csv, NETLIST.md and the KiCad netlist from the
verified netlist export + design.py metadata."""

import csv
import os
import re
import shutil
import xml.etree.ElementTree as ET

import design
import verify

HERE = os.path.dirname(os.path.abspath(__file__))
KDIR = os.path.abspath(os.path.join(HERE, '..'))
XML = os.path.join(KDIR, 'build', 'smartcoaster.net.xml')

MPN = {
    'ESP32-S3-MINI-1': ('ESP32-S3-MINI-1-N8R2', 'Wi-Fi/BLE SoC module, 8 MB flash, 2 MB PSRAM'),
    'HX711': ('HX711', '24-bit load-cell ADC, gain 128, 10 SPS'),
    'TP4056': ('TP4056', '1-cell Li-ion CC/CV charger, 4.2 V, 500 mA (Rprog 2.4k)'),
    'DW01A': ('DW01A', '1-cell Li-ion protection IC, SOT-23-6'),
    'FS8205A': ('FS8205A', 'dual N-MOSFET, 20 V, 6 A, SOP-8, protection pair'),
    'ME6211C33M5': ('ME6211C33M5G', '3.3 V LDO, 500 mA, 100 mV dropout, SOT-23-5'),
    'USBLC6-2SC6': ('USBLC6-2SC6', 'USB 2.0 ESD protection, 2-line, SOT-23-6'),
    'USB_C_16P': ('HRO TYPE-C-31-M-12', 'USB-C receptacle 16P, USB 2.0, 5 V sink'),
    'LOAD CELL': ('JST BM04B-SRSS-TB', '1.0 mm 4-pin, 4-wire load cell (E+/E-/S+/S-)'),
    'OLED 0.91in': ('PinHeader 1x04 2.54', '0.91in 128x32 SSD1306 I2C module header'),
    'KEY K1': ('JST B2B-PH-K-S', '2-pin, front-panel tact switch'),
    'BATT 3.7V': ('JST B2B-PH-K-S', '2-pin, LiPo 500 mAh with protection board'),
    'RESET': ('Omron B3U-1000P', 'SMD tact switch 3x4 mm'),
    'BOOT': ('Omron B3U-1000P', 'SMD tact switch 3x4 mm'),
}


PASSIVE_DESC = {
    '10uF': 'MLCC 10 µF 10 V X5R ±10% 0805',
    '1uF': 'MLCC 1 µF 16 V X5R ±10% 0603',
    '100nF': 'MLCC 100 nF 25 V X7R ±10% 0603',
    '5.1k': '厚膜 5.1 kΩ ±1% 1/10 W 0603',
    '2.4k': '厚膜 2.4 kΩ ±1% 1/10 W 0603',
    '10k': '厚膜 10 kΩ ±1% 1/10 W 0603',
    '4.7k': '厚膜 4.7 kΩ ±1% 1/10 W 0603',
    '100k': '厚膜 100 kΩ ±1% 1/10 W 0603',
    '1k': '厚膜 1 kΩ ±1% 1/10 W 0603',
    '100': '厚膜 100 Ω ±1% 1/10 W 0603',
    '47': '厚膜 47 Ω ±1% 1/10 W 0603',
}


def group_parts():
    """Group identical value+footprint parts into BOM lines."""
    parts = [dict(p) for p in design.PARTS]
    groups = {}
    order = []
    for p in parts:
        key = (p['kind'], p['value'], p['fp'])
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(p)
    return [(k, groups[k]) for k in order]


def main():
    verify.export()
    shutil.copyfile(XML, os.path.join(KDIR, 'smartcoaster', 'smartcoaster.net'))

    comps, nets = verify.read_netlist()

    # ---------------- BOM ----------------
    rows = []
    n = 0
    for key, items in group_parts():
        kind, value, fp = key
        n += 1
        refs = [p['ref'] for p in items]
        refs.sort(key=lambda r: (re.match(r'[A-Z]+', r).group(0), int(re.search(r'\d+', r).group(0))))
        mpn, desc = MPN.get(value, ('', ''))
        if not desc:
            desc = PASSIVE_DESC.get(value, '')
        note = items[0].get('note', '') if len(items) == 1 else ''
        rows.append({
            'Item': n,
            'Qty': len(items),
            'Refs': ' '.join(refs),
            'Value': value,
            'MPN': mpn,
            'Footprint': fp,
            'Description': desc,
            'Note': note if desc != note else '',
        })
    with open(os.path.join(KDIR, 'BOM.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['Item', 'Qty', 'Refs', 'Value', 'MPN',
                                          'Footprint', 'Description', 'Note'])
        w.writeheader()
        w.writerows(rows)

    # ---------------- NETLIST.md ----------------
    pin_name = {}
    for p in design.PARTS:
        pin_name[p['ref']] = p['value']
    lines = ['# SmartCoaster V1-B — 人可读连接表 (NETLIST)', '',
             '> 由 `design.py` 生成，经 `verify.py` 与 KiCad 导出的网表逐引脚比对通过。',
             '> 机器可读版本：`smartcoaster/smartcoaster.net`（KiCad XML）。', '',
             '| # | 网络 | 连接 (器件.引脚) | 说明 |', '|---|---|---|---|']
    NOTE = {
        'VBUS': 'USB 5 V（仅充电）', 'GND': '系统地 / 保护后负极 P-', '3V3': 'LDO 输出',
        'VBAT': '电池正极（保护前）', 'CELL_N': '电芯负极（保护前）', 'BAT_MID': '双 MOSFET 共漏',
        'PROT_OD': 'DW01A 放电控制', 'PROT_OC': 'DW01A 充电控制', 'PROT_VDD': 'DW01A 供电(经100Ω)',
        'PROT_CS': 'DW01A 电流检测', 'PROG': 'TP4056 充电电流设定',
        'USB_DP': 'USB D+', 'USB_DM': 'USB D-', 'USB_CC1': 'USB-C CC1', 'USB_CC2': 'USB-C CC2',
        'ESP_EN': 'ESP32 EN 复位', 'ESP_BOOT': 'GPIO0 下载模式', 'KEY_K1': '用户按键',
        'HX_DOUT': 'HX711 数据输出 (GPIO4)', 'HX_PD_SCK': 'HX711 时钟 (GPIO5)',
        'HX_S_P': '传感器 S+ (连接器侧)', 'HX_S_N': '传感器 S- (连接器侧)',
        'HX_A_P': 'HX711 INA+ (滤波后)', 'HX_A_N': 'HX711 INA- (滤波后)', 'HX_VBG': 'HX711 基准 1.25 V',
        'I2C_SDA': 'OLED SDA (GPIO8)', 'I2C_SCL': 'OLED SCL (GPIO9)',
        'VBAT_SENSE': '电池分压 → GPIO1',
    }
    for i, (name, conns) in enumerate(sorted(design.NETS.items()), start=1):
        cells = ', '.join('%s.%s' % (r, p) for r, p in conns)
        lines.append('| %d | `%s` | %s | %s |' % (i, name, cells, NOTE.get(name, '')))
    lines += ['', '## 引脚级速查（按器件）', '']
    for p in design.PARTS:
        conns = []
        for name, cs in design.NETS.items():
            for r, pin in cs:
                if r == p['ref']:
                    conns.append('%s→%s' % (pin, name))
        if p['kind'] == 'ic' or p['ref'].startswith(('J', 'U', 'SW')):
            lines.append('- **%s** (%s): %s' % (p['ref'], p['value'], ', '.join(conns)))
    with open(os.path.join(KDIR, 'NETLIST.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print('BOM lines:', len(rows), 'nets:', len(design.NETS), 'components:', len(design.PARTS))


if __name__ == '__main__':
    main()
