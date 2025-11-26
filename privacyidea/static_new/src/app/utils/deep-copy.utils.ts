/**
 * Performs a deep copy of an object using JSON.stringify and JSON.parse.
 *
 * Note: This method has limitations. It will not correctly copy:
 * - Functions
 * - undefined
 * - Symbols
 * - Date objects (will be converted to ISO 8601 strings)
 * - RegExp objects (will be converted to empty objects)
 * - Map or Set objects
 * - NaN or Infinity (will be converted to null)
 * It also does not handle circular references and will throw an error.
 *
 * @param obj The object to deep copy.
 * @returns A deep copy of the object.
 * @template T The type of the object.
 */
export function deepCopy<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}
