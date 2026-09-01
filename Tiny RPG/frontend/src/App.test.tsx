import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { createCharacter, deleteCharacter, fetchCharacterCount, fetchCharacters, fetchClasses } from './api/tinyrpgApi'


vi.mock('./api/tinyrpgApi', () => ({
    fetchClasses: vi.fn(),
    createCharacter: vi.fn(),
    fetchCharacters: vi.fn(),
    deleteCharacter: vi.fn(),
    fetchCharacterCount: vi.fn(),
}))

const mockedFetchClasses = vi.mocked(fetchClasses)
const mockedCreateCharacter = vi.mocked(createCharacter)
const mockedFetchCharacters = vi.mocked(fetchCharacters)
const mockedDeleteCharacter = vi.mocked(deleteCharacter)
const mockedFetchCharacterCount = vi.mocked(fetchCharacterCount)

describe('App', () => {
    beforeEach(() => {
        mockedFetchClasses.mockReset()
        mockedCreateCharacter.mockReset()
        mockedFetchCharacters.mockReset()
        mockedDeleteCharacter.mockReset()
        mockedFetchCharacterCount.mockReset()
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

    it('shows a message when the roster is empty', async () => {
        const user = userEvent.setup()

        mockedFetchClasses.mockResolvedValue({ Warrior: 120 })
        mockedFetchCharacters.mockResolvedValue([])

        render(<App />)

        await screen.findByRole('option', { name: 'Warrior' })

        expect(
            screen.queryByText('No characters created yet.'),
        ).not.toBeInTheDocument()

        await user.click(
            screen.getByRole('button', { name: 'Load roster' }),
        )

        expect(
            await screen.findByText('No characters created yet.'),
        ).toBeInTheDocument()
    })

    it('displays characters from the roster', async () => {
        const user = userEvent.setup()
        mockedFetchClasses.mockResolvedValue({ Warrior: 120 })

        mockedFetchCharacters.mockResolvedValue(
            [
                {
                    id: 1,
                    name: 'Avery',
                    character_class: 'Mage',
                    health: 80,
                    level: 1,
                },
                {
                    id: 2,
                    name: 'Deven',
                    character_class: 'Warrior',
                    health: 120,
                    level: 1,
                },
            ]
        )

        render(<App />)

        await screen.findByRole('option', { name: 'Warrior' })

        await user.click(
            screen.getByRole('button', { name: 'Load roster' }),
        )

        expect(
            await screen.findByText('Avery — Mage'),
        ).toBeInTheDocument()

        expect(
            screen.getByText('Deven — Warrior'),
        ).toBeInTheDocument()
    })

    it('displays an error when roster loading fails', async () => {
        const user = userEvent.setup()

        mockedFetchClasses.mockResolvedValue({
            Warrior: 120,
        })

        mockedFetchCharacters.mockRejectedValue(
            new Error('Unable to load roster'),
        )

        render(<App />)

        await screen.findByRole('option', { name: 'Warrior' })

        await user.click(
            screen.getByRole('button', { name: 'Load roster' }),
        )

        expect(await screen.findByRole('alert')).toHaveTextContent(
            'Unable to load roster',
        )
    })

    it('adds a created character to an already loaded roster', async () => {
        const user = userEvent.setup()

        mockedFetchClasses.mockResolvedValue({
            Warrior: 120,
        })

        mockedFetchCharacters.mockResolvedValue([])

        mockedCreateCharacter.mockResolvedValue({
            id: 1,
            name: 'Deven',
            character_class: 'Warrior',
            health: 120,
            level: 1,
        })

        render(<App />)

        await screen.findByRole('option', { name: 'Warrior' })

        await user.click(
            screen.getByRole('button', { name: 'Load roster' }),
        )

        expect(
            await screen.findByText('No characters created yet.'),
        ).toBeInTheDocument()

        await user.click(
            screen.getByRole('button', { name: 'Create Character' }),
        )

        expect(
            await screen.findByText('Deven — Warrior'),
        ).toBeInTheDocument()

        expect(mockedFetchCharacters).toHaveBeenCalledTimes(1)
    })

    it('removes a deleted character from the roster', async () => {
        const user = userEvent.setup()

        mockedFetchClasses.mockResolvedValue({
            Warrior: 120,
        })

        mockedFetchCharacters.mockResolvedValue([
            {
                id: 1,
                name: 'Avery',
                character_class: 'Warrior',
                health: 120,
                level: 1,
            },
        ])

        mockedDeleteCharacter.mockResolvedValue({
            message: 'Character deleted',
        })

        render(<App />)

        await screen.findByRole('option', { name: 'Warrior' })

        await user.click(
            screen.getByRole('button', { name: 'Load roster' }),
        )

        expect(
            await screen.findByText('Avery — Warrior'),
        ).toBeInTheDocument()

        await user.click(
            screen.getByRole('button', { name: 'Delete' }),
        )

        expect(mockedDeleteCharacter).toHaveBeenCalledWith(1)

        await waitFor(() => {
            expect(
                screen.queryByText('Avery — Warrior'),
            ).not.toBeInTheDocument()
        })
    })
})