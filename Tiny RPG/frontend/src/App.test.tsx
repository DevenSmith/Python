import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { changePassword, confirmPasswordReset, disableAccount, fetchCharacters, fetchClasses, fetchCurrentUser, fetchMonsters, fetchSecurityEvents, fetchSessions, fightMonster, levelUpCharacter, login, logout, logoutAllDevices, registerUser, requestEmailVerification, requestPasswordReset, restCharacter, restoreCurrentUser, reviveCharacter, revokeSession, storeAccessToken, updateAccount, verifyEmail } from './api/tinyrpgApi'

vi.mock('./api/tinyrpgApi', () => ({
  AUTH_EXPIRED_EVENT: 'tinyrpg:auth-expired', clearAccessToken: vi.fn(),
  createCharacter: vi.fn(), deleteCharacter: vi.fn(), fetchCharacterCount: vi.fn(),
  fetchCharacters: vi.fn(), fetchClasses: vi.fn(), fetchCurrentUser: vi.fn(), fetchMonsters: vi.fn(), fetchSecurityEvents: vi.fn(), fetchSessions: vi.fn(),
  changePassword: vi.fn(), confirmPasswordReset: vi.fn(), disableAccount: vi.fn(),
  fightMonster: vi.fn(), levelUpCharacter: vi.fn(), login: vi.fn(), logout: vi.fn(), logoutAllDevices: vi.fn(), registerUser: vi.fn(),
  requestEmailVerification: vi.fn(), requestPasswordReset: vi.fn(), restoreCurrentUser: vi.fn(),
  restCharacter: vi.fn(), reviveCharacter: vi.fn(), revokeSession: vi.fn(), storeAccessToken: vi.fn(), updateAccount: vi.fn(), verifyEmail: vi.fn(),
}))

const userRecord = { id: 1, email: 'avery@example.com', display_name: 'Avery', created_at: '2026-09-14T00:00:00Z', role: 'player' as const, email_verified: false }

describe('authentication UI', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.history.replaceState({}, '', '/')
    vi.mocked(fetchClasses).mockResolvedValue({ Warrior: 120 })
    vi.mocked(restoreCurrentUser).mockResolvedValue(null)
    vi.mocked(fetchSessions).mockResolvedValue([])
    vi.mocked(fetchSecurityEvents).mockResolvedValue([])
    vi.mocked(fetchMonsters).mockResolvedValue([])
  })

  it('shows sign in when there is no saved session', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(fetchCurrentUser).not.toHaveBeenCalled()
  })

  it('opens an emailed verification link directly', async () => {
    window.history.replaceState({}, '', '/?verify_token=email-token')

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Verify your email' })).toBeInTheDocument()
    expect(screen.getByLabelText('Verification token')).toHaveValue('email-token')
    expect(restoreCurrentUser).not.toHaveBeenCalled()
  })

  it('opens an emailed password-reset link directly', async () => {
    window.history.replaceState({}, '', '/?reset_token=email-reset-token')

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Choose a new password' })).toBeInTheDocument()
    expect(screen.getByLabelText('Reset token')).toHaveValue('email-reset-token')
    expect(restoreCurrentUser).not.toHaveBeenCalled()
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

  it('registers and opens the email verification screen', async () => {
    const user = userEvent.setup()
    vi.mocked(registerUser).mockResolvedValue({ user: userRecord, developmentToken: 'verification-token' })
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Need an account? Register' }))
    await user.type(screen.getByLabelText('Email'), 'avery@example.com')
    await user.type(screen.getByLabelText('Display name'), 'Avery')
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: 'Register' }))
    await waitFor(() => expect(registerUser).toHaveBeenCalledWith({ email: 'avery@example.com', display_name: 'Avery', password: 'secret123' }))
    expect(await screen.findByRole('heading', { name: 'Verify your email' })).toBeInTheDocument()
    expect(screen.getByLabelText('Verification token')).toHaveValue('verification-token')
    expect(login).not.toHaveBeenCalled()
  })

  it('verifies the email and returns to sign in', async () => {
    const user = userEvent.setup()
    vi.mocked(registerUser).mockResolvedValue({ user: userRecord, developmentToken: 'verification-token' })
    vi.mocked(verifyEmail).mockResolvedValue('Email verified')
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Need an account? Register' }))
    await user.type(screen.getByLabelText('Email'), 'avery@example.com')
    await user.type(screen.getByLabelText('Display name'), 'Avery')
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: 'Register' }))
    await user.click(await screen.findByRole('button', { name: 'Verify email' }))
    expect(verifyEmail).toHaveBeenCalledWith('verification-token')
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Email verified')
  })

  it('requests a replacement verification token', async () => {
    const user = userEvent.setup()
    vi.mocked(registerUser).mockResolvedValue({ user: userRecord, developmentToken: 'old-token' })
    vi.mocked(requestEmailVerification).mockResolvedValue({ message: 'Instructions created', developmentToken: 'new-token' })
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Need an account? Register' }))
    await user.type(screen.getByLabelText('Email'), 'avery@example.com')
    await user.type(screen.getByLabelText('Display name'), 'Avery')
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: 'Register' }))
    await user.click(await screen.findByRole('button', { name: 'Request another token' }))
    expect(requestEmailVerification).toHaveBeenCalledWith('avery@example.com')
    expect(screen.getByLabelText('Verification token')).toHaveValue('new-token')
  })

  it('logs out and returns to sign in', async () => {
    const user = userEvent.setup()
    vi.mocked(restoreCurrentUser).mockResolvedValue(userRecord)
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Log out' }))
    expect(logout).toHaveBeenCalled()
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('shows account details and updates the display name', async () => {
    const user = userEvent.setup()
    vi.mocked(restoreCurrentUser).mockResolvedValue(userRecord)
    vi.mocked(updateAccount).mockResolvedValue({ ...userRecord, display_name: 'Avery Updated' })
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Account' }))
    expect(screen.getByText('avery@example.com')).toBeInTheDocument()
    expect(screen.getByText('Not verified')).toBeInTheDocument()
    const name = screen.getByLabelText('Display name')
    await user.clear(name); await user.type(name, 'Avery Updated')
    await user.click(screen.getByRole('button', { name: 'Save profile' }))
    expect(updateAccount).toHaveBeenCalledWith('Avery Updated')
    expect(await screen.findByRole('status')).toHaveTextContent('Profile updated')
  })

  it('changes the password and returns to sign in', async () => {
    const user = userEvent.setup()
    vi.mocked(restoreCurrentUser).mockResolvedValue(userRecord)
    vi.mocked(changePassword).mockResolvedValue({ message: 'Password changed' })
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Account' }))
    await user.type(screen.getByLabelText('Current password'), 'old-password')
    await user.type(screen.getByLabelText('New password'), 'new-password')
    await user.click(screen.getByRole('button', { name: 'Change password' }))
    expect(changePassword).toHaveBeenCalledWith('old-password', 'new-password')
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('logs out every device from the account screen', async () => {
    const user = userEvent.setup()
    vi.mocked(restoreCurrentUser).mockResolvedValue(userRecord)
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Account' }))
    await user.click(screen.getByRole('button', { name: 'Log out on every device' }))
    expect(logoutAllDevices).toHaveBeenCalled()
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('lists active sessions and logs out another device', async () => {
    const user = userEvent.setup()
    vi.mocked(restoreCurrentUser).mockResolvedValue(userRecord)
    vi.mocked(fetchSessions).mockResolvedValue([{ id: 'other-session', created_at: '2026-09-15T00:00:00Z', last_seen_at: '2026-09-16T00:00:00Z', user_agent: 'Firefox', ip_address: '127.0.0.1', current: false }])
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Account' }))
    expect(await screen.findByText('Firefox')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Log out' }))
    expect(revokeSession).toHaveBeenCalledWith('other-session')
    expect(await screen.findByRole('status')).toHaveTextContent('Session signed out')
  })

  it('shows recent security activity on the account screen', async () => {
    const user = userEvent.setup()
    vi.mocked(restoreCurrentUser).mockResolvedValue(userRecord)
    vi.mocked(fetchSecurityEvents).mockResolvedValue([{ id: 1, event_type: 'login_succeeded', created_at: '2026-09-17T10:00:00Z', user_agent: 'Firefox', ip_address: '127.0.0.1' }])
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Account' }))
    expect(await screen.findByText('login succeeded')).toBeInTheDocument()
    expect(screen.getByText(/Firefox · 127.0.0.1/)).toBeInTheDocument()
  })

  it('requires a second click before disabling the account', async () => {
    const user = userEvent.setup()
    vi.mocked(restoreCurrentUser).mockResolvedValue(userRecord)
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Account' }))
    await user.click(screen.getByRole('button', { name: 'Disable my account' }))
    expect(disableAccount).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Yes, disable my account' }))
    expect(disableAccount).toHaveBeenCalled()
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('requests reset instructions and prefills the development token', async () => {
    const user = userEvent.setup()
    vi.mocked(requestPasswordReset).mockResolvedValue({
      message: 'If that account exists, password reset instructions were created',
      developmentToken: 'development-reset-token',
    })
    render(<App />)

    await user.click(await screen.findByRole('button', { name: 'Forgot password?' }))
    await user.type(screen.getByLabelText('Email'), 'avery@example.com')
    await user.click(screen.getByRole('button', { name: 'Request password reset' }))

    expect(await screen.findByRole('heading', { name: 'Choose a new password' })).toBeInTheDocument()
    expect(screen.getByLabelText('Reset token')).toHaveValue('development-reset-token')
    expect(requestPasswordReset).toHaveBeenCalledWith('avery@example.com')
  })

  it('submits the reset token and returns to sign in', async () => {
    const user = userEvent.setup()
    vi.mocked(requestPasswordReset).mockResolvedValue({ message: 'Instructions created', developmentToken: 'reset-token' })
    vi.mocked(confirmPasswordReset).mockResolvedValue('Password updated')
    render(<App />)

    await user.click(await screen.findByRole('button', { name: 'Forgot password?' }))
    await user.type(screen.getByLabelText('Email'), 'avery@example.com')
    await user.click(screen.getByRole('button', { name: 'Request password reset' }))
    await user.type(await screen.findByLabelText('New password'), 'new-secret-password')
    await user.click(screen.getByRole('button', { name: 'Update password' }))

    await waitFor(() => expect(confirmPasswordReset).toHaveBeenCalledWith('reset-token', 'new-secret-password'))
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Password updated')
  })

  it('loads monsters and fights with a roster character', async () => {
    const user = userEvent.setup()
    const character = { id: 7, owner_id: 1, name: 'Avery the Mage', character_class: 'Mage', health: 80, level: 1 }
    vi.mocked(restoreCurrentUser).mockResolvedValue(userRecord)
    vi.mocked(fetchMonsters).mockResolvedValue([{ slug: 'goblin', name: 'Goblin', health: 18, damage: 5 }])
    vi.mocked(fetchCharacters).mockResolvedValue([character])
    vi.mocked(fightMonster).mockResolvedValue({
      character_id: 7,
      monster: { slug: 'goblin', name: 'Goblin', health: 18, damage: 5 },
      victory: true,
      character_health: 75,
      rounds: [{ round_number: 1, character_roll: 20, outcome: 'critical', character_damage: 22, monster_health: 0, monster_damage: 0, character_health: 75 }],
    })
    render(<App />)

    await user.click(await screen.findByRole('button', { name: 'Load roster' }))
    await user.click(await screen.findByRole('button', { name: 'Fight' }))

    expect(fightMonster).toHaveBeenCalledWith(7, 'goblin')
    expect(await screen.findByRole('status')).toHaveTextContent('Victory over the Goblin')
    expect(screen.getByText(/rolled 20.*critical/)).toBeInTheDocument()
  })

  it('rests a roster character and displays the recovered health', async () => {
    const user = userEvent.setup()
    const injuredCharacter = { id: 7, owner_id: 1, name: 'Avery the Mage', character_class: 'Mage', health: 50, level: 1 }
    vi.mocked(restoreCurrentUser).mockResolvedValue(userRecord)
    vi.mocked(fetchCharacters).mockResolvedValue([injuredCharacter])
    vi.mocked(restCharacter).mockResolvedValue({ ...injuredCharacter, health: 66 })
    render(<App />)

    await user.click(await screen.findByRole('button', { name: 'Load roster' }))
    await user.click(await screen.findByRole('button', { name: 'Rest' }))

    expect(restCharacter).toHaveBeenCalledWith(7)
    expect(await screen.findByRole('status')).toHaveTextContent('Avery the Mage rested and recovered health')
    const rosterSection = screen.getByRole('heading', { name: 'Character roster' }).closest('section')
    expect(rosterSection).not.toBeNull()
    expect(within(rosterSection as HTMLElement).getByText(/Avery the Mage.*66 HP/)).toBeInTheDocument()
  })

  it('revives a defeated roster character and displays the restored health', async () => {
    const user = userEvent.setup()
    const defeatedCharacter = { id: 7, owner_id: 1, name: 'Avery the Mage', character_class: 'Mage', health: 0, level: 1 }
    vi.mocked(restoreCurrentUser).mockResolvedValue(userRecord)
    vi.mocked(fetchCharacters).mockResolvedValue([defeatedCharacter])
    vi.mocked(reviveCharacter).mockResolvedValue({ ...defeatedCharacter, health: 40 })
    render(<App />)

    await user.click(await screen.findByRole('button', { name: 'Load roster' }))
    expect(screen.queryByRole('button', { name: 'Rest' })).not.toBeInTheDocument()
    await user.click(await screen.findByRole('button', { name: 'Revive' }))

    expect(reviveCharacter).toHaveBeenCalledWith(7)
    expect(await screen.findByRole('status')).toHaveTextContent('Avery the Mage was revived with 40 HP')
    const rosterSection = screen.getByRole('heading', { name: 'Character roster' }).closest('section')
    expect(within(rosterSection as HTMLElement).getByText(/Avery the Mage.*Mage.*40 HP/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Rest' })).toBeInTheDocument()
  })

  it('levels up a roster character and displays the new level', async () => {
    const user = userEvent.setup()
    const character = { id: 7, owner_id: 1, name: 'Avery the Mage', character_class: 'Mage', health: 80, level: 1 }
    vi.mocked(restoreCurrentUser).mockResolvedValue(userRecord)
    vi.mocked(fetchCharacters).mockResolvedValue([character])
    vi.mocked(levelUpCharacter).mockResolvedValue({ ...character, level: 2 })
    render(<App />)

    await user.click(await screen.findByRole('button', { name: 'Load roster' }))
    await user.click(await screen.findByRole('button', { name: 'Level Up' }))

    expect(levelUpCharacter).toHaveBeenCalledWith(7)
    expect(await screen.findByRole('status')).toHaveTextContent('Avery the Mage reached level 2')
    const rosterSection = screen.getByRole('heading', { name: 'Character roster' }).closest('section')
    expect(within(rosterSection as HTMLElement).getByText(/Avery the Mage.*Level 2.*80 HP/)).toBeInTheDocument()
  })
})
