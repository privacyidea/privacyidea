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
import {
  BaseApiPayloadMapper,
  EnrollmentResponse,
  TokenEnrollmentData
} from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { EnrollTokenArguments } from "@services/token/token.service";
import {
  actualValuesFromEnrollmentUrl,
  getEnrollmentDeviations,
  tokenTypeDisplayDescription,
  tokenTypeDisplayLabel,
  tokenTypeLabel,
  tokenTypes
} from "./token.utils";

describe("tokenTypeLabel", () => {
  it("returns the display name of a token type key", () => {
    expect(tokenTypeLabel("hotp")).toBe("HOTP");
    expect(tokenTypeLabel("4eyes")).toBe("4Eyes");
    expect(tokenTypeLabel("applspec")).toBe("Application Specific Password");
  });

  it("looks the key up case-insensitively", () => {
    expect(tokenTypeLabel("TOTP")).toBe("TOTP");
    expect(tokenTypeLabel("WebAuthn")).toBe("WebAuthn");
  });

  it("returns undefined for anything that is no token type", () => {
    expect(tokenTypeLabel("poll")).toBeUndefined();
    expect(tokenTypeLabel("")).toBeUndefined();
  });

  it("returns undefined for the members of Object.prototype", () => {
    expect(tokenTypeLabel("constructor")).toBeUndefined();
    expect(tokenTypeLabel("__proto__")).toBeUndefined();
    expect(tokenTypeLabel("toString")).toBeUndefined();
  });

  it("returns display names for token types that are no longer offered for enrollment", () => {
    expect(tokenTypeLabel("pw")).toBe("Static Password");
    expect(tokenTypeLabel("ocra")).toBe("OCRA");
    expect(tokenTypeLabel("daplug")).toBe("Daplug");
    expect(tokenTypeLabel("deprecated")).toBe("Deprecated");
    expect(tokenTypes.map((tokenType) => tokenType.key)).not.toContain("pw");
  });

  it("covers every token type", () => {
    expect(tokenTypes.filter((tokenType) => !tokenTypeLabel(tokenType.key))).toEqual([]);
  });
});

describe("getEnrollmentDeviations", () => {
  const enrollParameters = (data: Record<string, unknown>): EnrollTokenArguments => ({
    data: data as TokenEnrollmentData,
    mapper: {} as BaseApiPayloadMapper
  });
  const responseWithUrl = (type: "hotp" | "totp" | "daypassword", url: string | null): EnrollmentResponse => ({
    type,
    detail: {
      type,
      serial: "OATH0001",
      ...(url !== null && { googleurl: { description: "URL", img: "", value: url } })
    },
    result: { status: true }
  });

  it("reports the OTP length of the enrollment URL that differs from the requested one", () => {
    const response = responseWithUrl(
      "hotp",
      "otpauth://hotp/OATH0001?secret=ABC&counter=1&digits=8&issuer=privacyIDEA"
    );

    expect(
      getEnrollmentDeviations(
        enrollParameters({ type: "hotp", otpLength: 6, hashAlgorithm: "sha1" }),
        actualValuesFromEnrollmentUrl(response)
      )
    ).toEqual([{ field: "otpLength", requested: 6, actual: 8 }]);
  });

  it("reports nothing when the enrollment URL matches the requested values", () => {
    const sha1Response = responseWithUrl(
      "totp",
      "otpauth://totp/TOTP0001?secret=ABC&period=30&digits=6&issuer=privacyIDEA"
    );
    const sha256Response = responseWithUrl(
      "totp",
      "otpauth://totp/TOTP0001?secret=ABC&algorithm=SHA256&period=60&digits=8&issuer=privacyIDEA"
    );

    expect(actualValuesFromEnrollmentUrl(sha256Response)).toEqual({
      otpLength: 8,
      hashAlgorithm: "sha256",
      timeStep: 60
    });
    expect(
      getEnrollmentDeviations(
        enrollParameters({ type: "totp", otpLength: 6, hashAlgorithm: "sha1", timeStep: 30 }),
        actualValuesFromEnrollmentUrl(sha1Response)
      )
    ).toEqual([]);
    expect(
      getEnrollmentDeviations(
        enrollParameters({ type: "totp", otpLength: 8, hashAlgorithm: "sha256", timeStep: 60 }),
        actualValuesFromEnrollmentUrl(sha256Response)
      )
    ).toEqual([]);
  });

  it("compares the day password time step in seconds", () => {
    const response = responseWithUrl(
      "daypassword",
      "otpauth://daypassword/DAYP0001?secret=ABC&algorithm=SHA256&period=7200&digits=6&issuer=privacyIDEA"
    );
    const params = { type: "daypassword", otpLength: 6, hashAlgorithm: "sha256" };

    expect(
      getEnrollmentDeviations(enrollParameters({ ...params, timeStep: "2h" }), actualValuesFromEnrollmentUrl(response))
    ).toEqual([]);
    expect(
      getEnrollmentDeviations(enrollParameters({ ...params, timeStep: "1h" }), actualValuesFromEnrollmentUrl(response))
    ).toEqual([{ field: "timeStep", requested: "1h", actual: 7200 }]);
  });

  it("reads no values from a response without an enrollment URL", () => {
    expect(actualValuesFromEnrollmentUrl(responseWithUrl("hotp", null))).toBeNull();
    expect(actualValuesFromEnrollmentUrl(null)).toBeNull();
    expect(getEnrollmentDeviations(enrollParameters({ type: "hotp", otpLength: 6 }), null)).toEqual([]);
  });

  it("reports nothing for other token types", () => {
    expect(getEnrollmentDeviations(enrollParameters({ type: "spass", otpLength: 6 }), { otpLength: 8 })).toEqual([]);
  });
});

describe("tokenTypeDisplayLabel", () => {
  it.each([
    { name: "the part before the colon", info: "HOTP: counter based", expected: "HOTP" },
    { name: "the fallback when the info has no colon", info: "counter based", expected: "fallback" },
    { name: "the fallback for an empty info", info: "", expected: "fallback" },
    { name: "an empty label for a leading colon", info: ": desc", expected: "" },
    { name: "the part before the first colon only", info: "Name: see http://x: more", expected: "Name" }
  ])("returns $name", ({ info, expected }) => {
    expect(tokenTypeDisplayLabel(info, "fallback")).toBe(expected);
  });
});

describe("tokenTypeDisplayDescription", () => {
  it.each([
    { name: "the trimmed part after the colon", info: "Name:   some description ", expected: "some description" },
    { name: "the whole text when the info has no colon", info: "only a description", expected: "only a description" },
    { name: "an empty string for an empty info", info: "", expected: "" },
    { name: "the description for a leading colon", info: ": desc", expected: "desc" },
    { name: "the description with a colon inside it", info: "Name: see http://x: more", expected: "see http://x: more" }
  ])("returns $name", ({ info, expected }) => {
    expect(tokenTypeDisplayDescription(info)).toBe(expected);
  });
});
