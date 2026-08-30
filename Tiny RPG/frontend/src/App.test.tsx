import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { createCharacter, fetchClasses } from './api/tinyrpgApi'


vi.mock('./api/tinyrpgApi', () => ({
    fetchClasses: vi.fn(),
    createCharacter: vi.fn(),
}))

const mockedFetchClasses = vi.mocked(fetchClasses)
const mockedCreateCharacter = vi.mocked(createCharacter)

describe('App', () => {
    beforeEach(() => {
        mockedFetchClasses.mockReset()
        mockedCreateCharacter.mockReset()
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

    it('allows the player to enter a character name', async () => {
        const user = userEvent.setup()

        mockedFetchClasses.mockResolvedValue({
            Warrior: 120,
        })

        render(<App />)

        await screen.findByRole('option', { name: 'Warrior' })

        const nameInput = screen.getByRole('textbox', { name: 'Name' })

        await user.clear(nameInput)
        await user.type(nameInput, 'Avery')

        expect(nameInput).toHaveValue('Avery')
    })

    it('submits the entered character to the API', async () => {
        const user = userEvent.setup()

        mockedFetchClasses.mockResolvedValue({
            Warrior: 120,
            Mage: 80,
        })

        mockedCreateCharacter.mockResolvedValue({
            id: 1,
            name: 'Avery',
            character_class: 'Mage',
            health: 80,
            level: 1,
        })

        render(<App />)

        await screen.findByRole('option', { name: 'Warrior' })

        const nameInput = screen.getByRole('textbox', { name: 'Name' })
        const classSelect = screen.getByRole('combobox', { name: 'Class' })

        await user.clear(nameInput)
        await user.type(nameInput, 'Avery')
        await user.selectOptions(classSelect, 'Mage')
        await user.click(
            screen.getByRole('button', { name: 'Create Character' }),
        )

        expect(mockedCreateCharacter).toHaveBeenCalledWith({
            name: 'Avery',
            character_class: 'Mage',
        })
        expect(await screen.findByText('Name: Avery')).toBeInTheDocument()
        expect(screen.getByText('Class: Mage')).toBeInTheDocument()
        expect(screen.getByText('Health: 80')).toBeInTheDocument()
    })

    it('displays an error when character creation fails', async () => {
        const user = userEvent.setup()

        mockedFetchClasses.mockResolvedValue({
            Warrior: 120,
            Mage: 80,
            Rogue: 100,
        })

        mockedCreateCharacter.mockRejectedValue(
            new Error('Unable to create character'),
        )

        render(<App />)

        expect(
            await screen.findByRole('option', { name: 'Warrior' }),
        ).toBeInTheDocument()

        await user.click(
            screen.getByRole('button', { name: 'Create Character' }),
        )

        expect(await screen.findByRole('alert')).toHaveTextContent(
            'Unable to create character',
        )
    })

    it('rejects a whitespace-only name', async () => {
        const user = userEvent.setup()
        mockedFetchClasses.mockResolvedValue({
            Warrior: 120,
            Mage: 80,
            Rogue: 100,
        })

        render(<App />)

        expect(
            await screen.findByRole('option', { name: 'Warrior' }),
        ).toBeInTheDocument()

        const nameInput = screen.getByRole('textbox', { name: 'Name' })
        await user.clear(nameInput)
        await user.type(nameInput, '   ')

        await user.click(
            screen.getByRole('button', { name: 'Create Character' }),
        )   

        expect(await screen.findByRole('alert')).toHaveTextContent(
            'Please enter a character name.',
        )
        expect(mockedCreateCharacter).not.toHaveBeenCalled()
        expect(nameInput).toHaveAttribute('aria-invalid', 'true')
        expect(nameInput).toHaveAccessibleDescription(
            'Please enter a character name.',
        )

        await user.clear(nameInput)
        await user.type(nameInput, 'Avery')

        expect(screen.queryByRole('alert')).not.toBeInTheDocument()
        expect(nameInput).toHaveAttribute('aria-invalid', 'false')
        expect(nameInput).not.toHaveAttribute('aria-describedby')
        expect(mockedCreateCharacter).not.toHaveBeenCalled()
    })
})