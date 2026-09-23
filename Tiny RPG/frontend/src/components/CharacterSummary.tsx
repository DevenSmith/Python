type CharacterSummaryProps = {
  id: number
  name: string
  characterClass: string
  health: number
  level: number
  experience: number
  experienceToNextLevel: number | null
}

function CharacterSummary({
  id,
  name,
  characterClass,
  health,
  level,
  experience,
  experienceToNextLevel,
}: CharacterSummaryProps) {
  return (
    <section>
      <h2>Character Created!</h2>
      <p>ID: {id}</p>
      <p>Name: {name}</p>
      <p>Class: {characterClass}</p>
      <p>Health: {health}</p>
      <p>Level: {level}</p>
      <p>XP: {experience}{experienceToNextLevel === null ? ' (maximum level)' : ` / ${experienceToNextLevel}`}</p>
    </section>
  )
}

export default CharacterSummary
