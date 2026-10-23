import { useTranslation } from "@/shared/i18n"
import { withLayerSweep } from "@/shared/motion"
import { THEMES, type Theme, useTheme } from "@/shared/theme"
import { type IconName, Segmented, type SegmentedOption } from "@/shared/ui"

const THEME_ICON: Readonly<Record<Theme, IconName>> = {
  light: "theme-light",
  dark: "theme-dark",
}

export function ThemeSwitch() {
  const { t } = useTranslation()
  const { theme, setTheme } = useTheme()
  const options: SegmentedOption<Theme>[] = THEMES.map((value) => ({
    value,
    label: t(`common:theme.${value}`),
    icon: THEME_ICON[value],
  }))
  const change = (next: Theme) => {
    void withLayerSweep(next, () => setTheme(next))
  }
  return (
    <Segmented
      label={t("common:theme.legend")}
      options={options}
      value={theme}
      display="icon"
      onChange={change}
    />
  )
}
