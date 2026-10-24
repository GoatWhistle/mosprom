const OFFLINE = {
  ru: { connecting: "Подключаюсь к слайсеру…", no_token: "Откройте чат из меню слайсера: Brim → Открыть в браузере" },
  en: { connecting: "Connecting to the slicer…", no_token: "Open the chat from the slicer menu: Brim → Open in browser" },
};

export function offline() {
  return OFFLINE[navigator.language && navigator.language.startsWith("ru") ? "ru" : "en"];
}

export function setBanner(slot, banner, text, kind) {
  slot.hidden = !text;
  banner.className = "banner" + (kind ? " banner-" + kind : "");
  banner.textContent = text || "";
}
