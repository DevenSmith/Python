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
export type LoginRequest = { email: string; password: string }
export type TokenResponse = { access_token: string; token_type: string }

export function getStoredAccessToken(): string | null {
  return accessToken
}

export function storeAccessToken(token: string): void {
  accessToken = token
}

export function clearAccessToken(): void {
  accessToken = null
}

async function refreshAccessToken(): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: 'POST',
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
  return (await response.json()) as T
}

export function fetchClasses(): Promise<ClassHealth> {
  return request<ClassHealth>('/classes')
}

export function registerUser(user: RegisterUserRequest): Promise<UserResponse> {
  return request<UserResponse>('/users', { method: 'POST', body: JSON.stringify(user) })
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
    await fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST', credentials: 'include' })
  } finally {
    clearAccessToken()
  }
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
