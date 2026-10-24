---
name: defect-diagnosis
order: 4
title_ru: Дефекты
title_en: Defects
description: The user shows a photo of a printed part or describes a print problem (stringing, blobs, holes in walls, gaps, rough or thick layers, warping, layer shifts, sagging overhangs) and wants the settings corrected.
---
# Defect diagnosis

1. Identify defects. From a photo, name each visible defect and where it is (outer wall,
   first layer, overhang, top surface, between parts). From text, map the words to defects.
   If the photo is unclear, ask for another angle or a close-up with ask_user.
2. Ask what matters when unknown: material and its age or drying, printer, whether the profile
   was changed. Do not ask what the scene context already shows.
3. Call lookup_defect for each defect. It returns causes, settings with the direction and a
   typical step, and the current values in the slicer.
4. Propose the smallest set of changes, most likely cause first. Change one or two settings per
   defect, by the typical step, relative to the current profile. Explain each change in one
   sentence: what it does and why it fixes this defect.
5. Mention causes that settings cannot fix: wet filament, clogged nozzle, loose belts, dirty bed.
6. Apply with apply_changes so the user confirms each value. Slice again if the user asks.
7. Ask the user to print again and send a new photo; compare with the previous attempt.
