interface TelegramWebApp {
  initData: string
  colorScheme: 'light' | 'dark'
  ready: () => void
  expand: () => void
  openLink: (url: string) => void
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp }
  }
}

const webApp = () => window.Telegram?.WebApp

/** True only inside a Mini App: the script also loads in a regular browser, but initData stays empty. */
export const isTelegramWebApp = () => Boolean(webApp()?.initData)

export const getInitData = () => webApp()?.initData ?? ''

export function initTelegramWebApp() {
  if (!isTelegramWebApp()) return
  webApp()?.ready()
  webApp()?.expand()
}

export const telegramColorScheme = () => (isTelegramWebApp() ? webApp()?.colorScheme : undefined)

/** External links go through the Telegram viewer in a Mini App and a new tab elsewhere. */
export function openExternal(url: string) {
  // Ссылки из справочников и внешних источников: javascript: и подобное не открываем.
  if (!/^https?:\/\//i.test(url)) return
  if (isTelegramWebApp()) webApp()?.openLink(url)
  else window.open(url, '_blank', 'noopener,noreferrer')
}
