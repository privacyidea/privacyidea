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

  it("decodes a URL‑safe Base64 string into the correct byte array", () => {
    const base64Url = "SGVsbG8td29ybGQ";
    const expected = new Uint8Array([72, 101, 108, 108, 111, 45, 119, 111, 114, 108, 100]);
    expect(service.base64URLToBytes(base64Url)).toEqual(expected);
  });

  it("adds the correct padding when the input length is not a multiple of 4", () => {
    const bytes = service.base64URLToBytes("TQ");
    expect(Array.from(bytes)).toEqual([77]);
  });

  it("encodes a byte array to standard Base64 with padding", () => {
    const bytes = new Uint8Array([72, 101, 108, 108, 111]);
    const out = service.bytesToBase64(bytes);
    expect(out).toBe("SGVsbG8=");
  });

  it("encodes a byte array to URL‑safe Base64 without padding", () => {
    const bytes = new Uint8Array([72, 101, 108, 108, 111, 32, 49]);
    const out = service.bufferToBase64Url(bytes);
    expect(out).toBe("SGVsbG8gMQ");
  });

  it("round‑trips bytes → Base64URL → bytes losslessly", () => {
    const original = new Uint8Array([1, 2, 3, 4, 5, 250, 255]);
    const b64Url = service.bufferToBase64Url(original);
    const decoded = service.base64URLToBytes(b64Url);
    expect(decoded).toEqual(original);
  });

  it("round‑trips bytes → Base64 → bytes losslessly", () => {
    const original = new Uint8Array([9, 8, 7, 6, 5, 4, 3, 2, 1]);
    const b64 = service.bytesToBase64(original);
    const decoded = service.base64URLToBytes(
      b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "")
    );
    expect(decoded).toEqual(original);
  });
});
