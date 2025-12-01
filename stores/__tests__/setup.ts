/**
 * Vitest setup for store tests
 */
import { vi } from 'vitest';

// Mock sessionStorage
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(global, 'sessionStorage', {
  value: sessionStorageMock,
});

// Reset mocks between tests
beforeEach(() => {
  sessionStorageMock.clear();
  vi.clearAllMocks();
});
