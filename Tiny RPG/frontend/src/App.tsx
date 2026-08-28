import { useEffect, useState } from 'react'
import './App.css'

type CharacterSummaryProps = {
  id: number
  name: string
  characterClass: string
  health: number
  level: number
}

type CharacterResponse = {
  id: number
  name: string
  character_class: string
  health: number
  level: number
}

function App() {
  const [classHealth, setClassHealth] =
    useState<Record<string, number>>({})
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
        const response = await fetch('http://127.0.0.1:8000/classes')

        if (!response.ok) {
          throw new Error(`Failed to load classes: ${response.status}`)
        }

        const loadedClassHealth =
          (await response.json()) as Record<string, number>

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

  async function createCharacter(): Promise<void> {
    setErrorMessage(null)
    setCreatedCharacter(null)
    setIsCreating(true)

    try {
      const response = await fetch('http://127.0.0.1:8000/characters', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: characterName,
          character_class: selectedClass,
        }),
      })

      if (!response.ok) {
        throw new Error(`Failed to create character: ${response.status}`)
      }

      const createdCharacterResponse =
        (await response.json()) as CharacterResponse

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
          void createCharacter()
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

function CharacterSummary({
  id,
  name,
  characterClass,
  health,
  level,
}: CharacterSummaryProps) {
  return (
    <section>
      <h2>Character Created!</h2>
      <p>ID: {id}</p>
      <p>Name: {name}</p>
      <p>Class: {characterClass}</p>
      <p>Health: {health}</p>
      <p>Level: {level}</p>
    </section>
  )
}

export default App