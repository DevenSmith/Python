import { useEffect, useState } from 'react'
import './App.css'
import CharacterSummary from './components/CharacterSummary'
import {
  createCharacter,
  fetchClasses,
  type CharacterResponse,
  type ClassHealth,
} from './api/tinyrpgApi'

function App() {
  const [classHealth, setClassHealth] =
    useState<ClassHealth>({})
  const [characterName, setCharacterName] = useState('Deven')
  const characterClasses = Object.keys(classHealth)
  const [selectedClass, setSelectedClass] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [createdCharacter, setCreatedCharacter] =
    useState<CharacterResponse | null>(null)
  const [isCreating, setIsCreating] = useState(false)

  useEffect(() => {
    async function loadClasses(): Promise<void> {
      setErrorMessage(null)
      setIsLoading(true)

      try {
        const loadedClassHealth = await fetchClasses()

        const firstClass = Object.keys(loadedClassHealth)[0]

        if (firstClass === undefined) {
          throw new Error('The API returned no character classes')
        }

        setClassHealth(loadedClassHealth)
        setSelectedClass(firstClass)
      } catch (error: unknown) {
        if (error instanceof Error) {
          setErrorMessage(error.message)
        } else {
          setErrorMessage('An unknown error occurred')
        }
      } finally {
        setIsLoading(false)
      }
    }

    void loadClasses()
  }, [])

  async function handleCreateCharacter(): Promise<void> {
    setErrorMessage(null)
    setCreatedCharacter(null)
    setIsCreating(true)

    try {
      const createdCharacterResponse = await createCharacter({
        name: characterName,
        character_class: selectedClass,
      })

      setCreatedCharacter(createdCharacterResponse)
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

  return (
    <main>
      <h1>TinyRPG</h1>
      <p>Create your character</p>

      <form
        onSubmit={(event) => {
          event.preventDefault()
          void handleCreateCharacter()
        }}
      >
        <label htmlFor="character-name">Name</label>
        <input
          id="character-name"
          type="text"
          value={characterName}
          onChange={(event) => setCharacterName(event.target.value)}
        />

        <h2>Available Classes</h2>

        <label htmlFor="character-class">Class</label>
        <select
          id="character-class"
          value={selectedClass}
          onChange={(event) => setSelectedClass(event.target.value)}
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

      {errorMessage !== null && <p role="alert">{errorMessage}</p>}
      {isLoading && <p>Loading classes...</p>}
    </main>
  )
}

export default App