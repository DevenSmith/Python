import './App.css'

type CharacterSummaryProps = {
  name: string
  startingHealth: number
}

function App() {
  const characterName = 'Deven'
  const startingHealth = 120

  return (
    <main>
      <h1>TinyRPG</h1>
      <p>Create your character</p>
      <CharacterSummary
        name={characterName}
        startingHealth={startingHealth}
      />
    </main>
  )
}

function CharacterSummary(props: CharacterSummaryProps) {
  return (
    <section>
      <p>Name: {props.name}</p>
      <p>Starting Health: {props.startingHealth}</p>
    </section>
  )
}

export default App