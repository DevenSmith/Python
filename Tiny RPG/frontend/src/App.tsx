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
  const [characterName, setCharacterName] = useState('Deven')
  const characterClasses = Object.keys(CLASS_HEALTH)
  const [selectedClass, setSelectedClass] = useState('Warrior')
  const startingHealth = CLASS_HEALTH[selectedClass]

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