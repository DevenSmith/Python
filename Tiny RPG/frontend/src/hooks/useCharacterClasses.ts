import { useEffect, useState } from 'react'
import { fetchClasses, type ClassHealth } from '../api/tinyrpgApi'

export function useCharacterClasses() {
    const [classHealth, setClassHealth] = useState<ClassHealth>({})
    const [isLoading, setIsLoading] = useState(false)
    const [classError, setClassError] = useState<string | null>(null)


    useEffect(() => {
        async function loadClasses(): Promise<void> {
            setClassError(null)
            setIsLoading(true)

            try {
                const loadedClassHealth = await fetchClasses()

                const firstClass = Object.keys(loadedClassHealth)[0]

                if (firstClass === undefined) {
                    throw new Error('The API returned no character classes')
                }

                setClassHealth(loadedClassHealth)
            } catch (error: unknown) {
                if (error instanceof Error) {
                    setClassError(error.message)
                } else {
                    setClassError('An unknown error occurred')
                }
            } finally {
                setIsLoading(false)
            }
        }

        void loadClasses()
    }, [])

    return { classHealth, isLoading, classError }
}