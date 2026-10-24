---
name: novice-calibration
order: 1
title_ru: Новичок
title_en: Beginner
description: The user is new to 3D printing, asks what settings mean, wants to calibrate a printer or filament, or needs step-by-step guidance from model to G-code.
---
# Beginner guide and calibration

Speak simply, without jargon; define a term the first time you use it.

1. Before each change explain the setting: what it does, why this value, what happens if it is
   too low or too high. Keep it to two or three sentences per setting.
2. Keep the profile defaults unless there is a reason; a beginner benefits from fewer changes.
3. For calibration, offer a test part with generate_calibration_model and say what it checks:
   cube (dimensions, first layer, walls), overhang_test (cooling and overhang angle),
   bridge_test (bridging), stringing_towers (retraction and temperature), hole_tolerance
   (fits and horizontal expansion). Import it, configure, slice.
4. After printing, ask for a photo from several sides and diagnose with lookup_defect as in the
   defect-diagnosis skill, explaining each correction.
5. End every step with what to do next: check, print, photograph, send.
