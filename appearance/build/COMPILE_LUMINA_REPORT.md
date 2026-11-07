# compile_lumina — one-command build report

> 2026-11-07T23:09:40 · 校验 39/39 · 结论 **PASS**

| 阶段 | 内容 | 耗时 | 结果 |
|---|---|---|---|
| /usr/bin/python3 appearance/tools/make_art_lumina.py |  | 11.3s | OK |
| /data/Documents/tools/Lumina-Layers/.venv/bin/python appearance/lumina/lumina_convert.py --art dog,elf |  | 90.7s | OK |
| bash appearance/cad/run_shell.sh --config /data/Documents/projects/SmartCoaster/appearance/config/lumina_project.yaml --skip-blender |  | 16.9s | OK |
| /data/Documents/tools/blender/blender -b --python appearance/render/build_scene.py |  | 184.3s | OK |
| /usr/bin/python3 appearance/render/make_3mf.py |  | 37.7s | OK |
| /usr/bin/python3 appearance/render/postprocess.py |  | 5.3s | OK |
| bash render/print/appearance/run_print_stage.sh |  | 141.0s | OK |
| /usr/bin/python3 appearance/tools/acceptance_check_lumina.py |  | 2.6s | OK |

日志：`appearance/build/compile_lumina.log`
