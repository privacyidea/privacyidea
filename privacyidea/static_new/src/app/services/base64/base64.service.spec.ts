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
import { TestBed } from "@angular/core/testing";
import { Base64Service } from "./base64.service";

beforeAll(() => {
  const g: any = globalThis as any;

  if (typeof g.atob === "undefined") {
    g.atob = (data: string) => Buffer.from(data, "base64").toString("binary");
  }
  if (typeof g.btoa === "undefined") {
    g.btoa = (data: string) => Buffer.from(data, "binary").toString("base64");
  }
});

describe("Base64Service", () => {
  let service: Base64Service;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [Base64Service]
    });
    service = TestBed.inject(Base64Service);
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("decodes a URL-safe Base64 string into the correct byte array", () => {
    const base64Url = "SGVsbG8td29ybGQ";
    const expected = new Uint8Array([72, 101, 108, 108, 111, 45, 119, 111, 114, 108, 100]);
    expect(service.base64URLToBytes(base64Url)).toEqual(expected);
  });

  it("handles URL-safe alphabet ('-' and '_') correctly", () => {
    const decoded = service.base64URLToBytes("-_8");
    expect(Array.from(decoded)).toEqual([251, 255]);
  });

  it("adds the correct padding when the input length is not a multiple of 4", () => {
    const bytes = service.base64URLToBytes("TQ");
    expect(Array.from(bytes)).toEqual([77]);
  });

  it("returns empty Uint8Array for empty input", () => {
    expect(service.base64URLToBytes("")).toEqual(new Uint8Array(0));
  });

  it("encodes a byte array to standard Base64 with padding", () => {
    const bytes = new Uint8Array([72, 101, 108, 108, 111]);
    const out = service.bytesToBase64(bytes);
    expect(out).toBe("SGVsbG8=");
  });

  it("bytesToBase64 handles empty array", () => {
    expect(service.bytesToBase64(new Uint8Array([]))).toBe("");
  });

  it("encodes a byte array to URL-safe Base64 without padding and with replacements", () => {
    const bytes = new Uint8Array([251, 255]);
    const out = service.bufferToBase64Url(bytes);
    expect(out).toBe("-_8");
  });

  it("round-trips bytes → Base64URL → bytes losslessly", () => {
    const original = new Uint8Array([1, 2, 3, 4, 5, 250, 255]);
    const b64Url = service.bufferToBase64Url(original);
    const decoded = service.base64URLToBytes(b64Url);
    expect(decoded).toEqual(original);
  });

  it("round-trips bytes → Base64 → bytes losslessly", () => {
    const original = new Uint8Array([9, 8, 7, 6, 5, 4, 3, 2, 1]);
    const b64 = service.bytesToBase64(original);
    const decoded = service.base64URLToBytes(
      b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "")
    );
    expect(decoded).toEqual(original);
  });

  it("webAuthnBase64EncArr + webAuthnBase64DecToArr round-trip (with CRLF line breaks)", () => {
    const bytes = new Uint8Array(60).map((_, i) => (i * 7 + 3) & 0xff);

    const enc = service.webAuthnBase64EncArr(bytes.buffer);
    expect(enc).toContain("\r\n");

    const dec = service.webAuthnBase64DecToArr(enc);
    expect(dec).toEqual(bytes);
  });

  it("webAuthnBase64DecToArr tolerates whitespace and newlines", () => {
    const original = new Uint8Array([0, 1, 2, 250, 251, 252, 253, 254, 255]);
    const enc = service.webAuthnBase64EncArr(original.buffer);
    const noisy = ` \n${enc.slice(0, 10)} \r\n ${enc.slice(10)} \t `;
    const dec = service.webAuthnBase64DecToArr(noisy);
    expect(dec).toEqual(original);
  });

  it("utf8ArrToStr / strToUtf8Arr round-trip for ASCII", () => {
    const s = "Hello-World";
    const bytes = service.strToUtf8Arr(s);
    expect(Array.isArray(Array.from(bytes))).toBe(true);
    const back = service.utf8ArrToStr(bytes);
    expect(back).toBe(s);
  });

  it("utf8ArrToStr / strToUtf8Arr round-trip for multibyte (umlaut, euro)", () => {
    const s = "Grüße €";
    const bytes = service.strToUtf8Arr(s);
    const back = service.utf8ArrToStr(bytes);
    expect(back).toBe(s);
  });

  it("base64EncArr small input matches window.btoa output", () => {
    const bytes = new Uint8Array([65, 66, 67, 68, 69]);
    const bin = String.fromCharCode(...bytes);
    const expected = window.btoa(bin);
    const actual = (service as any).base64EncArr(bytes.buffer) as string;
    expect(actual).toBe(expected);
  });

  it("base64EncArr inserts CRLF every 76 chars", () => {
    const bytes = new Uint8Array(60).map((_, i) => i);
    const out = (service as any).base64EncArr(bytes.buffer) as string;
    expect(out).toContain("\r\n");
  });

  it("base64DecToArr respects nBlockSize (pads output length)", () => {
    const out = (service as any).base64DecToArr("TQ==", 4) as Uint8Array;
    expect(out.length).toBe(4);
    expect(Array.from(out)).toEqual([77, 0, 0, 0]);
  });

  it("b64ToUint6 maps Base64 chars to digits; uint6ToB64 inverses mapping", () => {
    const b64ToUint6 = (service as any).b64ToUint6.bind(service) as (n: number) => number;
    const uint6ToB64 = (service as any).uint6ToB64.bind(service) as (n: number) => number;

    expect(b64ToUint6("A".charCodeAt(0))).toBe(0);
    expect(b64ToUint6("Z".charCodeAt(0))).toBe(25);
    expect(b64ToUint6("a".charCodeAt(0))).toBe(26);
    expect(b64ToUint6("z".charCodeAt(0))).toBe(51);
    expect(b64ToUint6("0".charCodeAt(0))).toBe(52);
    expect(b64ToUint6("9".charCodeAt(0))).toBe(61);
    expect(b64ToUint6("+".charCodeAt(0))).toBe(62);
    expect(b64ToUint6("/".charCodeAt(0))).toBe(63);

    expect(uint6ToB64(0)).toBe("A".charCodeAt(0));
    expect(uint6ToB64(25)).toBe("Z".charCodeAt(0));
    expect(uint6ToB64(26)).toBe("a".charCodeAt(0));
    expect(uint6ToB64(51)).toBe("z".charCodeAt(0));
    expect(uint6ToB64(52)).toBe("0".charCodeAt(0));
    expect(uint6ToB64(61)).toBe("9".charCodeAt(0));
    expect(uint6ToB64(62)).toBe("+".charCodeAt(0));
    expect(uint6ToB64(63)).toBe("/".charCodeAt(0));
  });
});