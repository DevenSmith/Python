import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchCharacters, storeAccessToken } from './tinyrpgApi'

describe('authenticated API requests', () => {
  afterEach(() => { localStorage.clear(); vi.unstubAllGlobals() })

  it('sends the JWT as a bearer token', async () => {
    storeAccessToken('test-jwt')
    const fetchMock = vi.fn().mockResolvedValue(new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    await fetchCharacters()
    const options = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(new Headers(options.headers).get('Authorization')).toBe('Bearer test-jwt')
  })

  it('removes a token rejected with 401', async () => {
    storeAccessToken('expired-jwt')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 401 })))
    await expect(fetchCharacters()).rejects.toThrow('session has expired')
    expect(localStorage.getItem('tinyrpg.access_token')).toBeNull()
  })
})
