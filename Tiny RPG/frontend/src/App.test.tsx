import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { fetchClasses } from './api/tinyrpgApi'

vi.mock('./api/tinyrpgApi', () => ({
    fetchClasses: vi.fn(),
    createCharacter: vi.fn(),
}))

const mockedFetchClasses = vi.mocked(fetchClasses)

describe('App', () => {
    beforeEach(() => {
        mockedFetchClasses.mockReset()
    })

    it('loads character classes from the API', async () => {
        mockedFetchClasses.mockResolvedValue({
            Warrior: 120,
            Mage: 80,
            Rogue: 100,
        })

        render(<App />)

        expect(
            await screen.findByRole('option', { name: 'Warrior' }),
        ).toBeInTheDocument()
        expect(screen.getByRole('option', { name: 'Mage' })).toBeInTheDocument()
        expect(screen.getByRole('option', { name: 'Rogue' })).toBeInTheDocument()
    })

    it('displays an error when classes fail to load', async () => {
        mockedFetchClasses.mockRejectedValue(new Error('API unavailable'))

        render(<App />)

        expect(await screen.findByRole('alert')).toHaveTextContent(
            'API unavailable',
        )
    })
})