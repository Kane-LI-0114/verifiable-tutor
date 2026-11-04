/** Install an in-memory Storage on `window.localStorage` for jsdom tests. */
export function installMemoryStorage(): Storage {
  // The Node runtime behind this jsdom environment exposes a broken
  // localStorage global, so tests that read or write it install their own.
  const data = new Map<string, string>();
  const storage: Storage = {
    get length() {
      return data.size;
    },
    clear: () => data.clear(),
    getItem: (key: string) => data.get(key) ?? null,
    key: (index: number) => Array.from(data.keys())[index] ?? null,
    removeItem: (key: string) => {
      data.delete(key);
    },
    setItem: (key: string, value: string) => {
      data.set(key, String(value));
    },
  };
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: storage,
  });
  return storage;
}
