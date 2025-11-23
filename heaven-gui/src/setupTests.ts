import '@testing-library/jest-dom'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// Ensure each test starts with a clean DOM
afterEach(() => {
  cleanup()
})
