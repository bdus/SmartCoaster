#!/usr/bin/env python3
"""Compare through-slot vs 0.7 mm shallow-cavity cases (same C3D10 h=0.30 mesh)."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

TH = 'results_h030_c3d10.json'
SH = 'results_shallow07_h030_c3d10.json'
th = json.load(open(TH)); sh = json.load(open(SH))

def g(d, k):
    return d['results'][k]

fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.6))
labels = ['through\nU-slot', '0.7 mm\nshallow cavity']
colors = ['#3b6ea5', '#c46a1b']
x = np.arange(2); w = 0.34

# (a) centre displacement
u5 = [abs(g(th, 'center_uz_mean_mm')), abs(g(sh, 'center_uz_mean_mm'))]
u1 = [v * 0.2 for v in u5]
b1 = axes[0].bar(x - w/2, u5, w, color=colors, label='5 kg')
b2 = axes[0].bar(x + w/2, u1, w, color=colors, alpha=0.45, hatch='//', label='1 kg (scaled)')
for bars in (b1, b2):
    for b in bars:
        axes[0].annotate(f'{b.get_height():.3f}', (b.get_x() + b.get_width()/2, b.get_height()),
                         ha='center', va='bottom', fontsize=9)
axes[0].set_xticks(x); axes[0].set_xticklabels(labels)
axes[0].set_ylabel('centre |Uz| (mm)'); axes[0].set_title('(a) centre deflection')
axes[0].legend(fontsize=8); axes[0].grid(axis='y', alpha=0.3)

# (b) stress
vm_all = [g(th, 'max_vm_mpa'), g(sh, 'max_vm_mpa')]
vm_nc = [g(th, 'max_vm_free_no_slotcorner_mpa'), g(sh, 'max_vm_free_no_slotcorner_mpa')]
b3 = axes[1].bar(x - w/2, vm_all, w, color=colors, label='absolute max (incl. sharp corner)')
b4 = axes[1].bar(x + w/2, vm_nc, w, color=colors, alpha=0.45, hatch='//', label='max away from sharp corner')
for bars in (b3, b4):
    for b in bars:
        axes[1].annotate(f'{b.get_height():.0f}', (b.get_x() + b.get_width()/2, b.get_height()),
                         ha='center', va='bottom', fontsize=9)
axes[1].set_xticks(x); axes[1].set_xticklabels(labels)
axes[1].set_ylabel('von Mises (MPa)'); axes[1].set_title('(b) peak stress, 5 kg')
axes[1].legend(fontsize=7); axes[1].grid(axis='y', alpha=0.3)

# (c) per-corner reaction split
rt = th['reactions']['per_corner_fz_N']; rs = sh['reactions']['per_corner_fz_N']
corners = ['(+14,+14)', '(-14,+14)', '(+14,-14)', '(-14,-14)']
xx = np.arange(4); ww = 0.36
b5 = axes[2].bar(xx - ww/2, rt, ww, color=colors[0], label='through')
b6 = axes[2].bar(xx + ww/2, rs, ww, color=colors[1], label='shallow 0.7')
for bars in (b5, b6):
    for b in bars:
        axes[2].annotate(f'{b.get_height():.1f}', (b.get_x() + b.get_width()/2, b.get_height()),
                         ha='center', va='bottom', fontsize=8)
axes[2].set_xticks(xx); axes[2].set_xticklabels(corners, fontsize=8)
axes[2].set_ylabel('reaction Fz (N)'); axes[2].set_title('(c) load share per screw, 5 kg')
axes[2].legend(fontsize=8); axes[2].grid(axis='y', alpha=0.3)

fig.suptitle('HY928D v2, 5 kg: through-slot vs 0.7 mm shallow cavity (C3D10 h=0.30 mm)', fontsize=12)
fig.tight_layout()
fig.savefig('figs/fig_compare.png', dpi=220)
print('wrote figs/fig_compare.png')

summary = {
    'through': {'file': TH, 'center_uz_5kg_mm': u5[0], 'max_vm_mpa': vm_all[0],
                'max_vm_no_slotcorner_mpa': vm_nc[0],
                'per_corner_fz_N': rt},
    'shallow07': {'file': SH, 'center_uz_5kg_mm': u5[1], 'max_vm_mpa': vm_all[1],
                  'max_vm_no_slotcorner_mpa': vm_nc[1],
                  'per_corner_fz_N': rs},
    'stiffness_ratio_through_over_shallow': u5[0] / u5[1],
    'stress_ratio_through_over_shallow': vm_nc[0] / vm_nc[1],
}
json.dump(summary, open('comparison_slot_vs_shallow.json', 'w'), indent=2)
print(json.dumps(summary, indent=2))
