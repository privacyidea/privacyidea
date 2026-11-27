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
import { provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { EnrollmentResponse, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  WebAuthnApiPayloadMapper,
  WebAuthnFinalizeApiPayloadMapper,
  WebauthnEnrollmentResponse
} from "@app/mappers/token-api-payload/webauthn-token-api-payload.mapper";
import { EnrollWebauthnComponent } from "@components/token/token-enrollment/enroll-webauthn/enroll-webauthn.component";
import { EnrollmentStepResult } from "@components/token/token-enrollment/token-enrollment.constants";
import { Base64Service } from "@services/base64/base64.service";
import { NotificationService } from "@services/notification/notification.service";
import { TokenService } from "@services/token/token.service";
import { firstValueFrom, lastValueFrom, of, throwError } from "rxjs";
import { axe } from "@testing/axe";

const makeEnrollInitResponse = (): WebauthnEnrollmentResponse =>
  ({
    detail: {
      serial: "SER123",
      webAuthnRegisterRequest: {
        transaction_id: "tx-1",
        relyingParty: { id: "example.com", name: "Example" },
        serialNumber: "SER123",
        name: "alice",
        displayName: "Alice",
        nonce: "abc",
        pubKeyCredAlgorithms: [{ type: "public-key", alg: -7 }],
        timeout: 60000,
        excludeCredentials: [{ id: "ex1", type: "public-key", transports: ["internal"] }],
        authenticatorSelection: {},
        attestation: "none",
        extensions: {}
      }
    },
    type: "webauthn"
  }) as unknown as WebauthnEnrollmentResponse;

const makePublicKeyCredential = () => {
  const rawId = new Uint8Array([5, 6]).buffer as ArrayBuffer;
  const attestationObject = new Uint8Array([1, 2, 3]).buffer as ArrayBuffer;
  const clientDataJSON = new Uint8Array([4, 5, 6]).buffer as ArrayBuffer;
  return {
    id: "cred-1",
    rawId,
    type: "public-key",
    authenticatorAttachment: "platform",
    response: { attestationObject, clientDataJSON },
    getClientExtensionResults: () => ({ credProps: { rk: true } }),
    toJSON: jest.fn()
  } as PublicKeyCredential;
};

const BASIC = { user: "alice", realm: "default" } as unknown as TokenEnrollmentData;

describe("EnrollWebauthnComponent", () => {
  let fixture: ComponentFixture<EnrollWebauthnComponent>;
  let component: EnrollWebauthnComponent;

  let tokenService: jest.Mocked<TokenService>;
  let notification: jest.Mocked<NotificationService>;
  let base64: jest.Mocked<Base64Service>;

  const setNavigatorCreate = (impl: () => Promise<PublicKeyCredential>) => {
    (navigator as { credentials: CredentialsContainer }).credentials = {
      create: jest.fn().mockImplementation(impl),
      get: jest.fn(),
      preventSilentAccess: jest.fn(),
      store: jest.fn()
    } as CredentialsContainer;
  };

  beforeEach(async () => {
    tokenService = { enrollToken: jest.fn() } as unknown as jest.Mocked<TokenService>;
    notification = {
      success: jest.fn(),
      error: jest.fn(),
      warning: jest.fn()
    } as unknown as jest.Mocked<NotificationService>;
    base64 = {
      base64URLToBytes: jest.fn().mockReturnValue(new Uint8Array([1])),
      bytesToBase64: jest.fn().mockReturnValue("b64")
    } as unknown as jest.Mocked<Base64Service>;

    await TestBed.configureTestingModule({
      imports: [EnrollWebauthnComponent],
      providers: [
        provideHttpClient(),
        provideZonelessChangeDetection(),
        { provide: TokenService, useValue: tokenService },
        { provide: NotificationService, useValue: notification },
        { provide: Base64Service, useValue: base64 },
        { provide: WebAuthnApiPayloadMapper, useValue: {} },
        { provide: WebAuthnFinalizeApiPayloadMapper, useValue: {} }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollWebauthnComponent);
    component = fixture.componentInstance;
  });

  const detectChangesStable = async () => {
    fixture.detectChanges();
    await Promise.resolve();
    fixture.detectChanges();
  };

  // Runs the registration the strategy hands to the enrollment dialog.
  // Runs the browser registration and then its final request, as the FIDO2 step and the flow do.
  const register = async (
    response: EnrollmentResponse,
    data: TokenEnrollmentData,
    signal: AbortSignal = new AbortController().signal
  ): Promise<EnrollmentStepResult> => {
    const firstStep = component.firstStep(response, data);
    if (firstStep.kind !== "fido2") {
      throw new Error("WebAuthn hands over a FIDO2 registration");
    }
    const finalRequest = await firstStep.register(signal);
    return finalRequest ? firstValueFrom(finalRequest) : null;
  };

  it("should create", async () => {
    await detectChangesStable();
    expect(component).toBeTruthy();
  });

  it("should expose buildEnrollmentArgs as the strategy entry point", async () => {
    await detectChangesStable();
    expect(typeof component.buildEnrollmentArgs).toBe("function");
  });

  it("should notify when WebAuthn API is unavailable", async () => {
    (navigator as { credentials?: CredentialsContainer }).credentials = undefined;
    await detectChangesStable();
    const enrollemntData = component.buildEnrollmentArgs(BASIC);
    expect(enrollemntData).toBeNull();
    expect(notification.error).toHaveBeenCalledWith("WebAuthn is not supported by this browser.");
  });

  it("should notify when init response missing detail", async () => {
    setNavigatorCreate(async () => makePublicKeyCredential());
    tokenService.enrollToken.mockReturnValue(
      of({ detail: undefined, type: "webauthn" } as unknown as EnrollmentResponse)
    );
    await detectChangesStable();
    const enrollmentArgs = component.buildEnrollmentArgs(BASIC);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentArgs!));
    const finalResponse = await register(initResponse as EnrollmentResponse, enrollmentArgs!.data);
    expect(finalResponse).toBeNull();
    expect(notification.error).toHaveBeenCalledWith(
      "Failed to initiate WebAuthn registration: Invalid server response or missing details."
    );
  });

  it("should notify when register request missing", async () => {
    setNavigatorCreate(async () => makePublicKeyCredential());
    tokenService.enrollToken.mockReturnValue(
      of({ detail: { webAuthnRegisterRequest: undefined }, type: "webauthn" } as unknown as EnrollmentResponse)
    );
    await detectChangesStable();
    const enrollmentArgs = component.buildEnrollmentArgs(BASIC);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentArgs!));
    const finalResponse = await register(initResponse as EnrollmentResponse, enrollmentArgs!.data);
    expect(finalResponse).toBeNull();
    expect(notification.error).toHaveBeenCalledWith(
      "Failed to initiate WebAuthn registration: Missing WebAuthn registration request data."
    );
  });

  it("should notify when finalize prerequisites missing", async () => {
    setNavigatorCreate(async () => makePublicKeyCredential());
    tokenService.enrollToken.mockReturnValue(
      of({
        detail: { webAuthnRegisterRequest: { transaction_id: null }, serial: null },
        type: "webauthn"
      } as unknown as EnrollmentResponse)
    );
    await detectChangesStable();
    const enrollmentArgs = component.buildEnrollmentArgs(BASIC);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentArgs!));
    const finalResponse = await register(initResponse as EnrollmentResponse, enrollmentArgs!.data);
    expect(finalResponse).toBeNull();
    expect(notification.warning).toHaveBeenCalledWith(
      "Invalid transaction ID or serial number in enrollment detail for finalization."
    );
  });

  it("readPublicKeyCred warns when the response has no webAuthnRegisterRequest", async () => {
    const readPublicKeyCred = (
      component as unknown as {
        readPublicKeyCred: (r: WebauthnEnrollmentResponse) => Promise<PublicKeyCredential | null>;
      }
    ).readPublicKeyCred;

    const result = await readPublicKeyCred({ detail: {} } as unknown as WebauthnEnrollmentResponse);

    expect(result).toBeNull();
    expect(notification.warning).toHaveBeenCalledWith("Invalid WebAuthn registration request data.");
  });

  it("finalizeEnrollment warns when the response or its detail is missing", async () => {
    const finalizeEnrollment = (
      component as unknown as {
        finalizeEnrollment: (args: {
          webauthnEnrollmentData: unknown;
          webauthnEnrollmentResponse: WebauthnEnrollmentResponse | null;
          publicKeyCred: PublicKeyCredential;
        }) => Promise<EnrollmentResponse | null>;
      }
    ).finalizeEnrollment.bind(component);

    const result = await finalizeEnrollment({
      webauthnEnrollmentData: {},
      webauthnEnrollmentResponse: null,
      publicKeyCred: {} as PublicKeyCredential
    });

    expect(result).toBeNull();
    expect(notification.warning).toHaveBeenCalledWith("Enrollment response or its detail is missing for finalization.");
  });

  it("cancels the browser's registration once the step was left, without an error", async () => {
    const create = jest.fn(
      (options?: CredentialCreationOptions) =>
        new Promise<Credential | null>((_, reject) =>
          options?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")))
        )
    );
    (navigator as { credentials: CredentialsContainer }).credentials = { create } as unknown as CredentialsContainer;
    tokenService.enrollToken.mockReturnValue(of(makeEnrollInitResponse()));
    const enrollmentArgs = component.buildEnrollmentArgs(BASIC);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentArgs!));
    const left = new AbortController();

    const pending = register(initResponse as EnrollmentResponse, enrollmentArgs!.data, left.signal);
    left.abort();

    expect(await pending).toBeNull();
    expect(create).toHaveBeenCalledWith(expect.objectContaining({ signal: left.signal }));
    expect(notification.error).not.toHaveBeenCalled();
  });

  it("reports a failed attempt when credential creation throws", async () => {
    setNavigatorCreate(async () => {
      throw new Error("blocked");
    });
    tokenService.enrollToken.mockReturnValue(of(makeEnrollInitResponse()));

    await detectChangesStable();
    const enrollmentArgs = component.buildEnrollmentArgs(BASIC);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentArgs!));
    const finalResponsePromise = register(initResponse as EnrollmentResponse, enrollmentArgs!.data);
    const finalResponse = await finalResponsePromise;
    expect(finalResponse).toBeNull();
    expect(notification.error).toHaveBeenCalledWith("WebAuthn credential creation failed: blocked");
  });

  it("should complete full happy path and return final response", async () => {
    setNavigatorCreate(async () => makePublicKeyCredential());
    tokenService.enrollToken
      .mockReturnValueOnce(of(makeEnrollInitResponse()))
      .mockReturnValueOnce(of({ detail: { serial: "" }, type: "webauthn" } as unknown as EnrollmentResponse));

    await detectChangesStable();
    const enrollmentArgs = component.buildEnrollmentArgs(BASIC);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentArgs!));
    const finalResponse = await register(initResponse as EnrollmentResponse, enrollmentArgs!.data);

    expect(base64.base64URLToBytes).toHaveBeenCalled();
    expect(base64.bytesToBase64).toHaveBeenCalled();
    expect(finalResponse).toEqual({ detail: { serial: "SER123" }, type: "webauthn" });
  });

  it("sends the final request only when it is subscribed to, so it can outlive the step", async () => {
    setNavigatorCreate(async () => makePublicKeyCredential());
    tokenService.enrollToken.mockReturnValue(of(makeEnrollInitResponse()));

    await detectChangesStable();
    const enrollmentArgs = component.buildEnrollmentArgs(BASIC);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentArgs!));
    const firstStep = component.firstStep(initResponse as EnrollmentResponse, enrollmentArgs!.data);
    const finalRequest = firstStep.kind === "fido2" ? await firstStep.register(new AbortController().signal) : null;

    expect(finalRequest).not.toBeNull();
    expect(tokenService.enrollToken).toHaveBeenCalledTimes(1);
  });

  it("should notify when finalization fails", async () => {
    setNavigatorCreate(async () => makePublicKeyCredential());
    tokenService.enrollToken
      .mockReturnValueOnce(of(makeEnrollInitResponse()))
      .mockReturnValueOnce(throwError(() => new Error("finalize-fail")));

    await detectChangesStable();
    const enrollmentArgs = component.buildEnrollmentArgs(BASIC);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentArgs!));
    const finalResponsePromise = register(initResponse as EnrollmentResponse, enrollmentArgs!.data);
    const finalResponse = await finalResponsePromise;
    expect(finalResponse).toBeNull();
    expect(notification.error).toHaveBeenCalledWith("WebAuthn finalization failed: finalize-fail");
  });

  it("buildEnrollmentArgs returns the webauthn payload and mapper", async () => {
    (navigator as { credentials: CredentialsContainer }).credentials = {
      create: jest.fn().mockResolvedValue(makePublicKeyCredential()),
      get: jest.fn(),
      preventSilentAccess: jest.fn(),
      store: jest.fn()
    } as CredentialsContainer;
    await detectChangesStable();

    const enrollmentArgs = component.buildEnrollmentArgs(BASIC);

    expect(enrollmentArgs).toEqual({
      data: { realm: "default", type: "webauthn", user: "alice" },
      mapper: expect.any(Object)
    });
  });

  it("hands the enrollment dialog a FIDO2 registration step", () => {
    expect(component.firstStep(makeEnrollInitResponse(), BASIC).kind).toBe("fido2");
  });

  it("does not finalize a registration once the step was left", async () => {
    setNavigatorCreate(async () => makePublicKeyCredential());
    tokenService.enrollToken.mockReturnValue(of(makeEnrollInitResponse()));
    const enrollmentArgs = component.buildEnrollmentArgs(BASIC);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentArgs!));
    tokenService.enrollToken.mockClear();
    const left = new AbortController();

    const pending = register(initResponse as EnrollmentResponse, enrollmentArgs!.data, left.signal);
    left.abort();

    expect(await pending).toBeNull();
    expect(tokenService.enrollToken).not.toHaveBeenCalled();
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
