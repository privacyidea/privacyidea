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
import { EnrollmentResponse, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  ENROLLMENT_CANCELLED,
  EnrollmentStepResult
} from "@components/token/token-enrollment/token-enrollment.constants";
import { Base64Service } from "@services/base64/base64.service";
import { NotificationService } from "@services/notification/notification.service";
import { TokenService } from "@services/token/token.service";
import { MockBase64Service, MockNotificationService, MockTokenService } from "@testing/mock-services";
import { lastValueFrom, of, throwError } from "rxjs";
import { EnrollPasskeyComponent } from "./enroll-passkey.component";
import { axe } from "@testing/axe";

describe("EnrollPasskeyComponent", () => {
  let component: EnrollPasskeyComponent;
  let fixture: ComponentFixture<EnrollPasskeyComponent>;

  let tokenService: MockTokenService;
  let b64: MockBase64Service;
  let notif: MockNotificationService;

  const origCreds = navigator.credentials;

  function setNavigatorCredentials(obj: Partial<CredentialsContainer> | undefined) {
    Object.defineProperty(navigator, "credentials", {
      configurable: true,
      get: () => obj
    });
  }

  beforeEach(async () => {
    jest.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [EnrollPasskeyComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: Base64Service, useClass: MockBase64Service },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollPasskeyComponent);
    component = fixture.componentInstance;

    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    b64 = TestBed.inject(Base64Service) as unknown as MockBase64Service;
    notif = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    fixture.detectChanges();
  });

  // Runs the registration the strategy hands to the enrollment dialog.
  const register = (
    response: EnrollmentResponse,
    data: TokenEnrollmentData,
    signal: AbortSignal = new AbortController().signal
  ): Promise<EnrollmentStepResult> => {
    const firstStep = component.firstStep(response, data);
    if (firstStep.kind !== "fido2") {
      throw new Error("Passkey hands over a FIDO2 registration");
    }
    return firstStep.register(signal);
  };

  afterAll(() => {
    Object.defineProperty(navigator, "credentials", {
      configurable: true,
      get: () => origCreds
    });
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("rejects and notifies when WebAuthn is unsupported", () => {
    setNavigatorCredentials(undefined);
    expect(() => component.buildEnrollmentArgs({} as TokenEnrollmentData)).toThrow(
      /Passkey\/WebAuthn is not supported/i
    );
    expect(notif.error).toHaveBeenCalledWith("Passkey/WebAuthn is not supported by this browser.");
  });

  it("happy path: init -> create cred -> finalize", async () => {
    const finalResp = { detail: { serial: "S-1" } };
    const createdCred = {
      id: "cred-1",
      rawId: new Uint8Array([9, 9]).buffer,
      authenticatorAttachment: "platform",
      response: {
        attestationObject: new Uint8Array([7]).buffer,
        clientDataJSON: new Uint8Array([8]).buffer,
        getTransports: () => ["nfc", "usb"]
      },
      getClientExtensionResults: () => ({
        credProps: { rk: true },
        prf: { enabled: true, results: { first: new Uint8Array([1]).buffer } }
      })
    };

    setNavigatorCredentials({
      create: jest.fn().mockResolvedValue(createdCred)
    });

    const initResp = {
      detail: {
        transaction_id: "tid-1",
        serial: "S-1",
        passkey_registration: {
          rp: { name: "Example", id: "example.com" },
          user: { id: "AA", name: "alice", displayName: "Alice" },
          challenge: "xyz",
          pubKeyCredParams: [],
          excludeCredentials: [{ id: "CCD", type: "public-key" }],
          authenticatorSelection: {},
          timeout: 10000,
          extensions: {},
          attestation: "none"
        }
      }
    };
    const initData = {
      description: "x",
      passkeyRegOptions: {}
    } as unknown as TokenEnrollmentData;
    const args = component.buildEnrollmentArgs(initData);
    expect(args).not.toBeNull();
    tokenService.enrollToken.mockReturnValueOnce(lastValueFrom(of(initResp)));
    const initResponse = await tokenService.enrollToken(args);
    const res = await register(initResponse, args!.data);

    expect(tokenService.enrollToken).toHaveBeenCalledTimes(2);

    // The finalize request contains the transports and only the PRF flag, the PRF results stay in the client
    const finalizeArgs = tokenService.enrollToken.mock.calls[1][0];
    const finalizePayload = finalizeArgs.mapper.toApiPayload(finalizeArgs.data);
    expect(finalizePayload.transports).toEqual(["nfc", "usb"]);
    expect(finalizePayload.prf).toStrictEqual({ enabled: true });

    expect(b64.base64URLToBytes).toHaveBeenCalled();
    expect(b64.bytesToBase64).toHaveBeenCalled();

    expect(res).toStrictEqual(finalResp);
    expect((res as EnrollmentResponse).detail.serial).toBe("S-1");
  });

  it("reports a failed attempt for an invalid server response (no passkey_registration)", async () => {
    const initResp = { detail: { transaction_id: "t", serial: "S-9" } };
    tokenService.enrollToken.mockReturnValueOnce(of(initResp));
    setNavigatorCredentials({
      create: jest.fn()
    });
    const enrollmentArgs = component.buildEnrollmentArgs({} as TokenEnrollmentData);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentArgs));
    const finalResponse = register(initResponse as EnrollmentResponse, enrollmentArgs!.data);
    await expect(finalResponse).resolves.toBeNull();
    expect(notif.error).toHaveBeenCalledWith("Failed to initiate Passkey registration: Invalid server response.");
  });

  it("readPublicKeyCred rejects when the enrollment response has no passkey_registration", async () => {
    notif.error.mockClear();
    const readPublicKeyCred = (
      component as unknown as {
        readPublicKeyCred: (r: EnrollmentResponse) => Promise<Credential | null>;
      }
    ).readPublicKeyCred.bind(component);

    const result = await readPublicKeyCred({ detail: { serial: "S-9" } } as unknown as EnrollmentResponse);

    expect(result).toBeNull();
    expect(notif.error).toHaveBeenCalledWith("Failed to initiate Passkey registration: Invalid server response.");
  });

  it("finalize error: deletes token and notifies", async () => {
    const initResp = {
      detail: {
        transaction_id: "tid-2",
        serial: "S-2",
        passkey_registration: {
          rp: { name: "Example2", id: "example.com" },
          user: { id: "AA", name: "bob", displayName: "Bob" },
          challenge: "xyz",
          pubKeyCredParams: [],
          excludeCredentials: [],
          authenticatorSelection: {},
          timeout: 10000,
          extensions: {},
          attestation: "none"
        }
      }
    };

    tokenService.enrollToken.mockReturnValueOnce(of(initResp)).mockReturnValueOnce(throwError(() => new Error("fin")));

    const createdCred = {
      id: "cred-2",
      rawId: new Uint8Array([1]).buffer,
      authenticatorAttachment: null,
      response: {
        attestationObject: new Uint8Array([2]).buffer,
        clientDataJSON: new Uint8Array([3]).buffer
      },
      getClientExtensionResults: () => ({})
    };

    setNavigatorCredentials({
      create: jest.fn().mockResolvedValue(createdCred)
    });

    const enrollmentArgs = component.buildEnrollmentArgs({} as TokenEnrollmentData);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentArgs));
    const finalResponse = register(initResponse as EnrollmentResponse, enrollmentArgs!.data);

    await expect(finalResponse).resolves.toBe(ENROLLMENT_CANCELLED);

    expect(notif.error).toHaveBeenCalledWith(
      "Error during final Passkey registration step. Attempting to clean up token."
    );
    expect(tokenService.deleteToken).toHaveBeenCalledWith("S-2");
  });

  it("does not finalize a registration once the step was left", async () => {
    setNavigatorCredentials({ create: jest.fn().mockResolvedValue({}) });
    const initResponse = {
      detail: {
        serial: "S-3",
        transaction_id: "tx",
        passkey_registration: {
          rp: { name: "Example", id: "example.com" },
          user: { id: "AA", name: "alice", displayName: "Alice" },
          challenge: "AAAA",
          pubKeyCredParams: [],
          excludeCredentials: [],
          authenticatorSelection: {},
          timeout: 10000,
          extensions: {},
          attestation: "none"
        }
      }
    } as unknown as EnrollmentResponse;
    const left = new AbortController();

    const pending = register(initResponse, { type: "passkey" } as TokenEnrollmentData, left.signal);
    left.abort();

    expect(await pending).toBeNull();
    expect(tokenService.enrollToken).not.toHaveBeenCalled();
  });

  it("cancels the browser's registration once the step was left, without an error", async () => {
    const create = jest.fn(
      (options?: CredentialCreationOptions) =>
        new Promise<Credential | null>((_, reject) =>
          options?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")))
        )
    );
    setNavigatorCredentials({ create });
    const initResponse = {
      detail: {
        serial: "S-4",
        transaction_id: "tx",
        passkey_registration: {
          rp: { name: "Example", id: "example.com" },
          user: { id: "AA", name: "alice", displayName: "Alice" },
          challenge: "AAAA",
          pubKeyCredParams: [],
          excludeCredentials: [],
          authenticatorSelection: {},
          timeout: 10000,
          extensions: {},
          attestation: "none"
        }
      }
    } as unknown as EnrollmentResponse;
    const left = new AbortController();

    const pending = register(initResponse, { type: "passkey" } as TokenEnrollmentData, left.signal);
    left.abort();

    expect(await pending).toBeNull();
    expect(create).toHaveBeenCalledWith(expect.objectContaining({ signal: left.signal }));
    expect(notif.error).not.toHaveBeenCalled();
    expect(tokenService.deleteToken).not.toHaveBeenCalled();
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
