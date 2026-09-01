import { useState } from 'react'
import './App.css'
import CharacterSummary from './components/CharacterSummary'
import {
  createCharacter,
  fetchCharacters,
  fetchCharacterCount,
  type CharacterResponse,
} from './api/tinyrpgApi'
import { useCharacterClasses } from './hooks/useCharacterClasses'

function App() {
  const { classHealth, isLoading, classError } = useCharacterClasses()
  const [characterName, setCharacterName] = useState('Deven')
  const characterClasses = Object.keys(classHealth)
  const [chosenClass, setChosenClass] = useState<string | null>(null)
  const selectedClass = chosenClass ?? characterClasses[0] ?? ''
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [createdCharacter, setCreatedCharacter] =
    useState<CharacterResponse | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [nameError, setNameError] = useState<string | null>(null)
  const [roster, setRoster] = useState<CharacterResponse[] | null>(null)
  const [isRosterLoading, setIsRosterLoading] = useState(false)
  const [rosterError, setRosterError] = useState<string | null>(null)
  const [characterCount, setCharacterCount] = useState<number | null>(null)

  async function handleCreateCharacter(): Promise<void> {
    setErrorMessage(null)
    setCreatedCharacter(null)
    setNameError(null)

    if (characterName.trim() === '') {
      setNameError('Please enter a character name.')
      return
    }

    setIsCreating(true)

    try {
      const createdCharacterResponse = await createCharacter({
        name: characterName,
        character_class: selectedClass,
      })

      setCreatedCharacter(createdCharacterResponse)

      setRoster((currentRoster) => {
        if (currentRoster === null) {
          return null
        }

        return [...currentRoster, createdCharacterResponse]
      })
    } catch (error: unknown) {
      if (error instanceof Error) {
        setErrorMessage(error.message)
      } else {
        setErrorMessage('An unknown error occurred')
      }
    } finally {
      setIsCreating(false)
    }
  }

  async function handleLoadRoster(): Promise<void> {
    setRosterError(null)
    setIsRosterLoading(true)

    try {
      const characters = await fetchCharacters()
      setRoster(characters)
    } catch (error: unknown) {
      if (error instanceof Error) {
        setRosterError(error.message)
      } else {
        setRosterError('An unknown error occurred')
      }
    } finally {
      setIsRosterLoading(false)
    }
  }

  async function handleLoadCharacterCount(): Promise<void> {
    const response = await fetchCharacterCount()
    setCharacterCount(response.count)
  }

  return (
    <main>
      <h1>TinyRPG</h1>
      <p>Create your character</p>

      <form
        className="character-form"
        onSubmit={(event) => {
          event.preventDefault()
          void handleCreateCharacter()
        }}
      >
        <label htmlFor="character-name">Name</label>
        <input
          id="character-name"
          type="text"
          required
          value={characterName}
          onChange={(event) => {
            setCharacterName(event.target.value)
            setNameError(null)
          }}
          aria-invalid={nameError !== null}
          aria-describedby={nameError !== null ? 'name-error' : undefined}
        />
        {nameError !== null && (
          <p id="name-error" role="alert">
            {nameError}
          </p>
        )}

        <h2>Available Classes</h2>

        <label htmlFor="character-class">Class</label>
        <select
          id="character-class"
          value={selectedClass}
          onChange={(event) => setChosenClass(event.target.value)}
        >
          {characterClasses.map((characterClass) => (
            <option key={characterClass} value={characterClass}>
              {characterClass}
            </option>
          ))}
        </select>

        <button
          type="submit"
          disabled={
            isLoading ||
            isCreating ||
            selectedClass === ''
          }
        >
          {isCreating ? 'Creating...' : 'Create Character'}
        </button>
      </form>

      {createdCharacter !== null && (
        <CharacterSummary
          id={createdCharacter.id}
          name={createdCharacter.name}
          characterClass={createdCharacter.character_class}
          health={createdCharacter.health}
          level={createdCharacter.level}
        />
      )}

      {classError !== null && <p role="alert">{classError}</p>}
      {errorMessage !== null && <p role="alert">{errorMessage}</p>}
      {isLoading && <p>Loading classes...</p>}

      <section>
        <h2>Character roster</h2>

        <button
          type="button"
          disabled={isRosterLoading}
          onClick={() => {
            void handleLoadRoster()
          }}
        >
          {isRosterLoading ? 'Loading roster...' : 'Load roster'}
        </button>

        <button
          type="button"
          onClick={() => {
            void handleLoadCharacterCount()
          }}
        >
          Load character count
        </button>

        {characterCount !== null && (
          <p>Characters created: {characterCount}</p>
        )}

        {rosterError !== null && <p role="alert">{rosterError}</p>}

        {roster !== null && (
          roster.length === 0 ? (
            <p>No characters created yet.</p>
          ) : (
            <ul>
              {roster.map((character) => (
                <li key={character.id}>
                  {character.name} — {character.character_class}
                </li>
              ))}
            </ul>
          )
        )}
      </section>
    </main>
  )
}

export default App