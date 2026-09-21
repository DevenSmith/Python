import { useEffect, useState, type FormEvent } from 'react'
import './App.css'
import CharacterSummary from './components/CharacterSummary'
import {
  AUTH_EXPIRED_EVENT, changePassword, clearAccessToken, confirmPasswordReset,
  createCharacter, deleteCharacter, disableAccount, fightMonster,
  fetchCharacterCount, fetchCharacters, fetchCurrentUser, fetchMonsters, fetchSecurityEvents, fetchSessions, logout,
  levelUpCharacter, login, logoutAllDevices, registerUser, requestEmailVerification,
  renameCharacter, requestPasswordReset, restCharacter, restoreCurrentUser, reviveCharacter, revokeSession, storeAccessToken, updateAccount,
  verifyEmail,
  type CharacterResponse, type FightResponse, type MonsterResponse, type SecurityAuditEventResponse, type SessionResponse, type UserResponse,
} from './api/tinyrpgApi'
import { useCharacterClasses } from './hooks/useCharacterClasses'

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : 'An unknown error occurred'
}

function tokenFromUrl(name: string): string {
  return new URLSearchParams(window.location.search).get(name) ?? ''
}

function initialAuthMode(): 'login' | 'verify' | 'reset' {
  if (tokenFromUrl('verify_token') !== '') return 'verify'
  if (tokenFromUrl('reset_token') !== '') return 'reset'
  return 'login'
}

function clearAuthLink(): void {
  window.history.replaceState({}, '', window.location.pathname)
}

function App() {
  const { classHealth, isLoading, classError } = useCharacterClasses()
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null)
  const [isRestoringSession, setIsRestoringSession] = useState(true)
  const [startedFromAuthLink] = useState(
    () => tokenFromUrl('verify_token') !== '' || tokenFromUrl('reset_token') !== '',
  )
  const [authMode, setAuthMode] = useState<'login' | 'register' | 'verify' | 'forgot' | 'reset'>(initialAuthMode)
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState<string | null>(null)
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [resetToken, setResetToken] = useState(() => tokenFromUrl('reset_token'))
  const [newPassword, setNewPassword] = useState('')
  const [authMessage, setAuthMessage] = useState<string | null>(null)
  const [verificationToken, setVerificationToken] = useState(() => tokenFromUrl('verify_token'))
  const [showAccount, setShowAccount] = useState(false)
  const [accountDisplayName, setAccountDisplayName] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [accountNewPassword, setAccountNewPassword] = useState('')
  const [accountMessage, setAccountMessage] = useState<string | null>(null)
  const [accountError, setAccountError] = useState<string | null>(null)
  const [isUpdatingAccount, setIsUpdatingAccount] = useState(false)
  const [confirmDisable, setConfirmDisable] = useState(false)
  const [sessions, setSessions] = useState<SessionResponse[]>([])
  const [areSessionsLoading, setAreSessionsLoading] = useState(false)
  const [securityEvents, setSecurityEvents] = useState<SecurityAuditEventResponse[]>([])
  const [characterName, setCharacterName] = useState('Deven')
  const characterClasses = Object.keys(classHealth)
  const [chosenClass, setChosenClass] = useState<string | null>(null)
  const selectedClass = chosenClass ?? characterClasses[0] ?? ''
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [createdCharacter, setCreatedCharacter] = useState<CharacterResponse | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [nameError, setNameError] = useState<string | null>(null)
  const [roster, setRoster] = useState<CharacterResponse[] | null>(null)
  const [isRosterLoading, setIsRosterLoading] = useState(false)
  const [rosterError, setRosterError] = useState<string | null>(null)
  const [rosterMessage, setRosterMessage] = useState<string | null>(null)
  const [restingCharacterId, setRestingCharacterId] = useState<number | null>(null)
  const [revivingCharacterId, setRevivingCharacterId] = useState<number | null>(null)
  const [levelingCharacterId, setLevelingCharacterId] = useState<number | null>(null)
  const [editingCharacterId, setEditingCharacterId] = useState<number | null>(null)
  const [editedCharacterName, setEditedCharacterName] = useState('')
  const [isRenaming, setIsRenaming] = useState(false)
  const [characterCount, setCharacterCount] = useState<number | null>(null)
  const [monsters, setMonsters] = useState<MonsterResponse[]>([])
  const [chosenMonster, setChosenMonster] = useState<string | null>(null)
  const [chosenFighter, setChosenFighter] = useState<number | null>(null)
  const [fightResult, setFightResult] = useState<FightResponse | null>(null)
  const [combatError, setCombatError] = useState<string | null>(null)
  const [isFighting, setIsFighting] = useState(false)

  useEffect(() => {
    const expireSession = () => {
      setCurrentUser(null); setRoster(null); setCreatedCharacter(null)
      setAuthError('Your session has expired. Please sign in again.')
    }
    window.addEventListener(AUTH_EXPIRED_EVENT, expireSession)

    async function restoreSession(): Promise<void> {
      if (startedFromAuthLink) {
        setIsRestoringSession(false)
        return
      }
      try { setCurrentUser(await restoreCurrentUser()) }
      catch (error: unknown) { clearAccessToken(); setAuthError(errorText(error)) }
      finally { setIsRestoringSession(false) }
    }
    void restoreSession()
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, expireSession)
  }, [startedFromAuthLink])

  useEffect(() => {
    if (currentUser === null) return
    fetchMonsters().then(setMonsters).catch((error: unknown) => setCombatError(errorText(error)))
  }, [currentUser])

  async function handleAuthentication(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault(); setAuthError(null); setIsAuthenticating(true)
    try {
      if (authMode === 'register') {
        const registration = await registerUser({ email, display_name: displayName, password })
        if (registration.developmentToken !== null) setVerificationToken(registration.developmentToken)
        setPassword(''); setAuthMode('verify')
        setAuthMessage('Account created. Verify your email before signing in.')
        return
      }
      const token = await login({ email, password })
      storeAccessToken(token.access_token)
      setCurrentUser(await fetchCurrentUser())
      setPassword('')
    } catch (error: unknown) { clearAccessToken(); setAuthError(errorText(error)) }
    finally { setIsAuthenticating(false) }
  }

  function changeAuthMode(mode: 'login' | 'register' | 'verify' | 'forgot' | 'reset'): void {
    setAuthMode(mode); setAuthError(null); setAuthMessage(null)
  }

  async function handleEmailVerification(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault(); setAuthError(null); setAuthMessage(null); setIsAuthenticating(true)
    try {
      await verifyEmail(verificationToken)
      setVerificationToken(''); clearAuthLink(); setAuthMode('login')
      setAuthMessage('Email verified. You can now sign in.')
    } catch (error: unknown) { setAuthError(errorText(error)) }
    finally { setIsAuthenticating(false) }
  }

  async function handleVerificationRequest(): Promise<void> {
    setAuthError(null); setAuthMessage(null); setIsAuthenticating(true)
    try {
      const result = await requestEmailVerification(email)
      if (result.developmentToken !== null) setVerificationToken(result.developmentToken)
      setAuthMessage(result.message)
    } catch (error: unknown) { setAuthError(errorText(error)) }
    finally { setIsAuthenticating(false) }
  }

  async function handlePasswordResetRequest(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault(); setAuthError(null); setAuthMessage(null); setIsAuthenticating(true)
    try {
      const result = await requestPasswordReset(email)
      setAuthMessage(result.message)
      if (result.developmentToken !== null) setResetToken(result.developmentToken)
      setAuthMode('reset')
    } catch (error: unknown) { setAuthError(errorText(error)) }
    finally { setIsAuthenticating(false) }
  }

  async function handlePasswordResetConfirm(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault(); setAuthError(null); setAuthMessage(null); setIsAuthenticating(true)
    try {
      await confirmPasswordReset(resetToken, newPassword)
      setPassword(''); setNewPassword(''); setResetToken(''); clearAuthLink(); setAuthMode('login')
      setAuthMessage('Password updated. You can now sign in with your new password.')
    } catch (error: unknown) { setAuthError(errorText(error)) }
    finally { setIsAuthenticating(false) }
  }

  async function handleLogout(): Promise<void> {
    await logout(); setCurrentUser(null); setRoster(null)
    setCreatedCharacter(null); setCharacterCount(null); setAuthError(null)
  }

  async function openAccount(): Promise<void> {
    if (currentUser === null) return
    setAccountDisplayName(currentUser.display_name)
    setAccountMessage(null); setAccountError(null); setShowAccount(true)
    setAreSessionsLoading(true)
    try {
      const [activeSessions, recentEvents] = await Promise.all([
        fetchSessions(), fetchSecurityEvents(),
      ])
      setSessions(activeSessions); setSecurityEvents(recentEvents)
    }
    catch (error: unknown) { setAccountError(errorText(error)) }
    finally { setAreSessionsLoading(false) }
  }

  async function handleRevokeSession(loginSession: SessionResponse): Promise<void> {
    setAccountError(null); setAccountMessage(null); setIsUpdatingAccount(true)
    try {
      await revokeSession(loginSession.id)
      if (loginSession.current) {
        clearAccessToken(); setCurrentUser(null); setShowAccount(false)
        setAuthMessage('This device was signed out.')
      } else {
        setSessions((existing) => existing.filter((item) => item.id !== loginSession.id))
        setAccountMessage('Session signed out.')
      }
    } catch (error: unknown) { setAccountError(errorText(error)) }
    finally { setIsUpdatingAccount(false) }
  }

  async function handleProfileUpdate(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault(); setAccountError(null); setAccountMessage(null); setIsUpdatingAccount(true)
    try {
      setCurrentUser(await updateAccount(accountDisplayName))
      setAccountMessage('Profile updated.')
    } catch (error: unknown) { setAccountError(errorText(error)) }
    finally { setIsUpdatingAccount(false) }
  }

  async function handlePasswordChange(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault(); setAccountError(null); setAccountMessage(null); setIsUpdatingAccount(true)
    try {
      await changePassword(currentPassword, accountNewPassword)
      clearAccessToken(); setCurrentUser(null); setShowAccount(false)
      setCurrentPassword(''); setAccountNewPassword('')
      setAuthMessage('Password changed. Sign in again with your new password.')
    } catch (error: unknown) { setAccountError(errorText(error)) }
    finally { setIsUpdatingAccount(false) }
  }

  async function handleLogoutAll(): Promise<void> {
    setAccountError(null); setIsUpdatingAccount(true)
    try {
      await logoutAllDevices(); setCurrentUser(null); setShowAccount(false)
      setAuthMessage('All sessions were signed out.')
    } catch (error: unknown) { setAccountError(errorText(error)) }
    finally { setIsUpdatingAccount(false) }
  }

  async function handleDisableAccount(): Promise<void> {
    setAccountError(null); setIsUpdatingAccount(true)
    try {
      await disableAccount(); setCurrentUser(null); setShowAccount(false)
      setAuthMessage('Your account has been disabled.')
    } catch (error: unknown) { setAccountError(errorText(error)) }
    finally { setIsUpdatingAccount(false) }
  }

  async function handleCreateCharacter(): Promise<void> {
    setErrorMessage(null); setCreatedCharacter(null); setNameError(null)
    if (characterName.trim() === '') { setNameError('Please enter a character name.'); return }
    setIsCreating(true)
    try {
      const created = await createCharacter({ name: characterName, character_class: selectedClass })
      setCreatedCharacter(created)
      setRoster((current) => current === null ? null : [...current, created])
    } catch (error: unknown) { setErrorMessage(errorText(error)) }
    finally { setIsCreating(false) }
  }

  async function handleLoadRoster(): Promise<void> {
    setRosterError(null); setIsRosterLoading(true)
    try { setRoster(await fetchCharacters()) }
    catch (error: unknown) { setRosterError(errorText(error)) }
    finally { setIsRosterLoading(false) }
  }

  async function handleLoadCharacterCount(): Promise<void> {
    try { setCharacterCount((await fetchCharacterCount()).count) }
    catch (error: unknown) { setRosterError(errorText(error)) }
  }

  async function handleDeleteCharacter(characterId: number): Promise<void> {
    setRosterError(null); setRosterMessage(null)
    try {
      await deleteCharacter(characterId)
      setRoster((current) => current?.filter((character) => character.id !== characterId) ?? null)
      setCharacterCount((current) => current === null ? null : Math.max(0, current - 1))
    } catch (error: unknown) { setRosterError(errorText(error)) }
  }

  async function handleRestCharacter(characterId: number): Promise<void> {
    setRosterError(null); setRosterMessage(null); setRestingCharacterId(characterId)
    try {
      const restedCharacter = await restCharacter(characterId)
      setRoster((current) => current?.map((character) => character.id === characterId ? restedCharacter : character) ?? null)
      setCreatedCharacter((current) => current?.id === characterId ? restedCharacter : current)
      setRosterMessage(`${restedCharacter.name} rested and recovered health.`)
    } catch (error: unknown) { setRosterError(errorText(error)) }
    finally { setRestingCharacterId(null) }
  }

  async function handleReviveCharacter(characterId: number): Promise<void> {
    setRosterError(null); setRosterMessage(null); setRevivingCharacterId(characterId)
    try {
      const revivedCharacter = await reviveCharacter(characterId)
      setRoster((current) => current?.map((character) => character.id === characterId ? revivedCharacter : character) ?? null)
      setCreatedCharacter((current) => current?.id === characterId ? revivedCharacter : current)
      setRosterMessage(`${revivedCharacter.name} was revived with ${revivedCharacter.health} HP.`)
    } catch (error: unknown) { setRosterError(errorText(error)) }
    finally { setRevivingCharacterId(null) }
  }

  async function handleLevelUpCharacter(characterId: number): Promise<void> {
    setRosterError(null); setRosterMessage(null); setLevelingCharacterId(characterId)
    try {
      const leveledCharacter = await levelUpCharacter(characterId)
      setRoster((current) => current?.map((character) => character.id === characterId ? leveledCharacter : character) ?? null)
      setCreatedCharacter((current) => current?.id === characterId ? leveledCharacter : current)
      setRosterMessage(`${leveledCharacter.name} reached level ${leveledCharacter.level}.`)
    } catch (error: unknown) { setRosterError(errorText(error)) }
    finally { setLevelingCharacterId(null) }
  }

  async function handleRenameCharacter(characterId: number): Promise<void> {
    const name = editedCharacterName.trim()
    if (name === '') { setRosterError('Please enter a character name.'); return }
    setRosterError(null); setRosterMessage(null); setIsRenaming(true)
    try {
      const renamedCharacter = await renameCharacter(characterId, name)
      setRoster((current) => current?.map((character) => character.id === characterId ? renamedCharacter : character) ?? null)
      setCreatedCharacter((current) => current?.id === characterId ? renamedCharacter : current)
      setRosterMessage(`Character renamed to ${renamedCharacter.name}.`)
      setEditingCharacterId(null)
    } catch (error: unknown) { setRosterError(errorText(error)) }
    finally { setIsRenaming(false) }
  }

  async function handleFight(characterId: number, monsterSlug: string): Promise<void> {
    setCombatError(null); setFightResult(null); setIsFighting(true)
    try {
      const result = await fightMonster(characterId, monsterSlug)
      setFightResult(result)
      setRoster((current) => current?.map((character) => character.id === characterId ? { ...character, health: result.character_health } : character) ?? null)
      setCreatedCharacter((current) => current?.id === characterId ? { ...current, health: result.character_health } : current)
    } catch (error: unknown) { setCombatError(errorText(error)) }
    finally { setIsFighting(false) }
  }

  if (isRestoringSession) return <main><h1>TinyRPG</h1><p>Checking session...</p></main>

  if (currentUser === null) {
    return <main><h1>TinyRPG</h1><section className="auth-panel">
      <h2>{authMode === 'login' ? 'Sign in' : authMode === 'register' ? 'Create account' : authMode === 'verify' ? 'Verify your email' : authMode === 'forgot' ? 'Forgot password' : 'Choose a new password'}</h2>
      {(authMode === 'login' || authMode === 'register') && <form className="auth-form" onSubmit={(event) => void handleAuthentication(event)}>
          <label htmlFor="email">Email</label>
          <input id="email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
          {authMode === 'register' && <><label htmlFor="display-name">Display name</label><input id="display-name" required value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></>}
          <label htmlFor="password">Password</label>
          <input id="password" type="password" required minLength={authMode === 'register' ? 8 : 1} value={password} onChange={(event) => setPassword(event.target.value)} />
          <button type="submit" disabled={isAuthenticating}>{isAuthenticating ? 'Please wait...' : authMode === 'login' ? 'Sign in' : 'Register'}</button>
        </form>}
      {authMode === 'forgot' && <form className="auth-form" onSubmit={(event) => void handlePasswordResetRequest(event)}>
        <p>Enter your account email. The response is the same whether the account exists.</p>
        <label htmlFor="reset-email">Email</label>
        <input id="reset-email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
        <button type="submit" disabled={isAuthenticating}>{isAuthenticating ? 'Requesting...' : 'Request password reset'}</button>
      </form>}
      {authMode === 'verify' && <form className="auth-form" onSubmit={(event) => void handleEmailVerification(event)}>
        <p>Enter the token from your verification email.</p>
        <label htmlFor="verification-token">Verification token</label>
        <input id="verification-token" required value={verificationToken} onChange={(event) => setVerificationToken(event.target.value)} />
        <button type="submit" disabled={isAuthenticating}>{isAuthenticating ? 'Verifying...' : 'Verify email'}</button>
        <button type="button" disabled={isAuthenticating || email === ''} onClick={() => void handleVerificationRequest()}>Request another token</button>
      </form>}
      {authMode === 'reset' && <form className="auth-form" onSubmit={(event) => void handlePasswordResetConfirm(event)}>
        <label htmlFor="reset-token">Reset token</label>
        <input id="reset-token" required value={resetToken} onChange={(event) => setResetToken(event.target.value)} />
        <label htmlFor="new-password">New password</label>
        <input id="new-password" type="password" required minLength={8} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
        <button type="submit" disabled={isAuthenticating}>{isAuthenticating ? 'Updating...' : 'Update password'}</button>
      </form>}
      {authError !== null && <p role="alert">{authError}</p>}
      {authMessage !== null && <p role="status">{authMessage}</p>}
      {authMode === 'login' && <><button className="link-button" type="button" onClick={() => changeAuthMode('register')}>Need an account? Register</button><button className="link-button" type="button" onClick={() => changeAuthMode('forgot')}>Forgot password?</button></>}
      {authMode !== 'login' && <button className="link-button" type="button" onClick={() => changeAuthMode('login')}>Back to sign in</button>}
    </section></main>
  }

  if (showAccount) {
    return <main><h1>TinyRPG</h1><section className="account-panel">
      <div className="account-heading"><h2>Account</h2><button type="button" onClick={() => setShowAccount(false)}>Back to game</button></div>
      <dl className="account-details">
        <div><dt>Email</dt><dd>{currentUser.email}</dd></div>
        <div><dt>Role</dt><dd>{currentUser.role}</dd></div>
        <div><dt>Email status</dt><dd>{currentUser.email_verified ? 'Verified' : 'Not verified'}</dd></div>
        <div><dt>Member since</dt><dd>{new Date(currentUser.created_at).toLocaleDateString()}</dd></div>
      </dl>
      <form className="account-form" onSubmit={(event) => void handleProfileUpdate(event)}>
        <h3>Profile</h3><label htmlFor="account-display-name">Display name</label>
        <input id="account-display-name" required value={accountDisplayName} onChange={(event) => setAccountDisplayName(event.target.value)} />
        <button type="submit" disabled={isUpdatingAccount}>Save profile</button>
      </form>
      <form className="account-form" onSubmit={(event) => void handlePasswordChange(event)}>
        <h3>Change password</h3><label htmlFor="current-password">Current password</label>
        <input id="current-password" type="password" required value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />
        <label htmlFor="account-new-password">New password</label>
        <input id="account-new-password" type="password" required minLength={8} value={accountNewPassword} onChange={(event) => setAccountNewPassword(event.target.value)} />
        <button type="submit" disabled={isUpdatingAccount}>Change password</button>
      </form>
      <section className="account-actions"><h3>Sessions</h3>
        {areSessionsLoading && <p>Loading sessions…</p>}
        {!areSessionsLoading && sessions.length === 0 && <p>No active sessions found.</p>}
        <ul className="session-list">{sessions.map((loginSession) => <li key={loginSession.id}>
          <div><strong>{loginSession.current ? 'This device' : 'Signed-in device'}</strong><span>{loginSession.user_agent}</span><span>IP: {loginSession.ip_address}</span><span>Last active: {new Date(loginSession.last_seen_at).toLocaleString()}</span></div>
          <button type="button" disabled={isUpdatingAccount} onClick={() => void handleRevokeSession(loginSession)}>Log out</button>
        </li>)}</ul>
        <button type="button" disabled={isUpdatingAccount} onClick={() => void handleLogoutAll()}>Log out on every device</button>
      </section>
      <section className="account-actions"><h3>Recent security activity</h3>
        {areSessionsLoading && <p>Loading activity…</p>}
        {!areSessionsLoading && securityEvents.length === 0 && <p>No security activity recorded yet.</p>}
        <ul className="security-event-list">{securityEvents.map((event) => <li key={event.id}>
          <strong>{event.event_type.replaceAll('_', ' ')}</strong>
          <span>{new Date(event.created_at).toLocaleString()}</span>
          <span>{event.user_agent} · {event.ip_address}</span>
        </li>)}</ul>
      </section>
      <section className="danger-zone"><h3>Disable account</h3>
        {!confirmDisable ? <button type="button" onClick={() => setConfirmDisable(true)}>Disable my account</button> : <><p>This immediately blocks sign-in and all authenticated requests.</p><button type="button" disabled={isUpdatingAccount} onClick={() => void handleDisableAccount()}>Yes, disable my account</button><button type="button" onClick={() => setConfirmDisable(false)}>Cancel</button></>}
      </section>
      {accountError !== null && <p role="alert">{accountError}</p>}{accountMessage !== null && <p role="status">{accountMessage}</p>}
    </section></main>
  }

  const availableFighters = roster ?? (createdCharacter === null ? [] : [createdCharacter])
  const selectedFighter = chosenFighter ?? availableFighters[0]?.id ?? null
  const selectedMonster = chosenMonster ?? monsters[0]?.slug ?? ''

  return <main>
    <h1>TinyRPG</h1>
    <div className="session-bar"><span>Signed in as <strong>{currentUser.display_name}</strong> ({currentUser.role})</span><div><button type="button" onClick={() => void openAccount()}>Account</button><button type="button" onClick={() => void handleLogout()}>Log out</button></div></div>
    <p>Create your character</p>
    <form className="character-form" onSubmit={(event) => { event.preventDefault(); void handleCreateCharacter() }}>
      <label htmlFor="character-name">Name</label>
      <input id="character-name" type="text" required value={characterName} onChange={(event) => { setCharacterName(event.target.value); setNameError(null) }} aria-invalid={nameError !== null} aria-describedby={nameError !== null ? 'name-error' : undefined} />
      {nameError !== null && <p id="name-error" role="alert">{nameError}</p>}
      <h2>Available Classes</h2><label htmlFor="character-class">Class</label>
      <select id="character-class" value={selectedClass} onChange={(event) => setChosenClass(event.target.value)}>{characterClasses.map((characterClass) => <option key={characterClass} value={characterClass}>{characterClass}</option>)}</select>
      <button type="submit" disabled={isLoading || isCreating || selectedClass === ''}>{isCreating ? 'Creating...' : 'Create Character'}</button>
    </form>
    {createdCharacter !== null && <CharacterSummary id={createdCharacter.id} name={createdCharacter.name} characterClass={createdCharacter.character_class} health={createdCharacter.health} level={createdCharacter.level} />}
    {classError !== null && <p role="alert">{classError}</p>}{errorMessage !== null && <p role="alert">{errorMessage}</p>}{isLoading && <p>Loading classes...</p>}
    <section><h2>Character roster</h2>
      <button type="button" disabled={isRosterLoading} onClick={() => void handleLoadRoster()}>{isRosterLoading ? 'Loading roster...' : 'Load roster'}</button>
      <button type="button" onClick={() => void handleLoadCharacterCount()}>Load character count</button>
      {characterCount !== null && <p>Characters created: {characterCount}</p>}{rosterError !== null && <p role="alert">{rosterError}</p>}
      {rosterMessage !== null && <p role="status">{rosterMessage}</p>}
      {roster !== null && (roster.length === 0 ? <p>No characters created yet.</p> : <ul>{roster.map((character) => <li key={character.id}>
        {character.name} — {character.character_class} — Level {character.level} — {character.health} HP
        {character.health === 0
          ? <button type="button" disabled={revivingCharacterId === character.id} onClick={() => void handleReviveCharacter(character.id)}>{revivingCharacterId === character.id ? 'Reviving...' : 'Revive'}</button>
          : <button type="button" disabled={restingCharacterId === character.id || character.health >= (classHealth[character.character_class] ?? Infinity)} onClick={() => void handleRestCharacter(character.id)}>{restingCharacterId === character.id ? 'Resting...' : 'Rest'}</button>}
        <button type="button" disabled={levelingCharacterId === character.id} onClick={() => void handleLevelUpCharacter(character.id)}>{levelingCharacterId === character.id ? 'Leveling...' : 'Level Up'}</button>
        <button type="button" onClick={() => { setEditingCharacterId(character.id); setEditedCharacterName(character.name); setRosterError(null); setRosterMessage(null) }}>Rename</button>
        <button type="button" onClick={() => void handleDeleteCharacter(character.id)}>Delete</button>
        {editingCharacterId === character.id && <form onSubmit={(event) => { event.preventDefault(); void handleRenameCharacter(character.id) }}>
          <label htmlFor={`rename-character-${character.id}`}>New name for {character.name}</label>
          <input id={`rename-character-${character.id}`} value={editedCharacterName} maxLength={30} required onChange={(event) => setEditedCharacterName(event.target.value)} />
          <button type="submit" disabled={isRenaming}>{isRenaming ? 'Saving...' : 'Save name'}</button>
          <button type="button" disabled={isRenaming} onClick={() => setEditingCharacterId(null)}>Cancel</button>
        </form>}
      </li>)}</ul>)}
    </section>
    <section className="combat-panel"><h2>Monster arena</h2>
      <div className="combat-controls">
        <label htmlFor="fighter">Fighter</label>
        <select id="fighter" value={selectedFighter ?? ''} onChange={(event) => setChosenFighter(Number(event.target.value))} disabled={availableFighters.length === 0}>
          {availableFighters.map((character) => <option key={character.id} value={character.id}>{character.name} — {character.health} HP</option>)}
        </select>
        <label htmlFor="monster">Monster</label>
        <select id="monster" value={selectedMonster} onChange={(event) => setChosenMonster(event.target.value)} disabled={monsters.length === 0}>
          {monsters.map((monster) => <option key={monster.slug} value={monster.slug}>{monster.name} — {monster.health} HP / {monster.damage} damage</option>)}
        </select>
        <button type="button" disabled={isFighting || selectedFighter === null || selectedMonster === ''} onClick={() => selectedFighter !== null && void handleFight(selectedFighter, selectedMonster)}>{isFighting ? 'Fighting...' : 'Fight'}</button>
      </div>
      {availableFighters.length === 0 && <p>Create a character or load your roster to enter the arena.</p>}
      {combatError !== null && <p role="alert">{combatError}</p>}
      {fightResult !== null && <div className="combat-result" role="status">
        <h3>{fightResult.victory ? `Victory over the ${fightResult.monster.name}!` : `Defeated by the ${fightResult.monster.name}`}</h3>
        <p>Remaining health: {fightResult.character_health}</p>
        <ol>{fightResult.rounds.map((round) => <li key={round.round_number}>Round {round.round_number}: rolled {round.character_roll} ({round.outcome}), dealt {round.character_damage}; monster dealt {round.monster_damage}. You: {round.character_health} HP, monster: {round.monster_health} HP.</li>)}</ol>
      </div>}
    </section>
  </main>
}

export default App
