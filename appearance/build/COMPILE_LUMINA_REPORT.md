# compile_lumina — one-command build report

> 2026-11-07T23:51:18 · 校验 46/46 · 结论 **PASS**

| 阶段 | 内容 | 耗时 | 结果 |
|---|---|---|---|
| /data/Documents/tools/Lumina-Layers/.venv/bin/python appearance/lumina/lumina_convert.py --art dog,elf |  | 75.5s | OK |
| bash appearance/cad/run_shell.sh --config /data/Documents/projects/SmartCoaster/appearance/config/lumina_project.yaml --skip-blender |  | 17.3s | OK |
| /data/Documents/tools/blender/blender -b --python appearance/render/build_scene.py |  | 182.1s | OK |
| /usr/bin/python3 appearance/render/make_3mf.py |  | 28.2s | OK |
| /usr/bin/python3 appearance/render/postprocess.py |  | 5.5s | OK |
| bash render/print/appearance/run_print_stage.sh |  | 131.4s | OK |
| /usr/bin/python3 appearance/tools/acceptance_check_lumina.py |  | 2.3s | OK |

日志：`appearance/build/compile_lumina.log`
