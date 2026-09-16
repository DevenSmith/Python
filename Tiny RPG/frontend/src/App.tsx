import { useEffect, useState, type FormEvent } from 'react'
import './App.css'
import CharacterSummary from './components/CharacterSummary'
import {
  AUTH_EXPIRED_EVENT, clearAccessToken, confirmPasswordReset, createCharacter, deleteCharacter,
  fetchCharacterCount, fetchCharacters, fetchCurrentUser, logout,
  login, registerUser, requestEmailVerification, requestPasswordReset,
  restoreCurrentUser, storeAccessToken, verifyEmail,
  type CharacterResponse, type UserResponse,
} from './api/tinyrpgApi'
import { useCharacterClasses } from './hooks/useCharacterClasses'

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : 'An unknown error occurred'
}

function App() {
  const { classHealth, isLoading, classError } = useCharacterClasses()
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null)
  const [isRestoringSession, setIsRestoringSession] = useState(true)
  const [authMode, setAuthMode] = useState<'login' | 'register' | 'verify' | 'forgot' | 'reset'>('login')
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState<string | null>(null)
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [resetToken, setResetToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [authMessage, setAuthMessage] = useState<string | null>(null)
  const [verificationToken, setVerificationToken] = useState('')
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
  const [characterCount, setCharacterCount] = useState<number | null>(null)

  useEffect(() => {
    const expireSession = () => {
      setCurrentUser(null); setRoster(null); setCreatedCharacter(null)
      setAuthError('Your session has expired. Please sign in again.')
    }
    window.addEventListener(AUTH_EXPIRED_EVENT, expireSession)

    async function restoreSession(): Promise<void> {
      try { setCurrentUser(await restoreCurrentUser()) }
      catch (error: unknown) { clearAccessToken(); setAuthError(errorText(error)) }
      finally { setIsRestoringSession(false) }
    }
    void restoreSession()
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, expireSession)
  }, [])

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
      setVerificationToken(''); setAuthMode('login')
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
      setPassword(''); setNewPassword(''); setResetToken(''); setAuthMode('login')
      setAuthMessage('Password updated. You can now sign in with your new password.')
    } catch (error: unknown) { setAuthError(errorText(error)) }
    finally { setIsAuthenticating(false) }
  }

  async function handleLogout(): Promise<void> {
    await logout(); setCurrentUser(null); setRoster(null)
    setCreatedCharacter(null); setCharacterCount(null); setAuthError(null)
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
    setRosterError(null)
    try {
      await deleteCharacter(characterId)
      setRoster((current) => current?.filter((character) => character.id !== characterId) ?? null)
      setCharacterCount((current) => current === null ? null : Math.max(0, current - 1))
    } catch (error: unknown) { setRosterError(errorText(error)) }
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

  return <main>
    <h1>TinyRPG</h1>
    <div className="session-bar"><span>Signed in as <strong>{currentUser.display_name}</strong> ({currentUser.role})</span><button type="button" onClick={() => void handleLogout()}>Log out</button></div>
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
      {roster !== null && (roster.length === 0 ? <p>No characters created yet.</p> : <ul>{roster.map((character) => <li key={character.id}>{character.name} — {character.character_class}<button type="button" onClick={() => void handleDeleteCharacter(character.id)}>Delete</button></li>)}</ul>)}
    </section>
  </main>
}

export default App
