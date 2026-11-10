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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { AuthResponse, AuthService } from "@services/auth/auth.service";
import { TokenDetails, TokenInfo, Tokens, TokenService } from "@services/token/token.service";
import { ValidateService } from "@services/validate/validate.service";
import { MockTokenService, MockValidateService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { of } from "rxjs";
import { TestPasskeyActionComponent } from "./test-passkey-action.component";

describe("TestPasskeyActionComponent", () => {
  let fixture: ComponentFixture<TestPasskeyActionComponent>;
  let component: TestPasskeyActionComponent;
  let tokenSvc: MockTokenService;
  let validateSvc: MockValidateService;

  beforeEach(async () => {
    jest.clearAllMocks();
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [TestPasskeyActionComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ValidateService, useClass: MockValidateService }
      ]
    }).compileComponents();

    tokenSvc = TestBed.inject(TokenService) as unknown as MockTokenService;
    validateSvc = TestBed.inject(ValidateService) as unknown as MockValidateService;

    fixture = TestBed.createComponent(TestPasskeyActionComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("token", { serial: "Mock serial" } as TokenDetails);
    fixture.detectChanges();
  });

  function setCredentialIdHash(hash: string): void {
    fixture.componentRef.setInput("token", {
      serial: "Mock serial",
      info: { credential_id_hash: hash } as TokenInfo
    } as TokenDetails);
  }

  it("runs the test from its button and shows the result", async () => {
    jest
      .spyOn(validateSvc, "authenticatePasskey")
      .mockReturnValue(
        of({ result: { value: true, status: true }, detail: { username: "alice" } } as unknown as AuthResponse)
      );

    fixture.nativeElement.querySelector("button").click();
    await flushAsync();
    fixture.detectChanges();

    expect(validateSvc.authenticatePasskey).toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector(".passkey-test-result--success")?.textContent).toContain("alice");
  });

  it("reports success when the credential_id hash matches the current token", async () => {
    const credentialId = "AAA";
    setCredentialIdHash(await sha256HexFromBase64Url(credentialId));

    jest.spyOn(validateSvc, "authenticatePasskey").mockImplementation((args) => {
      args?.onCredentialId?.(credentialId);
      return of({
        result: { value: true, status: true },
        detail: { username: "alice", serial: "Mock serial" }
      } as unknown as AuthResponse);
    });

    component.testPasskey();
    await flushAsync();

    const result = component.result();
    expect(result?.kind).toBe("success");
    expect(result?.message).toMatch(/alice/);
  });

  it("reports a mismatch with matched serial/user/realm when the hash differs", async () => {
    setCredentialIdHash("deadbeef-not-a-real-hash");

    jest.spyOn(validateSvc, "authenticatePasskey").mockImplementation((args) => {
      args?.onCredentialId?.("AAA");
      return of({
        result: { value: true, status: true },
        detail: { username: "bob", serial: "OTHER-SERIAL" }
      } as unknown as AuthResponse);
    });
    (tokenSvc.getTokenDetails as jest.Mock).mockReturnValueOnce(
      of({ result: { value: { tokens: [{ user_realm: "themis" }] } } } as unknown as PiResponse<Tokens>)
    );

    component.testPasskey();
    await flushAsync();

    const result = component.result();
    expect(result?.kind).toBe("warning");
    expect(result?.message).toMatch(/different passkey/);
    expect(result?.mismatch?.serial).toBe("OTHER-SERIAL");
    expect(result?.mismatch?.username).toBe("bob");
    expect(result?.mismatch?.realm).toBe("themis");
  });

  it("skips mismatch detection for self-service users (non-admin)", async () => {
    const authSvc = TestBed.inject(AuthService) as unknown as MockAuthService;
    authSvc.role.set("user");
    setCredentialIdHash("deadbeef-not-a-real-hash");

    jest.spyOn(validateSvc, "authenticatePasskey").mockImplementation((args) => {
      args?.onCredentialId?.("AAA");
      return of({
        result: { value: true, status: true },
        detail: { username: "carol", serial: "OTHER-SERIAL" }
      } as unknown as AuthResponse);
    });

    component.testPasskey();
    await flushAsync();

    const result = component.result();
    expect(result?.kind).toBe("success");
    expect(result?.mismatch).toBeUndefined();
    expect(tokenSvc.getTokenDetails).not.toHaveBeenCalled();
  });

  it("reports 'No user found' when the validate response is falsy", async () => {
    jest
      .spyOn(validateSvc, "authenticatePasskey")
      .mockReturnValue(of({ result: { value: false, status: true }, detail: {} } as unknown as AuthResponse));

    component.testPasskey();
    await flushAsync();

    const result = component.result();
    expect(result?.kind).toBe("warning");
    expect(result?.message).toMatch(/No user found/);
  });
});

// Drains microtasks and a macrotask: crypto.subtle.digest may settle on the next tick.
async function flushAsync(): Promise<void> {
  await new Promise<void>((resolve) => setTimeout(resolve, 0));
  for (let i = 0; i < 5; i++) {
    await Promise.resolve();
  }
  await new Promise<void>((resolve) => setTimeout(resolve, 0));
}

// Mirror of the component's private SHA-256 helper, used only by the matching-hash test.
async function sha256HexFromBase64Url(b64url: string): Promise<string> {
  const pad = b64url
    .padEnd((b64url.length | 3) + 1, "=")
    .replace(/-/g, "+")
    .replace(/_/g, "/");
  const binary = atob(pad);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
