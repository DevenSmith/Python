import { useState } from 'react'
import './App.css'

type CharacterSummaryProps = {
  name: string
  startingHealth: number
}

function App() {
  const [characterName, setCharacterName] = useState('Deven')
  const [startingHealth, setStartingHealth] = useState(120)

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

      <CharacterSummary
        name={characterName}
        startingHealth={startingHealth}
      />

      <button
        type="button"
        onClick={() => setStartingHealth((currentHealth) => currentHealth + 10)}
      >
        Add 10 Health
      </button>
    </main>
  )
}

function CharacterSummary({ name, startingHealth }: CharacterSummaryProps) {
  return (
    <section>
      <p>Name: {name}</p>
      <p>Starting Health: {startingHealth}</p>
    </section>
  )
}

export default App