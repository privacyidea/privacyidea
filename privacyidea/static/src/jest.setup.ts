/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import "@angular/localize/init";
import { setupZonelessTestEnv } from "jest-preset-angular/setup-env/zoneless";
import { webcrypto } from "node:crypto";
import { deserialize, serialize } from "node:v8";

setupZonelessTestEnv();

// jsdom provides no `crypto.subtle`, so tests fall back to Node's webcrypto. Node's
// implementation rejects ArrayBuffers/views created in the jsdom realm with
// "2nd argument is not instance of ArrayBuffer". Install Node webcrypto behind a proxy
// whose `digest` re-wraps the input in a Node-realm Buffer so cross-realm buffers from
// component and test code are accepted.
if (!globalThis.crypto?.subtle) {
  const real = webcrypto as unknown as Crypto;
  const realDigest = real.subtle.digest.bind(real.subtle);
  const subtleProxy = new Proxy(real.subtle, {
    get(target, prop) {
      if (prop === "digest") {
        return (algorithm: AlgorithmIdentifier, data: BufferSource) => {
          const view =
            data instanceof ArrayBuffer
              ? new Uint8Array(data)
              : new Uint8Array(
                  (data as ArrayBufferView).buffer,
                  (data as ArrayBufferView).byteOffset,
                  (data as ArrayBufferView).byteLength
                );
          return realDigest(algorithm, Buffer.from(view));
        };
      }
      const value = Reflect.get(target, prop, target);
      return typeof value === "function" ? value.bind(target) : value;
    }
  });
  const cryptoProxy = new Proxy(real, {
    get(target, prop) {
      if (prop === "subtle") return subtleProxy;
      const value = Reflect.get(target, prop, target);
      return typeof value === "function" ? value.bind(target) : value;
    }
  });
  Object.defineProperty(globalThis, "crypto", { value: cryptoProxy, configurable: true });
}

global.console = {
  ...global.console,
  log: jest.fn(),
  error: jest.fn(),
  warn: jest.fn(),
  info: jest.fn(),
  debug: jest.fn()
};

global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn()
}));

global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn()
}));

global.MutationObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  disconnect: jest.fn(),
  takeRecords: jest.fn(() => [])
}));

// jsdom implements no layout, so Range has no getBoundingClientRect. Code that measures
// text width (e.g. truncation detection) gets a zero-sized rect unless a spec mocks it.
if (typeof Range.prototype.getBoundingClientRect !== "function") {
  Range.prototype.getBoundingClientRect = () => new DOMRect();
}

if (typeof globalThis.structuredClone !== "function") {
  globalThis.structuredClone = (<T>(value: T): T => deserialize(serialize(value)) as T) as typeof structuredClone;
}

// Pin the default Intl locale so date formatting is deterministic across dev machines
// and CI, regardless of the runtime's OS/LANG settings. Production code keeps calling
// Intl.DateTimeFormat(undefined, ...) to honor the real user's browser locale.
const RealDateTimeFormat = Intl.DateTimeFormat;
function PatchedDateTimeFormat(locales?: Intl.LocalesArgument, options?: Intl.DateTimeFormatOptions) {
  const isEmptyList = Array.isArray(locales) && locales.length === 0;
  return new RealDateTimeFormat(locales == null || isEmptyList ? "en-US" : locales, options);
}
// Keeps static members like supportedLocalesOf available after the patch.
Object.setPrototypeOf(PatchedDateTimeFormat, RealDateTimeFormat);
// Keeps `instanceof Intl.DateTimeFormat` and RealDateTimeFormat.prototype usage working.
PatchedDateTimeFormat.prototype = RealDateTimeFormat.prototype;
Intl.DateTimeFormat = PatchedDateTimeFormat as typeof Intl.DateTimeFormat;

Object.defineProperty(window, "matchMedia", {
  writable: true,
  configurable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn()
  }))
});

const realConsoleError = console.error;

console.error = (...args: unknown[]) => {
  if (typeof args[0] === "string" && args[0].includes("Error: Could not parse CSS stylesheet")) {
    return;
  }
  realConsoleError(...args);
};
