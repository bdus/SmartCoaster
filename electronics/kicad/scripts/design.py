"""SmartCoaster V1 (B design) — electrical design source of truth.

Nets come from electronics/pinmap.md; mechanical outline from
mechanical/square_v1/cad/square_model.py::make_pcb().

Coordinates here are *schematic* sheet coordinates (mm, origin top-left of the
paper).  PCB placement lives in gen_pcb.py.
"""

PROJECT = 'smartcoaster'
PAPER = 'A2'
TITLE = 'SmartCoaster V1 — smart coaster main board (B design)'
REV = '0.1-DRAFT'
DATE = '2026-11-04'

# ---------------------------------------------------------------------------
# Custom symbols (parts that KiCad's stock libraries do not carry)
# ---------------------------------------------------------------------------
CUSTOM_SYMBOLS = {
    # FS8205A dual N-MOSFET, SOP-8 battery-protection pair.
    # 1 S1, 2 G1, 3 S2, 4 G2, 5..8 D1/D2 (common drain, stacked on one point).
    'smartcoaster:FS8205A': '''
(symbol "FS8205A"
  (pin_names (offset 0.762))
  (exclude_from_sim no) (in_bom yes) (on_board yes)
  (property "Reference" "Q" (at 9.525 8.89 0) (effects (font (size 1.27 1.27)) (justify left)))
  (property "Value" "FS8205A" (at 9.525 6.35 0) (effects (font (size 1.27 1.27)) (justify left)))
  (property "Footprint" "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
  (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
  (property "Description" "Dual N-channel MOSFET, common drain, for DW01A battery protection" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
  (symbol "FS8205A_0_1"
    (rectangle (start -7.62 7.62) (end 7.62 -7.62) (stroke (width 0.254) (type default)) (fill (type background)))
  )
  (symbol "FS8205A_1_1"
    (pin passive line (at -12.7 5.08 0) (length 5.08) (name "S1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
    (pin input line (at -12.7 0 0) (length 5.08) (name "G1" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
    (pin passive line (at 12.7 5.08 180) (length 5.08) (name "S2" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
    (pin input line (at 12.7 0 180) (length 5.08) (name "G2" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
    (pin passive line (at 0 -12.7 90) (length 5.08) (name "D2" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
    (pin passive line (at 0 -12.7 90) (length 5.08) (name "D2" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
    (pin passive line (at 0 -12.7 90) (length 5.08) (name "D1" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
    (pin passive line (at 0 -12.7 90) (length 5.08) (name "D1" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
  )
)
''',
}

# ---------------------------------------------------------------------------
# Parts:  ref, lib, value, footprint, (x, y), rotation, kind
# kind: ic (big box), passive (2-pin), conn (connector)
# ---------------------------------------------------------------------------
PARTS = [
    # ---- USB-C input / ESD -------------------------------------------------
    dict(ref='J1', lib='Connector:USB_C_Receptacle_USB2.0_16P', value='USB_C_16P',
         fp='Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12', at=(65, 72), rot=0,
         kind='ic', mpn='HRO TYPE-C-31-M-12 (16P)',
         note='16P receptacle, USB2.0 only, 5 V sink'),
    dict(ref='U7', lib='Power_Protection:USBLC6-2SC6', value='USBLC6-2SC6',
         fp='Package_TO_SOT_SMD:SOT-23-6', at=(135, 58), rot=0, kind='ic',
         mpn='USBLC6-2SC6', note='USB ESD, 2-line + VBUS'),
    dict(ref='R9', lib='Device:R', value='5.1k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(135, 95), rot=90, kind='passive'),
    dict(ref='R10', lib='Device:R', value='5.1k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(135, 105), rot=90, kind='passive'),
    dict(ref='C1', lib='Device:C', value='10uF', fp='Capacitor_SMD:C_0805_2012Metric',
         at=(135, 118), rot=90, kind='passive', note='VBUS bulk'),

    # ---- Charger -----------------------------------------------------------
    dict(ref='U3', lib='Battery_Management:TP4056-42-ESOP8', value='TP4056',
         fp='Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.81mm',
         at=(200, 80), rot=0, kind='ic', mpn='TP4056 (ESOP-8)',
         note='1 cell Li-ion CC/CV charger, 500 mA (Rprog 2.4k)'),
    dict(ref='C3', lib='Device:C', value='10uF', fp='Capacitor_SMD:C_0805_2012Metric',
         at=(240, 60), rot=90, kind='passive', note='VBUS input'),
    dict(ref='C2', lib='Device:C', value='1uF', fp='Capacitor_SMD:C_0603_1608Metric',
         at=(240, 72), rot=90, kind='passive', note='BAT pin'),
    dict(ref='R8', lib='Device:R', value='2.4k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(240, 95), rot=90, kind='passive', note='Iprog = 1200/R = 500 mA'),

    # ---- Battery + protection ---------------------------------------------
    dict(ref='J2', lib='Connector_Generic:Conn_01x02', value='BATT 3.7V',
         fp='Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical',
         at=(200, 130), rot=0, kind='conn', mpn='JST B2B-PH-K-S',
         note='LiPo 500 mAh, JST-PH 2P'),
    dict(ref='U4', lib='Battery_Management:DW01A', value='DW01A',
         fp='Package_TO_SOT_SMD:SOT-23-6', at=(300, 90), rot=0, kind='ic',
         mpn='DW01A', note='1-cell protection IC'),
    dict(ref='U5', lib='smartcoaster:FS8205A', value='FS8205A',
         fp='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm', at=(300, 140), rot=0, kind='ic',
         mpn='FS8205A', note='dual N-MOSFET, common drain'),
    dict(ref='R11', lib='Device:R', value='100', fp='Resistor_SMD:R_0603_1608Metric',
         at=(350, 100), rot=90, kind='passive', note='DW01A VDD RC filter'),
    dict(ref='C4', lib='Device:C', value='100nF', fp='Capacitor_SMD:C_0603_1608Metric',
         at=(350, 112), rot=90, kind='passive'),
    dict(ref='R12', lib='Device:R', value='1k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(350, 124), rot=90, kind='passive', note='DW01A current-sense'),

    # ---- 3.3 V LDO --------------------------------------------------------
    dict(ref='U6', lib='Regulator_Linear:ME6211C33M5', value='ME6211C33M5',
         fp='Package_TO_SOT_SMD:SOT-23-5', at=(400, 60), rot=0, kind='ic',
         mpn='ME6211C33M5G', note='3.3 V 500 mA LDO, 100 mV dropout @ 300 mA'),
    dict(ref='C5', lib='Device:C', value='1uF', fp='Capacitor_SMD:C_0603_1608Metric',
         at=(430, 50), rot=90, kind='passive', note='LDO input'),
    dict(ref='C6', lib='Device:C', value='1uF', fp='Capacitor_SMD:C_0603_1608Metric',
         at=(430, 62), rot=90, kind='passive', note='LDO output'),
    dict(ref='C7', lib='Device:C', value='10uF', fp='Capacitor_SMD:C_0805_2012Metric',
         at=(430, 74), rot=90, kind='passive', note='3V3 bulk'),

    # ---- MCU --------------------------------------------------------------
    dict(ref='U1', lib='RF_Module:ESP32-S3-MINI-1', value='ESP32-S3-MINI-1',
         fp='RF_Module:ESP32-S2-MINI-1', at=(520, 150), rot=0, kind='ic',
         mpn='ESP32-S3-MINI-1-N8R2',
         note='8 MB flash, 2 MB PSRAM, PCB antenna; MINI-1 land pattern (PROVISIONAL)'),
    dict(ref='R1', lib='Device:R', value='10k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(455, 96), rot=90, kind='passive', note='EN pull-up'),
    dict(ref='C9', lib='Device:C', value='1uF', fp='Capacitor_SMD:C_0603_1608Metric',
         at=(455, 108), rot=90, kind='passive', note='EN RC delay'),
    dict(ref='SW2', lib='Switch:SW_Push', value='RESET',
         fp='Button_Switch_SMD:SW_SPST_B3U-1000P', at=(470, 126), rot=0, kind='ic'),
    dict(ref='R2', lib='Device:R', value='10k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(455, 170), rot=90, kind='passive', note='BOOT(IO0) pull-up'),
    dict(ref='SW3', lib='Switch:SW_Push', value='BOOT',
         fp='Button_Switch_SMD:SW_SPST_B3U-1000P', at=(470, 188), rot=0, kind='ic'),
    dict(ref='C10', lib='Device:C', value='100nF', fp='Capacitor_SMD:C_0603_1608Metric',
         at=(562, 78), rot=90, kind='passive', note='3V3 decoupling'),

    # ---- Sensor front-end -------------------------------------------------
    dict(ref='U2', lib='Analog_ADC:HX711', value='HX711',
         fp='Package_SO:SOIC-16_3.9x9.9mm_P1.27mm', at=(120, 330), rot=0, kind='ic',
         mpn='HX711 (SOP-16)', note='24-bit load-cell ADC, gain 128, 10 Hz'),
    dict(ref='R5', lib='Device:R', value='10k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(165, 372), rot=90, kind='passive', note='DOUT pull-down'),
    dict(ref='C11', lib='Device:C', value='100nF', fp='Capacitor_SMD:C_0603_1608Metric',
         at=(168, 305), rot=90, kind='passive', note='AVDD decoupling'),
    dict(ref='C12', lib='Device:C', value='1uF', fp='Capacitor_SMD:C_0603_1608Metric',
         at=(168, 317), rot=90, kind='passive', note='AVDD bulk'),
    dict(ref='C14', lib='Device:C', value='100nF', fp='Capacitor_SMD:C_0603_1608Metric',
         at=(168, 329), rot=90, kind='passive', note='VBG reference bypass'),
    dict(ref='C15', lib='Device:C', value='100nF', fp='Capacitor_SMD:C_0603_1608Metric',
         at=(168, 341), rot=90, kind='passive', note='DVDD decoupling'),
    dict(ref='C16', lib='Device:C', value='100nF', fp='Capacitor_SMD:C_0603_1608Metric',
         at=(100, 292), rot=90, kind='passive', note='A+/A- differential filter'),
    dict(ref='R25', lib='Device:R', value='1k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(82, 265), rot=90, kind='passive', note='A+ input filter'),
    dict(ref='R26', lib='Device:R', value='1k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(82, 278), rot=90, kind='passive', note='A- input filter'),
    dict(ref='J3', lib='Connector_Generic:Conn_01x04', value='LOAD CELL',
         fp='Connector_JST:JST_SH_BM04B-SRSS-TB_1x04-1MP_P1.00mm_Vertical',
         at=(42, 262), rot=0, kind='conn', mpn='JST BM04B-SRSS-TB',
         note='E+ / E- / S+ / S- (4-wire cell)'),

    # ---- UI ---------------------------------------------------------------
    dict(ref='J4', lib='Connector_Generic:Conn_01x04', value='OLED 0.91"',
         fp='Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
         at=(200, 270), rot=0, kind='conn', mpn='PinHeader 1x04 2.54',
         note='GND / 3V3 / SCL / SDA (verify module order)'),
    dict(ref='R3', lib='Device:R', value='4.7k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(255, 265), rot=90, kind='passive', note='I2C SDA pull-up'),
    dict(ref='R4', lib='Device:R', value='4.7k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(255, 277), rot=90, kind='passive', note='I2C SCL pull-up'),
    dict(ref='J5', lib='Connector_Generic:Conn_01x02', value='KEY K1',
         fp='Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical',
         at=(200, 300), rot=0, kind='conn', mpn='JST B2B-PH-K-S',
         note='front-panel tact switch (shell mounted)'),
    dict(ref='D1', lib='Device:LED_RGB', value='RGB', fp='LED_SMD:LED_RGB_5050-6',
         at=(320, 270), rot=0, kind='ic'),
    dict(ref='D2', lib='Device:LED_RGB', value='RGB', fp='LED_SMD:LED_RGB_5050-6',
         at=(320, 320), rot=0, kind='ic'),
    dict(ref='Q1', lib='Transistor_FET:2N7002', value='2N7002',
         fp='Package_TO_SOT_SMD:SOT-23', at=(380, 262), rot=0, kind='ic'),
    dict(ref='Q2', lib='Transistor_FET:2N7002', value='2N7002',
         fp='Package_TO_SOT_SMD:SOT-23', at=(380, 290), rot=0, kind='ic'),
    dict(ref='Q3', lib='Transistor_FET:2N7002', value='2N7002',
         fp='Package_TO_SOT_SMD:SOT-23', at=(380, 318), rot=0, kind='ic'),
    dict(ref='R13', lib='Device:R', value='100', fp='Resistor_SMD:R_0603_1608Metric',
         at=(350, 250), rot=90, kind='passive', note='Halo R gate'),
    dict(ref='R14', lib='Device:R', value='100', fp='Resistor_SMD:R_0603_1608Metric',
         at=(350, 278), rot=90, kind='passive', note='Halo G gate'),
    dict(ref='R15', lib='Device:R', value='100', fp='Resistor_SMD:R_0603_1608Metric',
         at=(350, 306), rot=90, kind='passive', note='Halo B gate'),
    dict(ref='R16', lib='Device:R', value='100k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(410, 262), rot=90, kind='passive', note='gate pull-down'),
    dict(ref='R17', lib='Device:R', value='100k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(410, 290), rot=90, kind='passive', note='gate pull-down'),
    dict(ref='R18', lib='Device:R', value='100k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(410, 318), rot=90, kind='passive', note='gate pull-down'),
    dict(ref='R19', lib='Device:R', value='47', fp='Resistor_SMD:R_0603_1608Metric',
         at=(250, 320), rot=90, kind='passive', note='D1 red'),
    dict(ref='R20', lib='Device:R', value='47', fp='Resistor_SMD:R_0603_1608Metric',
         at=(250, 332), rot=90, kind='passive', note='D1 green'),
    dict(ref='R21', lib='Device:R', value='47', fp='Resistor_SMD:R_0603_1608Metric',
         at=(250, 344), rot=90, kind='passive', note='D1 blue'),
    dict(ref='R22', lib='Device:R', value='47', fp='Resistor_SMD:R_0603_1608Metric',
         at=(250, 356), rot=90, kind='passive', note='D2 red'),
    dict(ref='R23', lib='Device:R', value='47', fp='Resistor_SMD:R_0603_1608Metric',
         at=(250, 368), rot=90, kind='passive', note='D2 green'),
    dict(ref='R24', lib='Device:R', value='47', fp='Resistor_SMD:R_0603_1608Metric',
         at=(250, 380), rot=90, kind='passive', note='D2 blue'),

    # ---- Test points ------------------------------------------------------
    *[dict(ref='TP%d' % (i + 1), lib='Connector:TestPoint', value=v,
           fp='TestPoint:TestPoint_Pad_D1.5mm', at=(38, 300 + 16 * i), rot=0,
           kind='ic', note='probe pad: ' + v)
      for i, v in enumerate(['AVDD', 'AGND', 'A+', 'A-', 'DOUT', 'PD_SCK'])],

    # ---- Battery sense ----------------------------------------------------
    dict(ref='R6', lib='Device:R', value='100k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(488, 330), rot=90, kind='passive', note='VBAT divider top'),
    dict(ref='R7', lib='Device:R', value='100k', fp='Resistor_SMD:R_0603_1608Metric',
         at=(488, 342), rot=90, kind='passive', note='VBAT divider bottom'),
    dict(ref='C13', lib='Device:C', value='100nF', fp='Capacitor_SMD:C_0603_1608Metric',
         at=(488, 354), rot=90, kind='passive', note='ADC anti-alias'),
]


def _esp32_gnd():
    return ['1', '2', '42', '43'] + [str(i) for i in range(46, 66)]


# ---------------------------------------------------------------------------
# Nets: name -> list of (ref, pin)
# ---------------------------------------------------------------------------
NETS = {
    'VBUS': [('J1', 'A4'), ('J1', 'A9'), ('J1', 'B4'), ('J1', 'B9'),
             ('U7', '5'), ('U3', '4'), ('U3', '8'), ('C3', '1'), ('C1', '1')],
    'GND': [('J1', 'A1'), ('J1', 'A12'), ('J1', 'B1'), ('J1', 'B12'),
            ('J1', 'S1'),
            ('U7', '2'), ('U3', '3'), ('U3', '9'), ('U3', '1'),
            ('C3', '2'), ('C1', '2'), ('C2', '2'), ('R8', '2'),
            ('U5', '3'), ('R12', '2'),
            ('U6', '2'), ('C5', '2'), ('C6', '2'), ('C7', '2'),
            ('R9', '2'), ('R10', '2'),
            ('C9', '2'), ('C10', '2'), ('SW2', '2'), ('SW3', '2'),
            ('U2', '5'), ('U2', '4'), ('U2', '9'), ('U2', '10'), ('U2', '14'),
            ('U2', '15'), ('C11', '2'), ('C12', '2'), ('C14', '2'), ('C15', '2'),
            ('R5', '2'), ('J3', '2'), ('TP2', '1'),
            ('J4', '1'), ('J5', '2'),
            ('R16', '2'), ('R17', '2'), ('R18', '2'),
            ('Q1', '2'), ('Q2', '2'), ('Q3', '2'),
            ('R7', '2'), ('C13', '2')] +
            [('U1', p) for p in _esp32_gnd()],
    '3V3': [('U6', '5'), ('C6', '1'), ('C7', '1'),
            ('U1', '3'), ('C10', '1'), ('R1', '1'), ('R2', '1'),
            ('R3', '1'), ('R4', '1'),
            ('U2', '1'), ('U2', '3'), ('U2', '16'), ('C11', '1'), ('C12', '1'),
            ('C15', '1'), ('TP1', '1'),
            ('J3', '1'), ('J4', '2'),
            ('R19', '1'), ('R20', '1'), ('R21', '1'),
            ('R22', '1'), ('R23', '1'), ('R24', '1')],
    'VBAT': [('U3', '5'), ('J2', '1'), ('C2', '1'), ('U6', '1'), ('U6', '3'),
             ('R11', '1'), ('R6', '1'), ('C5', '1')],
    'CELL_N': [('J2', '2'), ('U5', '1'), ('U4', '6'), ('C4', '2')],
    'BAT_MID': [('U5', '5'), ('U5', '6'), ('U5', '7'), ('U5', '8')],
    'PROT_OD': [('U4', '1'), ('U5', '2')],
    'PROT_OC': [('U4', '3'), ('U5', '4')],
    'PROT_VDD': [('U4', '5'), ('R11', '2'), ('C4', '1')],
    'PROT_CS': [('U4', '2'), ('R12', '1')],
    'PROG': [('U3', '2'), ('R8', '1')],

    'USB_DP': [('J1', 'A6'), ('J1', 'B6'), ('U7', '1'), ('U7', '6'), ('U1', '24')],
    'USB_DM': [('J1', 'A7'), ('J1', 'B7'), ('U7', '3'), ('U7', '4'), ('U1', '23')],
    'USB_CC1': [('J1', 'A5'), ('R9', '1')],
    'USB_CC2': [('J1', 'B5'), ('R10', '1')],

    'ESP_EN': [('U1', '45'), ('R1', '2'), ('C9', '1'), ('SW2', '1')],
    'ESP_BOOT': [('U1', '4'), ('R2', '2'), ('SW3', '1')],
    'KEY_K1': [('U1', '14'), ('J5', '1')],

    'HX_DOUT': [('U2', '12'), ('U1', '8'), ('R5', '1'), ('TP5', '1')],
    'HX_PD_SCK': [('U2', '11'), ('U1', '9'), ('TP6', '1')],
    'HX_S_P': [('J3', '3'), ('R25', '1')],
    'HX_S_N': [('J3', '4'), ('R26', '1')],
    'HX_A_P': [('U2', '8'), ('R25', '2'), ('C16', '1'), ('TP3', '1')],
    'HX_A_N': [('U2', '7'), ('R26', '2'), ('C16', '2'), ('TP4', '1')],
    'HX_VBG': [('U2', '6'), ('C14', '1')],

    'I2C_SDA': [('U1', '12'), ('J4', '4'), ('R3', '2')],
    'I2C_SCL': [('U1', '13'), ('J4', '3'), ('R4', '2')],

    'HALO_R_PWM': [('U1', '15'), ('R13', '1')],
    'HALO_G_PWM': [('U1', '16'), ('R14', '1')],
    'HALO_B_PWM': [('U1', '17'), ('R15', '1')],
    'HALO_R_GATE': [('R13', '2'), ('Q1', '1'), ('R16', '1')],
    'HALO_G_GATE': [('R14', '2'), ('Q2', '1'), ('R17', '1')],
    'HALO_B_GATE': [('R15', '2'), ('Q3', '1'), ('R18', '1')],
    'LED_R_K': [('D1', '1'), ('D2', '1'), ('Q1', '3')],
    'LED_G_K': [('D1', '2'), ('D2', '2'), ('Q2', '3')],
    'LED_B_K': [('D1', '3'), ('D2', '3'), ('Q3', '3')],
    'LED1_RA': [('R19', '2'), ('D1', '6')],
    'LED1_GA': [('R20', '2'), ('D1', '5')],
    'LED1_BA': [('R21', '2'), ('D1', '4')],
    'LED2_RA': [('R22', '2'), ('D2', '6')],
    'LED2_GA': [('R23', '2'), ('D2', '5')],
    'LED2_BA': [('R24', '2'), ('D2', '4')],

    'VBAT_SENSE': [('U1', '5'), ('R6', '2'), ('R7', '1'), ('C13', '1')],
}

# Nets that need a PWR_FLAG because nothing on them is a power output.
PWR_FLAGS = ['GND', 'VBUS', 'CELL_N', 'PROT_VDD']

# Explicit no-connects for pins that would otherwise float (ERC "pin not
# connected"); everything not listed in NETS and not here is auto-NC'd by the
# generator and cross-checked in verify.py.
NC_PINS = {
    ('J1', 'A8'), ('J1', 'B8'),          # SBU1/SBU2
    ('U3', '6'), ('U3', '7'),            # STDBY / CHRG (no status LEDs in V1)
    ('U2', '2'), ('U2', '13'),              # BASE / XO
}

BLOCKS = [
    ('USB-C 5 V input, CC resistors, ESD', 30, 30, 175, 135),
    ('Li-ion charger + protection + 3.3 V LDO', 180, 30, 460, 165),
    ('ESP32-S3-MINI-1', 440, 40, 592, 215),
    ('HX711 load-cell front-end (chip-level, 3.3 V, no internal regulator)', 20, 235, 190, 400),
    ('UI: OLED header, key, RGB halo', 196, 240, 445, 400),
    ('Battery voltage sense', 458, 305, 585, 375),
]
