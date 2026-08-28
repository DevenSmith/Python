import { useState } from 'react'
import './App.css'

type CharacterSummaryProps = {
  name: string
  characterClass: string
  startingHealth: number
}

const CLASS_HEALTH: Record<string, number> = {
  Warrior: 120,
  Mage: 80,
  Rogue: 100,
}

function App() {
  const [classHealth, setClassHealth] =
    useState<Record<string, number>>(CLASS_HEALTH)
  const [characterName, setCharacterName] = useState('Deven')
  const characterClasses = Object.keys(classHealth)
  const [selectedClass, setSelectedClass] = useState('Warrior')
  const startingHealth = classHealth[selectedClass]
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

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

      setClassHealth(loadedClassHealth)
    } catch (error: unknown) {
      if (error instanceof Error) {
        setErrorMessage(error.message)
      } else {
        setErrorMessage('An unknown error occurred')
      }
    }finally {
      setIsLoading(false)
    }
  }

  return (
    <main>
      <h1>TinyRPG</h1>
      <p>Create your character</p>

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

      <CharacterSummary
        name={characterName}
        characterClass={selectedClass}
        startingHealth={startingHealth}
      />

      <button type="button" onClick={loadClasses} disabled={isLoading}>
        {isLoading ? 'Loading...' : 'Load Classes from API'}
      </button>

      {errorMessage !== null && <p role="alert">{errorMessage}</p>}
    </main>
  )
}

function CharacterSummary({
  name,
  characterClass,
  startingHealth,
}: CharacterSummaryProps) {
  return (
    <section>
      <p>Name: {name}</p>
      <p>Character Class: {characterClass}</p>
      <p>Starting Health: {startingHealth}</p>
    </section>
  )
}

export default App