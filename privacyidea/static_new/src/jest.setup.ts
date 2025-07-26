import { setupZonelessTestEnv } from 'jest-preset-angular/setup-env/zoneless';
setupZonelessTestEnv();

global.console = {
  ...global.console,
  log: jest.fn(),
  error: jest.fn(),
  warn: jest.fn(),
  info: jest.fn(),
  debug: jest.fn(),
};

const realConsoleError = console.error;

console.error = (...args: unknown[]) => {
  if (
    typeof args[0] === 'string' &&
    args[0].includes('Error: Could not parse CSS stylesheet')
  ) {
    return;
  }
  realConsoleError(...args);
};
