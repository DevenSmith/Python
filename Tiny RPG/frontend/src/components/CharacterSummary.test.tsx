import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import CharacterSummary from './CharacterSummary'

describe('CharacterSummary', () => {
    it('displays the created character', () => {
        render(
            <CharacterSummary
                id={1}
                name="Deven"
                characterClass="Warrior"
                health={120}
                level={1}
            />,
        )
        expect(screen.getByText('Name: Deven')).toBeInTheDocument()
        expect(screen.getByText('Class: Warrior')).toBeInTheDocument()
    })
})