import './App.css'
import { useState } from 'react'

type CharacterSummaryProps = {
  name: string
  startingHealth: number
}

function App() {
  const characterName = 'Deven'
  const [startingHealth, setStartingHealth] = useState(120)

  return (
    <main>
      <h1>TinyRPG</h1>
      <p>Create your character</p>
      <CharacterSummary
        name={characterName}
        startingHealth={startingHealth}
      />

      <button
        type="button"
        onClick={() => setStartingHealth(startingHealth + 10)}
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