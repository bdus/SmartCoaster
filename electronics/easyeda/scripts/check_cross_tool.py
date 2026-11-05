#!/usr/bin/env python3
"""Cross-tool validation: KiCad 9 (main delivery) vs EasyEDA Pro (second implementation).

Two tools cannot open the same *native* project file (EasyEDA imports KiCad 5.x only,
KiCad cannot read .eprj3), so the cross-check is done at the **data contract** level:
  X1 netlist:  KiCad XML netlist  vs  the netlist exported by the live EasyEDA client
  X2 placement: KiCad footprint x/y/angle vs the .epcb2 COMPONENT records
  X3 pads:     KiCad pad absolute positions vs the .epcb2 embedded-footprint pads
  X4 copper:   KiCad tracks/vias vs the .epcb2 LINE/VIA records
  X5 outline:  the mechanical C-ring bbox/size in .epcb2 vs the frozen 93.2 mm design
Exit 1 on any mismatch beyond tolerance.

Run with /data/Documents/tools/sim-venv/bin/python (pcbnew 9 + shapely-free).
"""
import json, math, sys, xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
PCB = ROOT / 'electronics' / 'kicad' / 'smartcoaster' / 'smartcoaster_2l.kicad_pcb'
NET = ROOT / 'electronics' / 'kicad' / 'smartcoaster' / 'smartcoaster.net'
EPCB = sorted((HERE / 'smartcoaster_easyeda' / 'pcb').glob('*.epcb2'))[0]
CLIENT_NET = HERE / 'inputs' / 'client_netlist.json'
OUT = HERE / 'reports' / 'cross_tool.json'
MM = 0.0254
OFF = 46.6
TOL = 0.02      # mil
def eda(x_mm, y_mm):
    return ((x_mm + OFF) / MM, (-y_mm + OFF) / MM)

def kicad_netlist():
    root = ET.parse(str(NET)).getroot()
    pins = {}
    for n in root.find('nets'):
        name = n.get('name')
        for node in n.findall('node'):
            ref, num = node.get('ref'), node.get('pin')
            pins.setdefault(ref, {})[num] = None if name.startswith('unconnected-') else name.lstrip('/')
    return pins

def client_netlist():
    d = json.loads(CLIENT_NET.read_text())
    out = {}
    for p in d.get('parts', []):
        out[p['ref']] = {str(k): (None if v in ('NC', '', None) else v) for k, v in (p.get('pins') or {}).items()}
    return out

def parse_pcb():
    docs = []
    cur = None
    for line in EPCB.read_text().split('\n'):
        if '"type":"DOCHEAD"' in line:
            body = line.split('||', 1)[1].strip().rstrip('|')
            try: b = json.loads(body)
            except Exception: b = {}
            cur = {'docType': b.get('docType'), 'uuid': b.get('uuid'), 'title': None, 'pads': [], 'recs': []}
            docs.append(cur)
            continue
        if cur is None or '||' not in line:
            continue
        h, b = line.split('||', 1)
        try:
            hh = json.loads(h); bb = json.loads(b.strip().rstrip('|'))
        except Exception:
            continue
        cur['recs'].append((hh, bb))
        if hh.get('type') == 'META' and bb.get('title'):
            cur['title'] = bb['title']
        if hh.get('type') == 'PAD':
            cur['pads'].append(bb)
    return docs

def main():
    import pcbnew
    board = pcbnew.LoadBoard(str(PCB))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    docs = parse_pcb()
    main_doc = [d for d in docs if d['docType'] == 'PCB'][0]
    fp_docs = {d['uuid']: d for d in docs if d['docType'] == 'FOOTPRINT'}
    ref_by_comp, comps, pad_nets = {}, {}, {}
    for hh, bb in main_doc['recs']:
        if hh.get('type') == 'ATTR' and bb.get('key') == 'Designator' and bb.get('parentId'):
            ref_by_comp[bb['parentId']] = bb.get('value')
        elif hh.get('type') == 'COMPONENT':
            comps[hh['id']] = bb
        elif hh.get('type') == 'PAD_NET':
            try: p = json.loads(hh['id'])
            except Exception: continue
            if isinstance(p, list) and p and p[0] == 'PAD_NET':
                pad_nets[(p[1], str(p[2]), p[3])] = bb.get('padNet', '')
    errors, warnings = [], []

    # X1 netlist
    ki = kicad_netlist(); cl = client_netlist()
    x1_pins = x1_nets = 0
    ki_nets = set()
    for ref, pins in ki.items():
        if ref not in cl:
            errors.append({'code': 'X1', 'ref': ref, 'detail': 'missing in client netlist'}); continue
        cp = cl[ref]
        for num, net in pins.items():
            if net is None:
                continue
            x1_pins += 1; ki_nets.add(net)
            got = cp.get(num)
            if got != net:
                errors.append({'code': 'X1', 'ref': ref, 'pin': num, 'kicad': net, 'client': got})
    x1_nets = len(ki_nets)
    extra = [(r, n) for r, pins in cl.items() if r in ki for n, net in pins.items() if net is not None and n not in ki[r]]
    for ref, num in extra[:10]:
        errors.append({'code': 'X1', 'ref': ref, 'pin': num, 'detail': 'connected in EasyEDA but not in KiCad'})

    # X2 placement / X3 pads
    max_place = 0.0; ncomp = 0
    for ref, fp in fps.items():
        # component
        cid = next((cid for cid, c in comps.items() if ref_by_comp.get(cid) == ref), None)
        if not cid:
            errors.append({'code': 'X2', 'ref': ref, 'detail': 'no COMPONENT in .epcb2'}); continue
        bx, by = eda(fp.GetPosition().x / 1e6, fp.GetPosition().y / 1e6)
        dx = abs(comps[cid]['x'] - bx); dy = abs(comps[cid]['y'] - by)
        max_place = max(max_place, dx, dy); ncomp += 1
        if dx > TOL or dy > TOL:
            errors.append({'code': 'X2', 'ref': ref, 'dx': dx, 'dy': dy})
        if abs(((comps[cid].get('angle', 0) - fp.GetOrientationDegrees()) + 180) % 360 - 180) > 0.01:
            errors.append({'code': 'X2', 'ref': ref, 'angle': comps[cid].get('angle'), 'kicad': fp.GetOrientationDegrees()})
        # pads
        fpattr = next((bb for hh, bb in main_doc['recs'] if hh.get('type') == 'ATTR'
                       and bb.get('key') == 'Footprint' and bb.get('parentId') == cid), None)
        doc = fp_docs.get(fpattr['value']) if fpattr else None
        if not doc:
            errors.append({'code': 'X3', 'ref': ref, 'detail': 'footprint doc missing'}); continue
        ang = math.radians(comps[cid].get('angle', 0))
        for pad in doc['pads']:
            num = str(pad.get('num'))
            lx, ly = pad['centerX'], pad['centerY']
            ax = comps[cid]['x'] + lx * math.cos(ang) - ly * math.sin(ang)
            ay = comps[cid]['y'] + lx * math.sin(ang) + ly * math.cos(ang)
            # all KiCad pads with this number, pick nearest
            knum = '' if num == 'MH' else num
            cands = [p for p in fp.Pads() if str(p.GetNumber()) == knum]
            if not cands:
                errors.append({'code': 'X3', 'ref': ref, 'pad': num, 'detail': 'not in KiCad footprint'}); continue
            best = min(cands, key=lambda p: (lambda e: (e[0]-ax)**2 + (e[1]-ay)**2)(eda(p.GetPosition().x/1e6, p.GetPosition().y/1e6)))
            ex, ey = eda(best.GetPosition().x / 1e6, best.GetPosition().y / 1e6)
            if max(abs(ex-ax), abs(ey-ay)) > TOL:
                errors.append({'code': 'X3', 'ref': ref, 'pad': num, 'dx': ax-ex, 'dy': ay-ey})

    # X4 copper
    ki_tracks = []
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            x, y = eda(t.GetPosition().x/1e6, t.GetPosition().y/1e6)
            ki_tracks.append(('via', round(x, 1), round(y, 1), round(t.GetDrillValue()/1e6/MM, 1), round(t.GetWidth(pcbnew.F_Cu)/1e6/MM, 1), t.GetNetname()))
        else:
            x1, y1 = eda(t.GetStart().x/1e6, t.GetStart().y/1e6)
            x2, y2 = eda(t.GetEnd().x/1e6, t.GetEnd().y/1e6)
            layer = 1 if t.GetLayer() == pcbnew.F_Cu else 2
            ki_tracks.append(('line', round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1), round(t.GetWidth()/1e6/MM, 1), layer, t.GetNetname()))
    ep_tracks = []
    for hh, bb in main_doc['recs']:
        if hh.get('type') == 'LINE':
            ep_tracks.append(('line', round(bb['startX'], 1), round(bb['startY'], 1), round(bb['endX'], 1), round(bb['endY'], 1), round(bb['width'], 1), bb['layerId'], bb['netName']))
        elif hh.get('type') == 'VIA':
            ep_tracks.append(('via', round(bb['centerX'], 1), round(bb['centerY'], 1), round(bb['holeDiameter'], 1), round(bb['viaDiameter'], 1), bb['netName']))
    def same(a, b):
        if a[0] != b[0]:
            return False
        if a[-1] != b[-1]:
            return False
        if a[0] == 'line' and a[6] != b[6]:
            return False
        nums_a = [v for v in a[1:-1] if isinstance(v, (int, float))]
        nums_b = [v for v in b[1:-1] if isinstance(v, (int, float))]
        return len(nums_a) == len(nums_b) and all(abs(x - y) <= 0.16 for x, y in zip(nums_a, nums_b))
    used = set()
    unmatched_k = []
    for a in ki_tracks:
        hit = next((j for j, b in enumerate(ep_tracks) if j not in used and same(a, b)), None)
        if hit is None:
            unmatched_k.append(a)
        else:
            used.add(hit)
    unmatched_e = [b for j, b in enumerate(ep_tracks) if j not in used]
    if unmatched_k or unmatched_e:
        errors.append({'code': 'X4', 'detail': 'copper records differ beyond tolerance',
                       'kicad_only_count': len(unmatched_k), 'easyeda_only_count': len(unmatched_e),
                       'kicad_only': unmatched_k[:5], 'easyeda_only': unmatched_e[:5]})

    # X5 outline
    outline = next((bb for hh, bb in main_doc['recs'] if hh.get('type') == 'POLY' and bb.get('polyType') == 'BOARD_OUTLINE'), None)
    xs = [p for p in (outline or {}).get('path', []) if isinstance(p, (int, float))][0::2]
    ys = [p for p in (outline or {}).get('path', []) if isinstance(p, (int, float))][1::2]
    w = max(xs) - min(xs); h = max(ys) - min(ys)
    exp = 93.2 / MM
    x5 = abs(w - exp) <= 0.2 and abs(h - exp) <= 0.2
    if not x5:
        errors.append({'code': 'X5', 'w': w, 'h': h, 'expected': exp})

    summary = {
        'method': 'data-contract cross-check (not a shared native project file)',
        'X1_netlist': {'ok': not any(e['code'] == 'X1' for e in errors), 'connected_pins': x1_pins, 'nets': x1_nets},
        'X2_placement': {'ok': not any(e['code'] == 'X2' for e in errors), 'components': ncomp, 'max_error_mil': round(max_place, 4)},
        'X3_pads': {'ok': not any(e['code'] == 'X3' for e in errors), 'pads': sum(len(d['pads']) for d in fp_docs.values())},
        'X4_copper': {'ok': not any(e['code'] == 'X4' for e in errors), 'records': len(ep_tracks)},
        'X5_outline': {'ok': x5, 'w_mil': round(w, 1), 'h_mil': round(h, 1)},
        'errors': errors,
        'warnings': warnings,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
    print(f"X1 netlist {x1_pins} pins / {x1_nets} nets {'OK' if summary['X1_netlist']['ok'] else 'FAIL'}")
    print(f"X2 placement {ncomp} comps max err {summary['X2_placement']['max_error_mil']} mil {'OK' if summary['X2_placement']['ok'] else 'FAIL'}")
    print(f"X3 pads {'OK' if summary['X3_pads']['ok'] else 'FAIL'} | X4 copper {'OK' if summary['X4_copper']['ok'] else 'FAIL'} "
          f"| X5 outline {summary['X5_outline']['w_mil']}×{summary['X5_outline']['h_mil']} mil {'OK' if x5 else 'FAIL'}")
    if errors:
        print(f"CROSS-TOOL FAIL: {len(errors)} error(s)")
        for e in errors[:10]:
            print('  ', e)
        sys.exit(1)
    print('CROSS-TOOL OK: KiCad and EasyEDA agree on netlist, placement, pads, copper and outline')

if __name__ == '__main__':
    main()
