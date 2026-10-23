import { LOCALES, type Locale, useLocale, useTranslation } from "@/shared/i18n"
import { withTextScramble } from "@/shared/motion"
import { Segmented, type SegmentedOption } from "@/shared/ui"

const nextTask = () =>
  new Promise<void>((resolve) => {
    setTimeout(resolve)
  })

export function LocaleSwitch() {
  const { t, i18n } = useTranslation()
  const { locale, setLocale } = useLocale()
  const options: SegmentedOption<Locale>[] = LOCALES.map((value) => ({
    value,
    label: t(`common:language.${value}`),
    short: t(`common:language.short.${value}`),
  }))
  const change = (next: Locale) => {
    void withTextScramble(
      () => setLocale(next),
      async () => {
        await i18n.changeLanguage(next)
        await nextTask()
      },
    )
  }
  return (
    <Segmented
      label={t("common:language.legend")}
      options={options}
      value={locale}
      display="short"
      onChange={change}
    />
  )
}
