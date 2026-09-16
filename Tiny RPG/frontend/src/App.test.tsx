import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { fetchClasses, fetchCurrentUser, login, logout, registerUser, restoreCurrentUser, storeAccessToken } from './api/tinyrpgApi'

vi.mock('./api/tinyrpgApi', () => ({
  AUTH_EXPIRED_EVENT: 'tinyrpg:auth-expired', clearAccessToken: vi.fn(),
  createCharacter: vi.fn(), deleteCharacter: vi.fn(), fetchCharacterCount: vi.fn(),
  fetchCharacters: vi.fn(), fetchClasses: vi.fn(), fetchCurrentUser: vi.fn(),
  login: vi.fn(), logout: vi.fn(), registerUser: vi.fn(), restoreCurrentUser: vi.fn(), storeAccessToken: vi.fn(),
}))

const userRecord = { id: 1, email: 'avery@example.com', display_name: 'Avery', created_at: '2026-09-14T00:00:00Z', role: 'player' as const, email_verified: false }

describe('authentication UI', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchClasses).mockResolvedValue({ Warrior: 120 })
    vi.mocked(restoreCurrentUser).mockResolvedValue(null)
  })

  it('shows sign in when there is no saved session', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(fetchCurrentUser).not.toHaveBeenCalled()
  })

  it('restores a saved session through users/me', async () => {
    vi.mocked(restoreCurrentUser).mockResolvedValue(userRecord)
    render(<App />)
    expect(await screen.findByText(/Signed in as/)).toHaveTextContent('Avery')
  })

  it('signs in and stores the returned token', async () => {
    const user = userEvent.setup()
    vi.mocked(login).mockResolvedValue({ access_token: 'jwt-token', token_type: 'bearer' })
    vi.mocked(fetchCurrentUser).mockResolvedValue(userRecord)
    render(<App />)
    await user.type(await screen.findByLabelText('Email'), 'avery@example.com')
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() => expect(storeAccessToken).toHaveBeenCalledWith('jwt-token'))
    expect(await screen.findByText(/Signed in as/)).toHaveTextContent('Avery')
  })

  it('registers and then signs the new user in', async () => {
    const user = userEvent.setup()
    vi.mocked(registerUser).mockResolvedValue(userRecord)
    vi.mocked(login).mockResolvedValue({ access_token: 'new-token', token_type: 'bearer' })
    vi.mocked(fetchCurrentUser).mockResolvedValue(userRecord)
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Need an account? Register' }))
    await user.type(screen.getByLabelText('Email'), 'avery@example.com')
    await user.type(screen.getByLabelText('Display name'), 'Avery')
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: 'Register' }))
    await waitFor(() => expect(registerUser).toHaveBeenCalledWith({ email: 'avery@example.com', display_name: 'Avery', password: 'secret123' }))
    expect(login).toHaveBeenCalledWith({ email: 'avery@example.com', password: 'secret123' })
  })

  it('logs out and returns to sign in', async () => {
    const user = userEvent.setup()
    vi.mocked(restoreCurrentUser).mockResolvedValue(userRecord)
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Log out' }))
    expect(logout).toHaveBeenCalled()
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })
})
