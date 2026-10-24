# Jury-model run: bugs and quality findings

Run of the seven organizer models through Brim on the stand, 2026-10-24.
Stand: Win10 VM `user@192.168.1.190`, STE Slicer 7.10.12, plugin from `main` (0.4.0, then 0.4.1
from branch `fix/jury-run-findings`). Backend `brim-backend:latest` rebuilt from `main` 4c085cd
(Claude via subscription, backend always calls `opus`). Each model: new chat, skill «Инженер» pinned,
mode «Авто», STL + DOCX + JPG from `Desktop\Brim-models\<folder>` attached via the file dialog.

Status values: fixed (commit on branch, deployed to the stand), fixed (stand) (stand setup only),
mitigated, open, note. All plugin fixes are on `fix/jury-run-findings`, plugin 0.4.1, deployed to the stand;
plugin unit tests: 155 passed, 2 skipped (Python 3.14). No new tests were written (user instruction).

## Run results

Exported with the chat export button to `Desktop\results\<model>\` on the stand
(`project.3mf`, `result.gcode`, `chat.md`, `chat_NN.png`); copy outside the repo in
`~/mosprom-results/2026-10-24/`. Checked offline: G-code header mode equals the 3MF `printing_mode`,
only `T0` is used, nozzle temperature matches the material, 5D files contain A/C moves, 3MF ZIP CRC ok.
These are slicer outputs; nothing was printed.

| Model | Chat | Mode | Material | Key choices | Time, mass | Chat quality |
|---|---|---|---|---|---|---|
| 1 Шестерня | `7540b6a2…` (rerun) | classic | Fiberpart PC G20 | flat, 100 %, 4 walls, brim | 1 h 30 min, 4.9 g | Clean rerun; Lewis check shows the part fails at 25 N·m, user chose «max strength, state the risk»; one confirmation card (infill 20 → 100 %) |
| 2 Колесо | `2402e687…` | cylindrical | Enduse TPU D70 | base Ø15.98 = bore | 14.3 h, 58.3 g | Clean |
| 3 Пыльник | `c77f9c40…` | classic | Sealant TPU A95 | big flange down, no supports, 5 walls | 33.6 h, 83.2 g | Clean (third attempt, B11) |
| 4 Фигурка | `aa325df4…` (rerun) | classic | Fiberpart ABSPA G8 | tree supports, 0.1 mm, 3 walls, gyroid 15 %, brim | 74.0 h, 192.8 g | Clean rerun after B20; flags «no visible layers» as unreachable without post-processing |
| 5 Wilo | `c28264ee…` | cylindrical | Fiberpart PP G30 | base Ø7.9 < bore 7.97 | 41.6 h, 190 g | Clean; flags keyway risk |
| 6 Крыльчатка | `932d3cb2…` | classic | Fiberpart PA12 G12 | flat, supports from plate | 12.7 h, 69 g | Clean |
| 7 Ось Krones | `978b8716…` | cylindrical_full | Enduse PA6 | solid on axis, 100 %, 6 walls | 6.1 h, 16.2 g | Clean; torsion check shows neck margin 0.51 |

Folder names give 3D/5D for six models; the agent's mode matches all six. The figurine has no
mode in its folder name. Reference 3MF files are with the jury, so closeness to them is not known.

| # | Severity | Status | Finding |
|---|---|---|---|
| B1 | High | fixed | New chat inherits setting overrides of the previous chat |
| B2 | High | fixed | Slice report puts material on the wrong extruder |
| B3 | Low | fixed | `render_scene` advertises seven views, only `iso` works |
| B4 | Medium | open | Agent invented an attached PNG that does not exist |
| B5 | Low | fixed | Attachment dialog opens in `C:\Windows\System32` |
| B6 | Low | open | Long `ask_user` options are cut at the right edge |
| B7 | High | fixed (stand) | 5D slicing hangs: STE started without its install folder as working directory |
| B8 | High | fixed (stand) | 5D engine `glicer_console` was not activated (ATSS dialog) |
| B9 | High | fixed | `cylindrical_full` on a part with a bore around the axis never finishes; agent had no 5D placement rules |
| B10 | High | fixed | `PermissionError` on `chat.json` replace stops the agent turn on Windows |
| B11 | High | fixed | Slicing while STE's machine error check runs crashes the slicer (`KeyError: 0`) |
| B12 | Medium | fixed | Failed or hung slice gives the agent no reason; hung slice waits 900 s |
| B13 | Medium | mitigated | Two-extruder classic slice failed in the engine (`machine_extruder_count` has no value) |
| B14 | Low | open | Chat does not scroll to a new confirmation card; «Новые сообщения» must be clicked |
| B15 | Low | open | New chat keeps the previous chat's materials; only overrides are reset (B1) |
| B16 | Medium | open | All chats get the same title from the first message; the chat list cannot tell them apart |
| B17 | High | open | After 5D slices the CuraEngine process is gone; the next classic slice waits forever at 0 % |
| B18 | Low | open | Agent said it re-checked the scene after a restart without calling a tool (corrected itself in the next reply) |
| B19 | Low | open | Export opens Explorer with a delay; it steals focus from the slicer |
| B20 | High | fixed | Agent chose `cylindrical_full` for the figurine (no axis of revolution, 565k triangles); both 5D slices hung |
| N1 | Note | open | One model turn through the backend takes 1–3 min; a model run takes 15–40 min |
| N2 | Note | closed | `cylindrical_full` G-code has two headers (5D part and 3D core); not a bug |
| N3 | Note | open | Wilo G-code is 201 MB, figurine rerun 298 MB; ZIP size limit is unknown (open question Q2) |

## Rerun of the gear and the figurine, 2026-10-24

The first gear and figurine chats contained failed or interrupted steps (B17, B20). Both were rerun
in new chats on plugin 0.4.1 plus the B20 prompt rule, STE restarted before the gear chat. The gear
STL was downloaded again from the organizers' archive (SHA-256 of the archive and of `Шестерня.stl`
match `brief/sources/test-models-manifest.json`) under its original name, so the export folder is
`results\Шестерня` instead of `results\gear`. Old exports moved to `Desktop\results-old-2026-10-24`
on the stand and to `_old/` in the local copy.
Checked offline: G-code header `classic`, only `T0`, nozzle 290 °C (PC G20) / 280 °C (ABSPA G8),
3MF ZIP CRC ok, 3MF `printing_mode = classic`; chat exports contain no failed tool calls.
Quality notes: gear choices match the first run; the figurine has fewer walls (3 vs 4) and
lower mass (193 g vs 276 g) than the first run, and 74 h per piece (about 1100 h for 15) is listed
as the main risk with the option of several copies per plate.

## B20. 5D chosen for the figurine

Observed in the first figurine chat: the agent chose `cylindrical_full`; OpenSCAD could not
intersect the 565k-triangle mesh, two slices ran into the timeout, and the engine stayed broken
for the following classic slice until STE was restarted.
Fix: prompt rule — 5D only for parts of revolution or when the specification needs layers around
an axis; with `triangle_count` above 200 000 no 5D slicing (observed: 73k sliced, 565k did not).
Verified on the stand: the rerun agent chose classic and cited the triangle count.

## B1. New chat inherits setting overrides

Observed: the first gear chat started with `material_print_temperature 285`, `retraction_amount 6.9`,
`material_flow_layer_0 95`, `xy_offset_layer_0 -0.1`, `wall_0_wipe_dist 0.4` in `overrides`. These were
defect fixes from an earlier chat; the agent sliced with them.

Cause: `SlicerPort.clear_workspace` removed scene objects only; user changes on the global and
extruder stacks stayed.

Fix: `clear_workspace` also clears all user overrides (same code as `reset_overrides` without keys).
Verified on the stand: a new chat after the fix reports `overrides: {}`. Note: with no override the
machine default `printing_mode` is `cylindrical_full`; materials per extruder are not reset.

## B2. Slice report puts material on the wrong extruder

Observed: gear chats 1 and 2 selected Fiberpart PC G20 on extruder 0; the slice result reported
`material_weight_g: [0.0, 4.51]` / `[0.0, 4.89]`, i.e. on extruder 1 with generic PLA. The agent warned
the user that the part may print in PLA and, in chat 2, argued about densities to explain it.
The G-code was correct: `T0`, `M104 S290`, `;Filament used: 1.72173m, 0m`.

Cause: STE `PrintInformation.materialWeights/materialLengths` are filled in the iteration order of
`global_stack.extruders` (a dict, unordered in Python 3.5), not by extruder index. On the stand the
order is `1, 0`.

Fix: `SlicingService._summary` maps the values back to extruder indices using the same iteration
order. Verified on the stand: the same gear project now reports `[4.89, 0.0]`.
Hardening in the same pass: `objects[].extruder` in the scene state, operation
`set_object_extruder(object_id, extruder)`, prompt rule to check per-extruder use after slicing.

## B3. `render_scene` views

`tools.json` listed `iso, front, back, left, right, top, bottom`; `Renderer` supports only `iso`.
The agent spent a turn on two failed calls. Fix: schema enum is `iso` only.

## B4. Agent invented a PNG attachment

Seen in a manual chat before this run (`73d1753a…`): the user attached only a DOCX and asked
«что видишь?»; the agent answered that a PNG `.../images/1.png` was attached but not visible.
No image was in the message, the attachments list or tool results. Not reproduced yet.
Checked 2026-10-24: a direct backend request with a PNG `image_url`, with and without tools, is
answered correctly («The image is solid red»), so images reach Claude; this is a model hallucination,
not a transport loss.

## B5. Attachment dialog start folder

The file dialog opens in the process working directory `C:\Windows\System32` instead of the last
used folder or the user's home.
Fix: the attach dialog starts in `shortcuts.home`.

## B6. Long question options are cut

`ask_user` option buttons are single-line; a 110-character option («Моменты в ТЗ на самом деле в
Н·см (0,25 / 0,75 Н·м): готовим печать как есть, запас около 3,3») is clipped at the panel edge at
566 px panel width. The full text is still sent when clicked.

## B7. 5D slicing hangs on the stand (stand setup)

`cylindrical_full` slice stayed at 0 %; log: `Failed to intersect model! No SCAD available!` and
`Exception while differece model! No SCAD available!`. `openscad.exe` ships in the STE folder, but the
stand's scheduled task `BrimSlicer` started `STESlicer.exe` with an empty working directory
(System32), so STE could not find it. The Start-menu shortcut uses the install folder.
Fix on the stand: task working directory = `C:\Program Files\Stereotech STE Slicer 7.10`.
This also explains B5 (dialog in System32).

## B8. 5D engine not activated (stand setup)

After B7 the `cylindrical` slice opened the ATSS window «Отправьте этот код в поддержку». Activated
with the organizers' self-service form (code → `steslicer_license.reg`, 10-day licence); `reg import`
rejected the UTF-8-with-BOM file, so the value was written with PowerShell
(`HKCU\Software\common\interface\Value`). 5D slicing works after a restart.

## B9. 5D modes and parts with a bore

STE `cylindrical_full` intersects the model with the base cylinder (`cylindrical_mode_base_diameter`,
default 6 mm) and prints that core in 3D first. The conveyor wheel has a Ø16 mm bore, so the
intersection is empty, OpenSCAD exits 1 and the slice never finishes. `cylindrical` with
`cylindrical_mode_base_diameter = 16` slices (6.7 h, 57.9 g on the first try).
Fix: `analyze_geometry` reports `rotation_axis_5d` (`crosses_material`, `min_radius_mm`,
`max_radius_mm` around the vertical axis through the plate centre); prompt rules for axis placement,
base diameter and when `cylindrical_full` is impossible. Checked offline: wheel r 7.99 mm, Wilo
r 3.99 mm, Krones axle crosses material. On the stand the agent then chose `cylindrical` with base
Ø15.98 mm for the wheel by itself.

## B10. `chat.json` replace fails on Windows

`PermissionError: [WinError 5]` on `os.replace(chat.json.part, chat.json)` stopped the turn. Trigger
in this run: the stand status script read `chat.json`; any antivirus or indexer can do the same.
Fix: retry the replace up to 10 times with 0.1 s pauses; the stand script now opens the file with
`FileShare.Delete`.

## B11. STE crash during slicing

Twice on the CV-joint boot (17 MB STL): `CuraEngineBackend._onGCodePrefixMessage` → `KeyError: 0`, STE
closed. Cause from STE sources: the machine error check took 23 s on the large mesh; when it finished
during slicing, `_onStackErrorCheckFinished → needsSlicing → _clearLayerData` reset
`scene.gcode_dict`, and the next prefix message from the engine has no entry (STE has no guard there,
unlike `_onGCodeLayerMessage`). Fix: `SlicingService` waits until
`MachineErrorChecker.needToWaitForResult` is false (≤ 180 s) before `forceSlice`. The third boot run
sliced without a crash.

## B12. Slice failures without reason

`slice_failed` came with `slicer_errors: []`; a hung 5D slice waited the full 900 s. Fix: the plugin
marks `steslicer.log` before slicing and returns new ERROR lines as `engine_log`; known fatal lines
(`Failed to intersect model`, `No SCAD available`, `setting with no value given`) stop the wait after
20 s. `Connection reset by peer` is ignored (it also appears on normal engine restarts).
Limit: the figurine's first `cylindrical_full` slice hung without any log line, so it still ran
into the 900 s timeout.

## B13. Two-extruder classic slice

Boot with PLA supports on extruder 1: CuraEngine `[ERROR] Trying to retrieve setting with no value
given: 'machine_extruder_count'`, state Error. One observation; the retry crashed through B11, so
the two-extruder path is not separated from B11. Mitigation: prompt asks for one extruder and a
warning if the user wants two.

## B14. Confirmation card is off-screen

In «Авто» mode a confirmation card appears below the visible area; the activity bar says «Ждём
вашего решения ↓», but the list does not scroll until «Новые сообщения» is clicked.

## B15. Materials carry over to a new chat

After B1 a new chat starts with the previous chat's extruder materials (e.g. TPU D70 on extruder 0).
The agent selects a material anyway, but the context may suggest a choice was already made
(«уже заправлен»).

## B16. Identical chat titles

The title is the first user message cut to 60 characters. With a standard prompt every chat is
«Тестовое задание организаторов, п…»; the list shows only time. Switching to the right chat needed
the material name from STE's «Open Project» dialog.

## B17. Dead engine after 5D slicing

After the Krones `cylindrical_full` slice, the gear slice in classic logged «Sending slice message»
and stayed at 0 %; there was no `CuraEngine` process. The plugin's 45-min limit would have run out.
STE restart fixed it. Not fixed in the plugin: it cannot see the engine process.

## B18. Claimed check without a tool call

After «я перезапустил слайсер» the agent wrote «Проверил сцену после перезапуска…» and only sliced.
In the next reply it wrote a correction and compared with the slice result. The prompt asks to re-read
the scene after `interrupted`; the model skipped the call.

## B19. Export opens Explorer late

After the export the plugin opens the folder; on the stand Explorer appeared up to a minute later on
top of the slicer and caught the next clicks.

## N2. Two headers in `cylindrical_full` G-code

Krones: `;TIME:19725` (5D part, line 11) and `;TIME:2165` (3D core, line 15); 19 725 + 2 165 =
21 890 s, equal to the slicer total of 21 891 s. A checker that reads one header undercounts.
