---
name: material-selection
order: 3
title_ru: Материал
title_en: Material
description: The user asks which plastic to use, or the requirements (temperature, chemicals, humidity, UV, flexibility, density, food contact, conductivity) make the material the main decision.
---
# Material selection

1. Collect requirements as numbers: service temperature, load and creep, flexibility, density
   limit, humidity, oils and fuels, acids and alkali, solvents, UV, ozone, friction partner,
   food contact, electrical conductivity. Ask with ask_user only for the ones that are missing
   and decisive.
2. Call match_materials with those requirements. It filters the materials available in the
   slicer by typical reference properties of their polymer family.
3. Present the shortlist as a table: material, passes, fails with reason. Explain the
   trade-off between the top two candidates in plain words.
4. Inspect the chosen material with inspect_material to read the profile temperatures and
   notes before selecting it.
5. Select the material with apply_changes select_material and mention printing consequences:
   drying, enclosure, bed adhesion, abrasive filler, nozzle.
6. Never invent a material that is not in the slicer. If nothing passes, say which requirement
   blocks every candidate and what compromise or post-processing would help.
