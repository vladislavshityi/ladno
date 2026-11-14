import { afterEach, describe, expect, it, vi } from 'vitest'
import { getInitData, isTelegramWebApp, openExternal } from './telegram'

const withWebApp = (webApp: object | undefined) => vi.stubGlobal('window', { Telegram: webApp && { WebApp: webApp }, open: vi.fn() })

describe('telegram', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('is not a Mini App when the script is absent or initData is empty', () => {
    withWebApp(undefined)
    expect(isTelegramWebApp()).toBe(false)
    withWebApp({ initData: '' })
    expect(isTelegramWebApp()).toBe(false)
  })

  it('detects a Mini App by initData', () => {
    withWebApp({ initData: 'query_id=1&hash=x' })
    expect(isTelegramWebApp()).toBe(true)
    expect(getInitData()).toBe('query_id=1&hash=x')
  })

  it('opens links through Telegram inside a Mini App', () => {
    const openLink = vi.fn()
    withWebApp({ initData: 'x', openLink })
    openExternal('https://pos.gosuslugi.ru/')
    expect(openLink).toHaveBeenCalledWith('https://pos.gosuslugi.ru/')
  })

  it('opens a new tab in a regular browser', () => {
    withWebApp(undefined)
    openExternal('https://pos.gosuslugi.ru/')
    expect(window.open).toHaveBeenCalledWith('https://pos.gosuslugi.ru/', '_blank', 'noopener,noreferrer')
  })

  it('refuses non-web links such as javascript:', () => {
    const openLink = vi.fn()
    withWebApp({ initData: 'x', openLink })
    openExternal('javascript:alert(1)')
    openExternal('data:text/html,<script>1</script>')
    expect(openLink).not.toHaveBeenCalled()
  })
})
