import { afterEach, describe, expect, it, vi } from 'vitest'
import { confirmPasswordReset, fetchCharacters, getStoredAccessToken, requestPasswordReset, storeAccessToken } from './tinyrpgApi'

describe('authenticated API requests', () => {
  afterEach(() => { vi.unstubAllGlobals() })

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
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(null, { status: 401 })))
    await expect(fetchCharacters()).rejects.toThrow('session has expired')
    expect(getStoredAccessToken()).toBeNull()
  })

  it('returns the development password-reset token from the response header', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ message: 'Instructions created' }),
      { status: 202, headers: { 'Content-Type': 'application/json', 'X-Password-Reset-Token': 'reset-token' } },
    )))

    await expect(requestPasswordReset('avery@example.com')).resolves.toEqual({
      message: 'Instructions created',
      developmentToken: 'reset-token',
    })
  })

  it('sends the reset token and new password to the confirmation endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ message: 'Password updated' }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    ))
    vi.stubGlobal('fetch', fetchMock)

    await expect(confirmPasswordReset('reset-token', 'new-secret-password')).resolves.toBe('Password updated')
    const options = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(JSON.parse(options.body as string)).toEqual({ token: 'reset-token', new_password: 'new-secret-password' })
  })
})
