#!/usr/bin/env python3
"""Consolidate the HY928D S1 FEA results into results.json."""
import json, os

def load(f):
    return json.load(open(f)) if os.path.exists(f) else None

P = load('results_h028_c3d10.json')
C30 = load('results_h030_c3d10.json')
C35 = load('results_h035_c3d10.json')
L20 = load('results_h020_c3d4.json')
L15 = load('results_h015_c3d4.json')
SH = load('results_shallow07_h030_c3d10.json')
Q28 = load('mesh_h028_c3d10_quality.json')
Q30 = load('mesh_h030_c3d10_quality.json')
Q35 = load('mesh_h035_c3d10_quality.json')
QSH = load('mesh_shallow07_h030_c3d10_quality.json')
Q20 = load('mesh_h020_c3d10_quality.json')
SETS28 = load('case_h028_c3d10_5kg.sets.json')
SETS30 = load('case_h030_c3d10_5kg.sets.json')
SETS1 = load('case_h030_c3d10_1kg.sets.json')
CMP = load('comparison_slot_vs_shallow.json')

def pct(a, b):
    return 100.0 * (a - b) / b

conv = {
    'C3D10_h035_vs_h030': {
        'center_uz_diff_pct': pct(C30['results']['center_uz_mean_mm'], C35['results']['center_uz_mean_mm']),
        'max_abs_u_diff_pct': pct(C30['results']['max_abs_u_mm'], C35['results']['max_abs_u_mm']),
        'max_vm_diff_pct': pct(C30['results']['max_vm_mpa'], C35['results']['max_vm_mpa']),
        'max_vm_no_slotcorner_diff_pct': pct(C30['results']['max_vm_free_no_slotcorner_mpa'],
                                             C35['results']['max_vm_free_no_slotcorner_mpa']),
        'note': 'center displacement is converged; the sharp-corner peak is not (singularity)',
    },
    'C3D10_h030_vs_h028': {
        'center_uz_diff_pct': pct(P['results']['center_uz_mean_mm'], C30['results']['center_uz_mean_mm']),
        'max_abs_u_diff_pct': pct(P['results']['max_abs_u_mm'], C30['results']['max_abs_u_mm']),
        'max_vm_diff_pct': pct(P['results']['max_vm_mpa'], C30['results']['max_vm_mpa']),
        'max_vm_no_slotcorner_diff_pct': pct(P['results']['max_vm_free_no_slotcorner_mpa'],
                                             C30['results']['max_vm_free_no_slotcorner_mpa']),
    },
    'C3D4_h020_vs_h015': {
        'center_uz_diff_pct': pct(L15['results']['center_uz_mean_mm'], L20['results']['center_uz_mean_mm']),
        'max_abs_u_diff_pct': pct(L15['results']['max_abs_u_mm'], L20['results']['max_abs_u_mm']),
        'max_vm_no_slotcorner_diff_pct': pct(L15['results']['max_vm_free_no_slotcorner_mpa'],
                                             L20['results']['max_vm_free_no_slotcorner_mpa']),
        'note': 'linear tets remain ~8% stiffer than the converged C3D10 result even at h=0.15',
    },
    'C3D10_h030_vs_C3D4_h015': {
        'center_uz_diff_pct': pct(L15['results']['center_uz_mean_mm'], C30['results']['center_uz_mean_mm']),
        'note': 'element-type sensitivity: linear tets are too stiff for this bending-dominated plate',
    },
    'failed_C3D10_runs': [
        {'mesh': 'mesh_h025_c3d10.msh', 'nodes': 413814, 'tets': 252459, 'dof': 1241442,
         'result': 'SIGSEGV (exit 139) after 4m44s during SPOOLES factorization; no result'},
        {'mesh': 'mesh_h020_c3d10.msh', 'nodes': 731936, 'tets': 460629, 'dof': 2195808,
         'result': 'SIGSEGV (exit 139) after 13m56s during SPOOLES factorization; no result'},
    ],
    'verdict': 'C3D10 h=0.28 is converged for displacements (<0.1% vs h=0.30/0.35) and for the '
               'non-singular peak stress (~2%). Finer C3D10 meshes exceed the practical SPOOLES '
               'limit of this ccx build and were not used.',
}

res = {
    'meta': {
        'project': 'SmartCoaster / HY928D 5 kg strain-gauge load cell',
        'stage': 'S1 mechanical FEA, round 1',
        'date': '2026-11-04',
        'solver': 'CalculiX 2.22 (SPOOLES), Gmsh 4.13.1',
        'units': 'mm-N-MPa',
        'status': 'trend analysis, not design certification',
    },
    'geometry': {
        'step': 'mechanical/hy928d/build/hy928d_v2.step',
        'plate_mm': [34.0, 34.0, 1.0],
        'corner_holes': '4 x D3.1 at 28 x 28 mm pitch',
        'centre_hole_d_mm': 5.0,
        'features': 'through U-slot (2.5 mm wide), arch slot (R5.0-R8.2, 25-155 deg), '
                    'two 12 x 2.5 mm vertical slots at x=+/-6.6, R2.5 notches',
        'provisional': 'U-slot / arch / vertical-slot curves are reconstructed from the drawing '
                       'and photos (params.json status=PROVISIONAL); dimensions are not supplier-confirmed.',
    },
    'material': {
        'name': '65Mn', 'E_MPa': 210000.0, 'nu': 0.3, 'rho_t_mm3': 7.85e-9,
        'model': 'linear elastic, small strain, isotropic',
        'yield': 'not specified by the project; supplier condition must be confirmed before a safety factor is quoted',
    },
    'assumptions': {
        'boundary_condition': 'ASSUMPTION A: all nodes within 2.2 mm of each corner-hole centre '
                              '(radius 2.2 mm, full 1 mm thickness) are ENCASTRE (Ux=Uy=Uz=0). '
                              'This is a simplification of the screw-clamp area, not a contact model.',
        'clamp_radius_mm': 2.2,
        'load': 'ASSUMPTION A: 49.05 N (5 kg) vertical -Z, distributed as consistent nodal forces '
                'on the top face z=1 mm inside r<=4.0 mm around the centre hole (annulus r=2.5-4.0 mm, '
                'area 30.59 mm2, mean pressure 1.60 MPa). 1 kg = 9.81 N case run separately.',
        'element': 'C3D10 quadratic tetrahedra; primary mesh h=0.28 mm (~3-4 elements through 1 mm thickness).',
        'solution': '*STATIC, linear perturbation; no contact, no prestress, no geometric nonlinearity.',
    },
    'mesh': {
        'primary': {'file': 'mesh_h028_c3d10.msh', 'element': 'C3D10', **{k: Q28[k] for k in
                    ['nodes', 'tets', 'corner_quality_min', 'corner_quality_p01',
                     'corner_quality_median', 'ho_jac_min_ratio', 'ho_jac_p01_ratio',
                     'ho_bad_elements_ratio_lt_0.1']}},
        'convergence_meshes': [
            {'h_mm': 0.35, 'file': 'mesh_h035_c3d10.msh', 'element': 'C3D10',
             'nodes': C35['mesh']['nodes'], 'tets': C35['mesh']['elements'],
             'corner_quality_min': Q35['corner_quality_min'], 'ho_jac_min_ratio': Q35['ho_jac_min_ratio']},
            {'h_mm': 0.30, 'file': 'mesh_h030_c3d10.msh', 'element': 'C3D10',
             'nodes': C30['mesh']['nodes'], 'tets': C30['mesh']['elements'],
             'corner_quality_min': Q30['corner_quality_min'], 'ho_jac_min_ratio': Q30['ho_jac_min_ratio']},
            {'h_mm': 0.28, 'file': 'mesh_h028_c3d10.msh', 'element': 'C3D10',
             'nodes': P['mesh']['nodes'], 'tets': P['mesh']['elements']},
            {'h_mm': 0.20, 'file': 'mesh_h020_c3d4.msh', 'element': 'C3D4',
             'nodes': L20['mesh']['nodes'], 'tets': L20['mesh']['elements']},
            {'h_mm': 0.15, 'file': 'mesh_h015_c3d4.msh', 'element': 'C3D4',
             'nodes': L15['mesh']['nodes'], 'tets': L15['mesh']['elements']},
        ],
        'failed_meshes': [
            {'h_mm': 0.25, 'file': 'mesh_h025_c3d10.msh', 'element': 'C3D10',
             'nodes': 413814, 'tets': 252459, 'corner_quality_min': None,
             'note': 'valid mesh; solver ran out of SPOOLES capacity'},
            {'h_mm': 0.20, 'file': 'mesh_h020_c3d10.msh', 'element': 'C3D10',
             'nodes': Q20['nodes'], 'tets': Q20['tets'],
             'corner_quality_min': Q20['corner_quality_min'], 'ho_jac_min_ratio': Q20['ho_jac_min_ratio'],
             'note': 'valid mesh (no bad elements); solver SIGSEGV'},
        ],
        'dof': {'C3D10_h028': 3 * P['mesh']['nodes'], 'C3D10_h030': 3 * C30['mesh']['nodes'],
                'C3D4_h015': 3 * L15['mesh']['nodes']},
    },
    'load': {
        'force_5kg_N': 49.05, 'force_1kg_N': 9.81,
        'area_mm2': SETS28['load_area_mm2'], 'mean_pressure_MPa': 49.05 / SETS28['load_area_mm2'],
        'load_nodes': SETS28['load_nodes'], 'clamp_nodes': SETS28['clamp_nodes'],
    },
    'results_primary_C3D10_h028': {
        **P['results'],
        'reactions': P['reactions'],
        'regions': P['regions'],
    },
    'linearity_1kg': {
        'method': 'same C3D10 h=0.30 mesh, separate 9.81 N solve (not scaled)',
        'center_uz_5kg_mm': C30['scaling']['center_uz_5kg_mm'],
        'center_uz_1kg_mm': C30['scaling']['center_uz_1kg_mm'],
        'measured_ratio': C30['scaling']['ratio_1kg_over_5kg'],
        'expected_ratio': 0.2,
        'error_pct': pct(C30['scaling']['ratio_1kg_over_5kg'], 0.2),
        'verdict': 'linear to <2e-7 relative; linear scaling is valid',
    },
    'convergence': conv,
    'slot_vs_shallow': {
        'method': 'same C3D10 h=0.30 mesh; U-slot replaced by a 0.7 mm deep top pocket, '
                  '0.3 mm bottom web; all other features unchanged',
        'through': CMP['through'], 'shallow07': CMP['shallow07'],
        'stiffness_ratio_through_over_shallow': CMP['stiffness_ratio_through_over_shallow'],
        'stress_ratio_no_slotcorner': CMP['stress_ratio_through_over_shallow'],
        'extra_region_stress_MPa': {
            'tongue_root_mid': [C30['regions']['tongue_root_mid_|x|<=10.5']['max'],
                                SH['regions']['tongue_root_mid_|x|<=10.5']['max']],
            'vertical_slot_end': [C30['regions']['slot_end_pm6.6_pm6']['max'],
                                  SH['regions']['slot_end_pm6.6_pm6']['max']],
            'arch_end': [C30['regions']['arch_end_pm7.4_y3.5']['max'],
                         SH['regions']['arch_end_pm7.4_y3.5']['max']],
        },
        'caveat': 'the 0.3 mm web has only ~1 C3D10 element through its thickness at h=0.30; '
                  'the shallow-cavity stiffness is therefore a preliminary estimate (likely within ~10%).',
    },
    'figures': [
        'figs/fig_through_top.png', 'figs/fig_through_3d_vm.png',
        'figs/fig_through_3d_uz.png', 'figs/fig_shallow_top.png',
        'figs/fig_shallow_3d_vm.png', 'figs/fig_compare.png',
    ],
    'limitations': [
        'ENCASTRE over a 2.2 mm radius disk is a crude screw-clamp model; real screw/boss compliance, '
        'friction and base contact will change the reaction split and local stress.',
        'The U-slot end at (+/-11.8, 9.6) is a sharp 90-degree corner in the reconstructed geometry. '
        'The 588 MPa peak there is a mesh-dependent singularity and must not be used as a design stress; '
        'the real part needs a rounded slot end.',
        'The U-slot/arch/vertical-slot outlines are PROVISIONAL; the 468 MPa vertical-slot-end stress '
        'and the 1.72x stiffness ratio depend on these curves.',
        'Linear elastic, small strain: at 0.34 mm centre travel on a 1 mm plate, geometric stiffening '
        'and contact with an overload stop are not modelled; the linear result is likely slightly conservative '
        'for displacement.',
        'No strain-gauge/glue layer, no solder pads, no cable stiffness, no thermal residual stress.',
        'The 1 kg case was verified on the h=0.30 mesh; the h=0.28 1 kg value is scaled (linear).',
        'C3D10 h=0.25/0.20 runs failed inside SPOOLES (SIGSEGV) on this machine; h=0.28 is the finest '
        'successful C3D10 mesh. Convergence at h=0.28 is nevertheless <0.1% in centre displacement.',
    ],
    'conclusions': [
        '5 kg centre deflection: 0.343 mm (range 0.337-0.354 over the hole rim); 1 kg: 0.0687 mm. '
        'The linear ratio is 0.200000.',
        'Max |U| = 0.369 mm at the tongue bottom notch (x=-2.5, y=-11.4).',
        'The four corner reactions sum to 49.050 N (100.00% of the applied load), so the load path and '
        'BCs are consistent. The split is strongly asymmetric: the two screws at y=+14 carry 24.38 N each, '
        'the two at y=-14 only 0.142 N each (0.6%). The U-slot opens toward +y, so the bottom screws sit on '
        'a compliant tail. This is a model result and a key item to check in the assembly.',
        'Absolute peak von Mises: 588 MPa at the sharp U-slot end corner (singular, mesh-dependent). '
        'The converged non-singular hot spot is 468 MPa at the R1.25 vertical-slot end (x=6.1, y=-5.9). '
        'Tongue-root nominal stress is 229 MPa, arch end 266 MPa, beam ligament 136 MPa, boss 163 MPa.',
        'With the 0.5-0.6 mm assembly float gap, 0.343 mm centre travel uses 57-69% of the gap and exceeds '
        'the provisional FLOAT_GAP/2 acceptance limit (0.25-0.30 mm). Check overload-stop contact and '
        'part tolerances before committing.',
        'Shallow 0.7 mm cavity: 1.72x stiffer (0.200 mm at 5 kg), tongue-root stress drops 229 -> 64 MPa, '
        'but the vertical-slot-end stress only drops 468 -> 447 MPa and the sensitivity falls by ~42%. '
        'It is not a free fix: the dominant slot-end concentration remains.',
    ],
}

json.dump(res, open('results.json', 'w'), indent=2)
print(json.dumps({k: res[k] for k in ['linearity_1kg', 'convergence']}, indent=2)[:3000])
print('wrote results.json')
