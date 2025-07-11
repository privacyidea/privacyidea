import { setupZonelessTestEnv } from 'jest-preset-angular/setup-env/zoneless';
setupZonelessTestEnv();

jest.spyOn(console, 'warn').mockImplementation(() => {});
