export type ClassHealth = Record<string, number>

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

export async function fetchClasses(): Promise<ClassHealth> {
  const response = await fetch(`${API_BASE_URL}/classes`)

  if (!response.ok) {
    throw new Error(`Failed to load classes: ${response.status}`)
  }

  return (await response.json()) as ClassHealth
}

export type CharacterCreate = {
  name: string
  character_class: string
}

export type CharacterResponse = {
  id: number
  name: string
  character_class: string
  health: number
  level: number
}

export async function createCharacter(
  character: CharacterCreate,
): Promise<CharacterResponse> {
  const response = await fetch(`${API_BASE_URL}/characters`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(character),
  })

  if (!response.ok) {
    throw new Error(`Failed to create character: ${response.status}`)
  }

  return (await response.json()) as CharacterResponse
}