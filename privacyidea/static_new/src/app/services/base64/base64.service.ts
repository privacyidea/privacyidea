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
import { Injectable } from "@angular/core";

export interface Base64ServiceInterface {
  base64URLToBytes(base64URL: string): Uint8Array;

  bytesToBase64(buffer: Uint8Array): string;

  bufferToBase64Url(buffer: Uint8Array): string;

  webAuthnBase64DecToArr(sBase64: string): Uint8Array;

  webAuthnBase64EncArr(bytes: ArrayBufferLike): string;

  utf8ArrToStr(aBytes: Uint8Array): string;

  strToUtf8Arr(sDOMStr: string): Uint8Array;
}

@Injectable({
  providedIn: "root"
})
export class Base64Service implements Base64ServiceInterface {
  base64URLToBytes(base64URL: string): Uint8Array {
    const padding = "=".repeat((4 - (base64URL.length % 4)) % 4);
    const base64 = (base64URL + padding).replace(/-/g, "+").replace(/_/g, "/");
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  bytesToBase64(buffer: Uint8Array): string {
    let binary = "";
    const len = buffer.byteLength;
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(buffer[i]);
    }
    return window.btoa(binary);
  }

  bufferToBase64Url(buffer: Uint8Array): string {
    const base64 = this.bytesToBase64(buffer);
    return base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  /**
   * Perform web-safe base64 decoding.
   * This will perform web-safe base64 decoding as specified by WebAuthn.
   *
   * @param {string} sBase64 - Base64 to decode.
   * @returns {Uint8Array} - The decoded binary.
   */
  public webAuthnBase64DecToArr(sBase64: string): Uint8Array {
    return this.base64DecToArr(
      sBase64
        .replace(/-/g, "+")
        .replace(/_/g, "/")
        .padEnd((sBase64.length | 3) + 1, "=")
    );
  }

  /**
   * Perform web-safe base64 encoding.
   * This will perform web-safe base64 encoding as specified by WebAuthn.
   *
   * @param {ArrayBufferLike} bytes - Bytes to encode.
   * @returns {string} - The encoded base64.
   */
  public webAuthnBase64EncArr(bytes: ArrayBufferLike): string {
    return this.base64EncArr(bytes).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
  }

  /**
   * Decode a UTF-8-string.
   * This will accept a UTF-8 string and decode it into the native string
   * representation of the JavaScript engine (read: UTF-16). This function
   * currently implements no sanity checks whatsoever. If the input is not
   * valid UTF-8, the result of this function is not well-defined!
   *
   * @param {Uint8Array} aBytes - A UTF-8 encoded string.
   * @returns {string} The decoded string.
   */
  public utf8ArrToStr(aBytes: Uint8Array): string {
    let sView = "";

    let nPart;
    const nLen = aBytes.length;
    for (let nIdx = 0; nIdx < nLen; nIdx++) {
      nPart = aBytes[nIdx];
      sView += String.fromCharCode(
        nPart > 251 && nPart < 254 && nIdx + 5 < nLen
          ? /* six bytes */
          (nPart - 252) * 1073741824 /* << 30 */ +
          ((aBytes[++nIdx] - 128) << 24) +
          ((aBytes[++nIdx] - 128) << 18) +
          ((aBytes[++nIdx] - 128) << 12) +
          ((aBytes[++nIdx] - 128) << 6) +
          aBytes[++nIdx] -
          128
          : nPart > 247 && nPart < 252 && nIdx + 4 < nLen
            ? /* five bytes */
            ((nPart - 248) << 24) +
            ((aBytes[++nIdx] - 128) << 18) +
            ((aBytes[++nIdx] - 128) << 12) +
            ((aBytes[++nIdx] - 128) << 6) +
            aBytes[++nIdx] -
            128
            : nPart > 239 && nPart < 248 && nIdx + 3 < nLen
              ? /* four bytes */
              ((nPart - 240) << 18) +
              ((aBytes[++nIdx] - 128) << 12) +
              ((aBytes[++nIdx] - 128) << 6) +
              aBytes[++nIdx] -
              128
              : nPart > 223 && nPart < 240 && nIdx + 2 < nLen
                ? /* three bytes */
                ((nPart - 224) << 12) + ((aBytes[++nIdx] - 128) << 6) + aBytes[++nIdx] - 128
                : nPart > 191 && nPart < 224 && nIdx + 1 < nLen
                  ? /* two bytes */
                  ((nPart - 192) << 6) + aBytes[++nIdx] - 128
                  : /* one byte */
                  nPart
      );
    }

    return sView;
  }

  /**
   * Encode a string to UTF-8.
   * This will accept a string in the native representation of the JavaScript
   * engine (read: UTF-16), and encode it as UTF-8.
   *
   * @param {string} sDOMStr - A string to encode.
   * @returns {Uint8Array} - The encoded string.
   */
  public strToUtf8Arr(sDOMStr: string): Uint8Array {
    let aBytes: Uint8Array;
    let nChr: number;
    const nStrLen = sDOMStr.length;
    let nArrLen = 0;

    /*
     * Determine the byte-length of the string when encoded as UTF-8.
     */

    for (let nMapIdx = 0; nMapIdx < nStrLen; nMapIdx++) {
      nChr = sDOMStr.charCodeAt(nMapIdx);
      nArrLen +=
        nChr < 0x80 ? 1 : nChr < 0x800 ? 2 : nChr < 0x10000 ? 3 : nChr < 0x200000 ? 4 : nChr < 0x4000000 ? 5 : 6;
    }

    aBytes = new Uint8Array(nArrLen);

    let nIdx = 0;
    for (let nChrIdx = 0; nChrIdx < nStrLen; nChrIdx++) {
      nChr = sDOMStr.charCodeAt(nChrIdx);
      if (nChr < 128) {
        /* one byte */
        aBytes[nIdx++] = nChr;
      } else if (nChr < 0x800) {
        /* two bytes */
        aBytes[nIdx++] = 192 + (nChr >>> 6);
        aBytes[nIdx++] = 128 + (nChr & 63);
      } else if (nChr < 0x10000) {
        /* three bytes */
        aBytes[nIdx++] = 224 + (nChr >>> 12);
        aBytes[nIdx++] = 128 + ((nChr >>> 6) & 63);
        aBytes[nIdx++] = 128 + (nChr & 63);
      } else if (nChr < 0x200000) {
        /* four bytes */
        aBytes[nIdx++] = 240 + (nChr >>> 18);
        aBytes[nIdx++] = 128 + ((nChr >>> 12) & 63);
        aBytes[nIdx++] = 128 + ((nChr >>> 6) & 63);
        aBytes[nIdx++] = 128 + (nChr & 63);
      } else if (nChr < 0x4000000) {
        /* five bytes */
        aBytes[nIdx++] = 248 + (nChr >>> 24);
        aBytes[nIdx++] = 128 + ((nChr >>> 18) & 63);
        aBytes[nIdx++] = 128 + ((nChr >>> 12) & 63);
        aBytes[nIdx++] = 128 + ((nChr >>> 6) & 63);
        aBytes[nIdx++] = 128 + (nChr & 63);
      } else {
        /* six bytes */
        aBytes[nIdx++] = 252 + (nChr >>> 30);
        aBytes[nIdx++] = 128 + ((nChr >>> 24) & 63);
        aBytes[nIdx++] = 128 + ((nChr >>> 18) & 63);
        aBytes[nIdx++] = 128 + ((nChr >>> 12) & 63);
        aBytes[nIdx++] = 128 + ((nChr >>> 6) & 63);
        aBytes[nIdx++] = 128 + (nChr & 63);
      }
    }

    return aBytes;
  }

  /**
   * Convert a UTF-8 encoded base64 character to a base64 digit.
   * Adapted from Base64 / binary data / UTF-8 strings utilities (#2)
   * Source: https://developer.mozilla.org/en-US/docs/Web/API/WindowBase64/Base64_encoding_and_decoding
   * Author: madmurphy
   *
   * @param {number} nChr - A UTF-8 encoded base64 character.
   * @returns {number} - The base64 digit.
   */
  private b64ToUint6(nChr: number): number {
    return nChr > 64 && nChr < 91
      ? nChr - 65
      : nChr > 96 && nChr < 123
        ? nChr - 71
        : nChr > 47 && nChr < 58
          ? nChr + 4
          : nChr === 43
            ? 62
            : nChr === 47
              ? 63
              : 0;
  }

  /**
   * Convert a base64 digit, to a UTF-8 encoded base64 character.
   * Adapted from Base64 / binary data / UTF-8 strings utilities (#2)
   * Source: https://developer.mozilla.org/en-US/docs/Web/API/WindowBase64/Base64_encoding_and_decoding
   * Author: madmurphy
   *
   * @param {number} nUint6 - A base64 digit.
   * @returns {number} - The UTF-8 encoded base64 character.
   */
  private uint6ToB64(nUint6: number): number {
    return nUint6 < 26
      ? nUint6 + 65
      : nUint6 < 52
        ? nUint6 + 71
        : nUint6 < 62
          ? nUint6 - 4
          : nUint6 === 62
            ? 43
            : nUint6 === 63
              ? 47
              : 65;
  }

  /**
   * Decode base64 into UTF-8.
   *
   * This will take a base64 encoded string and decode it to UTF-8,
   * optionally NUL-padding it to make its length a multiple of a given
   * block size.
   * Adapted from Base64 / binary data / UTF-8 strings utilities (#2)
   * Source: https://developer.mozilla.org/en-US/docs/Web/API/WindowBase64/Base64_encoding_and_decoding
   * Author: madmurphy
   *
   * @param {string} sBase64 - Base64 to decode.
   * @param {number} [nBlockSize=1] - The block-size for the output.
   *
   * @returns {Uint8Array} - The decoded string.
   */
  private base64DecToArr(sBase64: string, nBlockSize?: number): Uint8Array {
    const sB64Enc = sBase64.replace(/[^A-Za-z0-9+\/]/g, "");
    const nInLen = sB64Enc.length;
    const nOutLen = nBlockSize ? Math.ceil(((nInLen * 3 + 1) >>> 2) / nBlockSize) * nBlockSize : (nInLen * 3 + 1) >>> 2;
    const aBytes = new Uint8Array(nOutLen);

    let nMod3,
      nMod4,
      nUint24 = 0,
      nOutIdx = 0;
    for (let nInIdx = 0; nInIdx < nInLen; nInIdx++) {
      nMod4 = nInIdx & 3;
      nUint24 |= this.b64ToUint6(sB64Enc.charCodeAt(nInIdx)) << (18 - 6 * nMod4);
      if (nMod4 === 3 || nInLen - nInIdx === 1) {
        for (nMod3 = 0; nMod3 < 3 && nOutIdx < nOutLen; nMod3++, nOutIdx++) {
          aBytes[nOutIdx] = (nUint24 >>> ((16 >>> nMod3) & 24)) & 255;
        }
        nUint24 = 0;
      }
    }

    return aBytes;
  }

  /**
   * Encode a binary into base64.
   * This will take a binary ArrayBufferLike and encode it into base64.
   * Adapted from Base64 / binary data / UTF-8 strings utilities (#2)
   * Source: https://developer.mozilla.org/en-US/docs/Web/API/WindowBase64/Base64_encoding_and_decoding
   * Author: madmurphy
   *
   * @param {ArrayBufferLike} bytes - Bytes to encode.
   *
   * @returns {string} - The encoded base64.
   */
  private base64EncArr(bytes: ArrayBufferLike): string {
    const aBytes = new Uint8Array(bytes);
    const eqLen = (3 - (aBytes.length % 3)) % 3;
    let sB64Enc = "";

    let nMod3,
      nUint24 = 0;
    const nLen = aBytes.length;
    for (let nIdx = 0; nIdx < nLen; nIdx++) {
      nMod3 = nIdx % 3;

      // Split the output in lines 76-characters long
      if (nIdx > 0 && ((nIdx * 4) / 3) % 76 === 0) {
        sB64Enc += "\r\n";
      }

      nUint24 |= aBytes[nIdx] << ((16 >>> nMod3) & 24);
      if (nMod3 === 2 || aBytes.length - nIdx === 1) {
        sB64Enc += String.fromCharCode(
          this.uint6ToB64((nUint24 >>> 18) & 63),
          this.uint6ToB64((nUint24 >>> 12) & 63),
          this.uint6ToB64((nUint24 >>> 6) & 63),
          this.uint6ToB64(nUint24 & 63)
        );
        nUint24 = 0;
      }
    }

    return eqLen === 0 ? sB64Enc : sB64Enc.substring(0, sB64Enc.length - eqLen) + (eqLen === 1 ? "=" : "==");
  }
}
