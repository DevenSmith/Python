export type ClassHealth = Record<string, number>

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
export const AUTH_EXPIRED_EVENT = 'tinyrpg:auth-expired'
let accessToken: string | null = null

export type UserResponse = {
  id: number
  email: string
  display_name: string
  created_at: string
  role: 'player' | 'admin'
  email_verified: boolean
}
export type RegisterUserRequest = { email: string; display_name: string; password: string }
export type RegistrationResponse = { user: UserResponse; developmentToken: string | null }
export type LoginRequest = { email: string; password: string }
export type TokenResponse = { access_token: string; token_type: string }
export type PasswordResetRequestResponse = {
  message: string
  developmentToken: string | null
}
export type SessionResponse = {
  id: string
  created_at: string
  last_seen_at: string
  user_agent: string
  ip_address: string
  current: boolean
}
export type SecurityAuditEventResponse = {
  id: number
  event_type: string
  created_at: string
  ip_address: string
  user_agent: string
}

export function getStoredAccessToken(): string | null {
  return accessToken
}

export function storeAccessToken(token: string): void {
  accessToken = token
}

export function clearAccessToken(): void {
  accessToken = null
}

function getCookie(name: string): string | null {
  const prefix = `${encodeURIComponent(name)}=`
  const cookie = document.cookie.split('; ').find((value) => value.startsWith(prefix))
  return cookie === undefined ? null : decodeURIComponent(cookie.slice(prefix.length))
}

function csrfHeaders(): HeadersInit {
  const token = getCookie('csrf_token')
  return token === null ? {} : { 'X-CSRF-Token': token }
}

async function refreshAccessToken(): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: 'POST',
    headers: csrfHeaders(),
    credentials: 'include',
  })
  if (!response.ok) return false
  const token = (await response.json()) as TokenResponse
  storeAccessToken(token.access_token)
  return true
}

async function request<T>(path: string, options: RequestInit = {}, requiresAuthentication = false, mayRetry = true): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body !== undefined) headers.set('Content-Type', 'application/json')

  if (requiresAuthentication) {
    const token = getStoredAccessToken()
    if (token !== null) headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers, credentials: 'include' })
  if (requiresAuthentication && response.status === 401) {
    if (mayRetry && await refreshAccessToken()) {
      return request<T>(path, options, requiresAuthentication, false)
    }
    clearAccessToken()
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
    throw new Error('Your session has expired. Please sign in again.')
  }
  if (!response.ok) throw new Error(`Request failed: ${response.status}`)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export function fetchClasses(): Promise<ClassHealth> {
  return request<ClassHealth>('/classes')
}

export async function registerUser(user: RegisterUserRequest): Promise<RegistrationResponse> {
  const response = await fetch(`${API_BASE_URL}/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(user),
    credentials: 'include',
  })
  if (!response.ok) throw new Error(`Unable to register: ${response.status}`)
  return {
    user: (await response.json()) as UserResponse,
    developmentToken: response.headers.get('X-Verification-Token'),
  }
}

export function login(credentials: LoginRequest): Promise<TokenResponse> {
  return request<TokenResponse>('/auth/token', { method: 'POST', body: JSON.stringify(credentials) })
}

export function fetchCurrentUser(): Promise<UserResponse> {
  return request<UserResponse>('/users/me', {}, true)
}

export async function restoreCurrentUser(): Promise<UserResponse | null> {
  if (getStoredAccessToken() === null && !await refreshAccessToken()) return null
  return fetchCurrentUser()
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      headers: csrfHeaders(),
      credentials: 'include',
    })
  } finally {
    clearAccessToken()
  }
}

export async function requestPasswordReset(email: string): Promise<PasswordResetRequestResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/password-reset/request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
    credentials: 'include',
  })
  if (!response.ok) throw new Error(`Unable to request password reset: ${response.status}`)
  const body = (await response.json()) as { message: string }
  return {
    message: body.message,
    developmentToken: response.headers.get('X-Password-Reset-Token'),
  }
}

export async function confirmPasswordReset(token: string, newPassword: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/auth/password-reset/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, new_password: newPassword }),
    credentials: 'include',
  })
  if (!response.ok) throw new Error(`Unable to reset password: ${response.status}`)
  const body = (await response.json()) as { message: string }
  return body.message
}

export async function verifyEmail(token: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/auth/verify-email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
    credentials: 'include',
  })
  if (!response.ok) throw new Error(`Unable to verify email: ${response.status}`)
  const body = (await response.json()) as { message: string }
  return body.message
}

export async function requestEmailVerification(email: string): Promise<PasswordResetRequestResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/verify-email/request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
    credentials: 'include',
  })
  if (!response.ok) throw new Error(`Unable to request verification: ${response.status}`)
  const body = (await response.json()) as { message: string }
  return {
    message: body.message,
    developmentToken: response.headers.get('X-Verification-Token'),
  }
}

export function updateAccount(displayName: string): Promise<UserResponse> {
  return request<UserResponse>('/users/me', {
    method: 'PATCH',
    body: JSON.stringify({ display_name: displayName }),
  }, true)
}

export function changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
  return request<{ message: string }>('/users/me/password', {
    method: 'POST',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  }, true)
}

export async function logoutAllDevices(): Promise<void> {
  await request<void>('/users/me/logout-all', { method: 'POST' }, true)
  clearAccessToken()
}

export function fetchSessions(): Promise<SessionResponse[]> {
  return request<SessionResponse[]>('/users/me/sessions', {}, true)
}

export function fetchSecurityEvents(limit = 20): Promise<SecurityAuditEventResponse[]> {
  return request<SecurityAuditEventResponse[]>(`/users/me/security-events?limit=${limit}`, {}, true)
}

export function revokeSession(sessionId: string): Promise<void> {
  return request<void>(`/users/me/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  }, true)
}

export async function disableAccount(): Promise<void> {
  await request<void>('/users/me', { method: 'DELETE' }, true)
  clearAccessToken()
}

export type CharacterCreate = { name: string; character_class: string }
export type CharacterResponse = {
  id: number
  owner_id?: number
  name: string
  character_class: string
  health: number
  level: number
}
export type CharacterCountResponse = { count: number }
export type DeleteCharacterResponse = { message: string }

export function createCharacter(character: CharacterCreate): Promise<CharacterResponse> {
  return request<CharacterResponse>('/characters', { method: 'POST', body: JSON.stringify(character) }, true)
}

export function fetchCharacters(): Promise<CharacterResponse[]> {
  return request<CharacterResponse[]>('/characters', {}, true)
}

export function fetchCharacterCount(): Promise<CharacterCountResponse> {
  return request<CharacterCountResponse>('/characters/count', {}, true)
}

export function deleteCharacter(characterId: number): Promise<DeleteCharacterResponse> {
  return request<DeleteCharacterResponse>(`/characters/${characterId}`, { method: 'DELETE' }, true)
}
