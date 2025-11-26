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

import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideExperimentalZonelessChangeDetection } from "@angular/core";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { lastValueFrom, map, of, throwError } from "rxjs";
import { EnrollWebauthnComponent } from "./enroll-webauthn.component";
import {
  WebAuthnApiPayloadMapper,
  WebAuthnFinalizeApiPayloadMapper
} from "../../../../mappers/token-api-payload/webauthn-token-api-payload.mapper";
import { NotificationService } from "../../../../services/notification/notification.service";
import { TokenService } from "../../../../services/token/token.service";
import { Base64Service } from "../../../../services/base64/base64.service";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { provideHttpClient } from "@angular/common/http";
import { DialogService } from "../../../../services/dialog/dialog.service";

const dialogStub = {
  isTokenEnrollmentFirstStepDialogOpen: false,
  openTokenEnrollmentFirstStepDialog: jest.fn(() => ({
    afterClosed: () => of(undefined),
    close: jest.fn()
  })),
  closeTokenEnrollmentFirstStepDialog: jest.fn()
};

const makeEnrollInitResponse = () => ({
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
});

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
    getClientExtensionResults: () => ({ credProps: { rk: true } })
  } as any;
};

const BASIC = { user: "alice", realm: "default" } as unknown as TokenEnrollmentData;

describe("EnrollWebauthnComponent", () => {
  let fixture: ComponentFixture<EnrollWebauthnComponent>;
  let component: EnrollWebauthnComponent;

  let tokenService: jest.Mocked<TokenService>;
  let notification: jest.Mocked<NotificationService>;
  let base64: jest.Mocked<Base64Service>;

  const setNavigatorCreate = (impl: () => Promise<any>) => {
    (navigator as any).credentials = {
      create: jest.fn().mockImplementation(impl)
    };
  };

  beforeEach(async () => {
    tokenService = { enrollToken: jest.fn() } as any;
    notification = { openSnackBar: jest.fn() } as any;
    base64 = {
      base64URLToBytes: jest.fn().mockReturnValue(new Uint8Array([1])),
      bytesToBase64: jest.fn().mockReturnValue("b64")
    } as any;

    await TestBed.configureTestingModule({
      imports: [EnrollWebauthnComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideExperimentalZonelessChangeDetection(),
        { provide: TokenService, useValue: tokenService },
        { provide: NotificationService, useValue: notification },
        { provide: Base64Service, useValue: base64 },
        { provide: WebAuthnApiPayloadMapper, useValue: {} },
        { provide: WebAuthnFinalizeApiPayloadMapper, useValue: {} },
        { provide: DialogService, useValue: dialogStub }
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

  it("should create", async () => {
    await detectChangesStable();
    expect(component).toBeTruthy();
  });

  it("should emit outputs on init", async () => {
    const additionalEmits: any[] = [];
    let emittedHandler: ((...args: any[]) => any) | undefined;

    component.additionalFormFieldsChange.subscribe((v) => additionalEmits.push(v));
    component.getEnrollmentDataChange.subscribe((fn) => (emittedHandler = fn));

    await detectChangesStable();

    expect(additionalEmits[0]).toEqual({});
    expect(typeof emittedHandler).toBe("function");
  });

  it("should notify when WebAuthn API is unavailable", async () => {
    (navigator as any).credentials = undefined;
    await detectChangesStable();
    const enrollemntData = component.getEnrollmentData(BASIC);
    expect(enrollemntData).toBeNull();
    expect(notification.openSnackBar).toHaveBeenCalledWith("WebAuthn is not supported by this browser.");
  });

  // Is now handled by generic token enrollment component
  //
  // it("should notify when initial enrollment fails", async () => {
  //   setNavigatorCreate(async () => makePublicKeyCredential());
  //   tokenService.enrollToken.mockReturnValue(throwError(() => new Error("boom")) as any);
  //   await detectChangesStable();
  //   const res = await component.getEnrollmentData(BASIC);

  //   expect(res).toBeNull();
  //   expect(notification.openSnackBar).toHaveBeenCalledWith("WebAuthn registration process failed: boom");
  // });

  it("should notify when init response missing detail", async () => {
    setNavigatorCreate(async () => makePublicKeyCredential());
    tokenService.enrollToken.mockReturnValue(of({ detail: undefined, type: "webauthn" } as any) as any);
    await detectChangesStable();
    const enrollmentData = component.getEnrollmentData(BASIC);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentData!));
    const finalResponse = await component.onEnrollmentResponse(
      initResponse as EnrollmentResponse,
      enrollmentData!.data
    );
    expect(finalResponse).toBeNull();
    expect(notification.openSnackBar).toHaveBeenCalledWith(
      "Failed to initiate WebAuthn registration: Invalid server response or missing details."
    );
  });

  it("should notify when register request missing", async () => {
    setNavigatorCreate(async () => makePublicKeyCredential());
    tokenService.enrollToken.mockReturnValue(
      of({ detail: { webAuthnRegisterRequest: undefined }, type: "webauthn" } as any) as any
    );
    await detectChangesStable();
    const enrollmentData = component.getEnrollmentData(BASIC);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentData!));
    const finalResponse = await component.onEnrollmentResponse(
      initResponse as EnrollmentResponse,
      enrollmentData!.data
    );
    expect(finalResponse).toBeNull();
    expect(notification.openSnackBar).toHaveBeenCalledWith(
      "Failed to initiate WebAuthn registration: Missing WebAuthn registration request data."
    );
  });

  it("should notify when finalize prerequisites missing", async () => {
    setNavigatorCreate(async () => makePublicKeyCredential());
    tokenService.enrollToken.mockReturnValue(
      of({
        detail: { webAuthnRegisterRequest: { transaction_id: null }, serial: null },
        type: "webauthn"
      } as any) as any
    );
    await detectChangesStable();
    const enrollmentData = component.getEnrollmentData(BASIC);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentData!));
    const finalResponse = await component.onEnrollmentResponse(
      initResponse as EnrollmentResponse,
      enrollmentData!.data
    );
    expect(finalResponse).toBeNull();
    expect(notification.openSnackBar).toHaveBeenCalledWith(
      "Invalid transaction ID or serial number in enrollment detail for finalization."
    );
  });

  it("should return null when credential creation throws and close dialog", async () => {
    const openDialog = jest.fn();
    const closeDialog = jest.fn();
    (component as any).dialogService = {
      isTokenEnrollmentFirstStepDialogOpen: false,
      openTokenEnrollmentFirstStepDialog: openDialog,
      closeTokenEnrollmentFirstStepDialog: closeDialog
    };

    setNavigatorCreate(async () => {
      throw new Error("blocked");
    });
    tokenService.enrollToken.mockReturnValue(of(makeEnrollInitResponse() as any) as any);

    await detectChangesStable();
    const enrollmentData = component.getEnrollmentData(BASIC);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentData!));
    const finalResponse = await component.onEnrollmentResponse(
      initResponse as EnrollmentResponse,
      enrollmentData!.data
    );
    expect(openDialog).toHaveBeenCalled();
    expect(closeDialog).toHaveBeenCalled();
    expect(finalResponse).toBeNull();
    expect(notification.openSnackBar).toHaveBeenCalledWith("WebAuthn credential creation failed: blocked");
  });

  it("should complete full happy path and return final response", async () => {
    const openDialog = jest.fn();
    const closeDialog = jest.fn();
    (component as any).dialogService = {
      isTokenEnrollmentFirstStepDialogOpen: false,
      openTokenEnrollmentFirstStepDialog: openDialog,
      closeTokenEnrollmentFirstStepDialog: closeDialog
    };

    setNavigatorCreate(async () => makePublicKeyCredential());
    tokenService.enrollToken
      .mockReturnValueOnce(of(makeEnrollInitResponse() as any) as any)
      .mockReturnValueOnce(of({ detail: { serial: "" }, type: "webauthn" } as any) as any);

    await detectChangesStable();
    const enrollmentData = component.getEnrollmentData(BASIC);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentData!));
    const finalResponse = await component.onEnrollmentResponse(
      initResponse as EnrollmentResponse,
      enrollmentData!.data
    );

    expect(openDialog).toHaveBeenCalled();
    expect(closeDialog).toHaveBeenCalled();
    expect(base64.base64URLToBytes).toHaveBeenCalled();
    expect(base64.bytesToBase64).toHaveBeenCalled();
    expect(finalResponse).toEqual({ detail: { serial: "SER123" }, type: "webauthn" });
  });

  it("should notify when finalization fails", async () => {
    const openDialog = jest.fn();
    const closeDialog = jest.fn();
    (component as any).dialogService = {
      isTokenEnrollmentFirstStepDialogOpen: false,
      openTokenEnrollmentFirstStepDialog: openDialog,
      closeTokenEnrollmentFirstStepDialog: closeDialog
    };

    setNavigatorCreate(async () => makePublicKeyCredential());
    tokenService.enrollToken
      .mockReturnValueOnce(of(makeEnrollInitResponse() as any) as any)
      .mockReturnValueOnce(throwError(() => new Error("finalize-fail")) as any);

    await detectChangesStable();
    const enrollmentData = component.getEnrollmentData(BASIC);
    const initResponse = await lastValueFrom(tokenService.enrollToken(enrollmentData!));
    const finalResponse = await component.onEnrollmentResponse(
      initResponse as EnrollmentResponse,
      enrollmentData!.data
    );
    expect(finalResponse).toBeNull();
    expect(notification.openSnackBar).toHaveBeenCalledWith("WebAuthn finalization failed: finalize-fail");
  });

  it("getEnrollmentDataChange should wrap getEnrollmentData into an observable", async () => {
    let handler: ((data: any) => any) | undefined;
    component.getEnrollmentDataChange.subscribe((fn) => (handler = fn));

    (navigator as any).credentials = { create: jest.fn().mockResolvedValue(makePublicKeyCredential()) };

    await detectChangesStable();

    expect(typeof handler).toBe("function");
    const enrollmentData = handler!(BASIC);

    expect(enrollmentData).toEqual({
      data: { realm: "default", type: "webauthn", user: "alice" },
      mapper: expect.any(Object)
    });
  });
});
