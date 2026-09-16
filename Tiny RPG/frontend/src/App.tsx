import { useEffect, useState, type FormEvent } from 'react'
import './App.css'
import CharacterSummary from './components/CharacterSummary'
import {
  AUTH_EXPIRED_EVENT, clearAccessToken, createCharacter, deleteCharacter,
  fetchCharacterCount, fetchCharacters, fetchCurrentUser, logout,
  login, registerUser, restoreCurrentUser, storeAccessToken,
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
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState<string | null>(null)
  const [isAuthenticating, setIsAuthenticating] = useState(false)
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
      if (authMode === 'register') await registerUser({ email, display_name: displayName, password })
      const token = await login({ email, password })
      storeAccessToken(token.access_token)
      setCurrentUser(await fetchCurrentUser())
      setPassword('')
    } catch (error: unknown) { clearAccessToken(); setAuthError(errorText(error)) }
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
      <h2>{authMode === 'login' ? 'Sign in' : 'Create account'}</h2>
      <form className="auth-form" onSubmit={(event) => void handleAuthentication(event)}>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
        {authMode === 'register' && <><label htmlFor="display-name">Display name</label><input id="display-name" required value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></>}
        <label htmlFor="password">Password</label>
        <input id="password" type="password" required minLength={authMode === 'register' ? 8 : 1} value={password} onChange={(event) => setPassword(event.target.value)} />
        <button type="submit" disabled={isAuthenticating}>{isAuthenticating ? 'Please wait...' : authMode === 'login' ? 'Sign in' : 'Register'}</button>
      </form>
      {authError !== null && <p role="alert">{authError}</p>}
      <button className="link-button" type="button" onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setAuthError(null) }}>{authMode === 'login' ? 'Need an account? Register' : 'Already registered? Sign in'}</button>
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
