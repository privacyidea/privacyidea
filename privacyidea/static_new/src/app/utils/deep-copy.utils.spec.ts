/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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

import { deepCopy } from './deep-copy.utils';

describe('deepCopy', () => {
  it('should deep copy a simple object', () => {
    const original = { a: 1, b: 'hello' };
    const copy = deepCopy(original);

    expect(copy).toEqual(original);
    expect(copy).not.toBe(original); // Ensure it's a new object
  });

  it('should deep copy an object with nested objects', () => {
    const original = { a: 1, b: { c: 2, d: 'world' } };
    const copy = deepCopy(original);

    expect(copy).toEqual(original);
    expect(copy).not.toBe(original);
    expect(copy.b).not.toBe(original.b); // Ensure nested object is also new
  });

  it('should deep copy an array of primitive values', () => {
    const original = [1, 2, 3];
    const copy = deepCopy(original);

    expect(copy).toEqual(original);
    expect(copy).not.toBe(original);
  });

  it('should deep copy an array of objects', () => {
    const original = [{ a: 1 }, { b: 2 }];
    const copy = deepCopy(original);

    expect(copy).toEqual(original);
    expect(copy).not.toBe(original);
    expect(copy[0]).not.toBe(original[0]); // Ensure nested objects in array are new
  });

  it('should handle null and undefined values', () => {
    const original = { a: null, b: undefined, c: 1 };
    const copy = deepCopy(original);

    // JSON.stringify removes undefined properties
    expect(copy).toEqual({ a: null, c: 1 });
    expect(copy).not.toBe(original);
  });

  it('should handle circular references (will throw an error with JSON.stringify)', () => {
    const original: any = {};
    original.a = original;

    expect(() => deepCopy(original)).toThrow(TypeError);
  });

  it('should handle Date objects (will convert to string with JSON.stringify)', () => {
    const date = new Date();
    const original = { a: date };
    const copy = deepCopy(original);

    expect(copy.a).not.toBeInstanceOf(Date);
    expect(copy.a).toEqual(date.toISOString());
  });

  it('should handle functions (will be removed with JSON.stringify)', () => {
    const original = { a: 1, b: () => console.log('test') };
    const copy = deepCopy(original);

    expect(copy).toEqual({ a: 1 });
    expect(copy.b).toBeUndefined();
  });
});
