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
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { EnrollPasskeyComponent } from "./enroll-passkey.component";
import {
  MockBase64Service,
  MockDialogService,
  MockNotificationService,
  MockTokenService
} from "../../../../../testing/mock-services";
import { TokenService } from "../../../../services/token/token.service";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { Base64Service } from "../../../../services/base64/base64.service";
import { NotificationService } from "../../../../services/notification/notification.service";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { lastValueFrom, of, throwError } from "rxjs";

describe("EnrollPasskeyComponent", () => {
  let component: EnrollPasskeyComponent;
  let fixture: ComponentFixture<EnrollPasskeyComponent>;

  let tokenSvc: MockTokenService;
  let dialogSvc: MockDialogService;
  let b64: MockBase64Service;
  let notif: MockNotificationService;

  const origCreds = navigator.credentials;

  function setNavigatorCredentials(obj: any) {
    Object.defineProperty(navigator, "credentials", {
      configurable: true,
      get: () => obj
    });
  }

  beforeEach(async () => {
    jest.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [EnrollPasskeyComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: Base64Service, useClass: MockBase64Service },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollPasskeyComponent);
    component = fixture.componentInstance;

    tokenSvc = TestBed.inject(TokenService) as any;
    dialogSvc = TestBed.inject(DialogService) as any;
    b64 = TestBed.inject(Base64Service) as any;
    notif = TestBed.inject(NotificationService) as any;

    fixture.detectChanges();
  });

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
    expect(() => component.getEnrollmentData({} as TokenEnrollmentData)).toThrow(/Passkey\/WebAuthn is not supported/i);
    expect(notif.openSnackBar).toHaveBeenCalledWith("Passkey/WebAuthn is not supported by this browser.");
  });

  it("happy path: init -> open dialog -> create cred -> finalize -> close", async () => {
    const finalResp = { detail: { serial: "S-1" } };

    const createdCred = {
      id: "cred-1",
      rawId: new Uint8Array([9, 9]).buffer,
      authenticatorAttachment: "platform",
      response: {
        attestationObject: new Uint8Array([7]).buffer,
        clientDataJSON: new Uint8Array([8]).buffer
      },
      getClientExtensionResults: () => ({ credProps: { rk: true } })
    };

    setNavigatorCredentials({
      create: jest.fn().mockResolvedValue(createdCred)
    });

    const reopenSpy = jest.spyOn(component.reopenDialogChange, "emit");

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
    } as any;
    const args = component.getEnrollmentData(initData);
    expect(args).not.toBeNull();
    tokenSvc.enrollToken.mockReturnValueOnce(lastValueFrom(of(initResp)));
    const initResponse = await tokenSvc.enrollToken(args);
    const res = await component.onEnrollmentResponse(initResponse, args!.data);

    expect(tokenSvc.enrollToken).toHaveBeenCalledTimes(2);
    expect(dialogSvc.openTokenEnrollmentFirstStepDialog).toHaveBeenCalledTimes(1);
    expect(dialogSvc.closeTokenEnrollmentFirstStepDialog).toHaveBeenCalledTimes(1);

    expect(b64.base64URLToBytes).toHaveBeenCalled();
    expect(b64.bytesToBase64).toHaveBeenCalled();

    expect(res).toStrictEqual(finalResp);
    expect(res?.detail.serial).toBe("S-1");

    const lastReopenArg = reopenSpy.mock.calls[reopenSpy.mock.calls.length - 1][0];
    expect(lastReopenArg).toBeUndefined();
  });

  it("handles invalid server response (no passkey_registration)", async () => {
    const initResp = { detail: { transaction_id: "t", serial: "S-9" } };
    tokenSvc.enrollToken.mockReturnValueOnce(of(initResp));

    setNavigatorCredentials({
      create: jest.fn()
    });

    const enrollmentData = component.getEnrollmentData({} as any);
    const initResponse = await lastValueFrom(tokenSvc.enrollToken(enrollmentData));
    const finalResponse = component.onEnrollmentResponse(initResponse as EnrollmentResponse, enrollmentData!.data);

    await expect(finalResponse).rejects.toThrow(/Invalid server response/i);

    expect(notif.openSnackBar).toHaveBeenCalledWith(
      "Failed to initiate Passkey registration: Invalid server response."
    );
    expect(dialogSvc.openTokenEnrollmentFirstStepDialog).not.toHaveBeenCalled();
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

    tokenSvc.enrollToken.mockReturnValueOnce(of(initResp)).mockReturnValueOnce(throwError(() => new Error("fin")));

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

    const enrollmentData = component.getEnrollmentData({} as any);
    const initResponse = await lastValueFrom(tokenSvc.enrollToken(enrollmentData));
    const finalResponse = component.onEnrollmentResponse(initResponse as EnrollmentResponse, enrollmentData!.data);

    await expect(finalResponse).rejects.toThrow();

    expect(notif.openSnackBar).toHaveBeenCalledWith(
      "Error during final Passkey registration step. Attempting to clean up token."
    );
    expect(tokenSvc.deleteToken).toHaveBeenCalledWith("S-2");
  });

  it("reopen dialog callback re-runs passkey init+finalize when dialog is closed", async () => {
    const createdCred = {
      id: "cred-1",
      rawId: new Uint8Array([1]).buffer,
      authenticatorAttachment: "platform",
      response: {
        attestationObject: new Uint8Array([2]).buffer,
        clientDataJSON: new Uint8Array([3]).buffer
      },
      getClientExtensionResults: () => ({})
    };
    Object.defineProperty(navigator, "credentials", {
      configurable: true,
      get: () => ({ create: jest.fn().mockResolvedValue(createdCred) })
    });

    const passkeyInit = (serial: string, tx: string) =>
      ({
        detail: {
          serial,
          transaction_id: tx,
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
      }) as EnrollmentResponse;

    const finalize = (serial: string) => ({ detail: { serial } });

    tokenSvc.enrollToken.mockReturnValueOnce(of(passkeyInit("S-1", "tx-1"))).mockReturnValueOnce(of(finalize("S-1")));

    let reopenCb: (() => Promise<EnrollmentResponse | null>) | undefined;

    component.reopenDialogChange.subscribe((fn) => (reopenCb = fn as any));

    const enrollmentData = component.getEnrollmentData({} as any);
    const initResponse = await lastValueFrom(tokenSvc.enrollToken(enrollmentData));
    const finalResponse = await component.onEnrollmentResponse(
      initResponse as EnrollmentResponse,
      enrollmentData!.data
    );
    expect(finalResponse).toEqual(finalize("S-1"));
    expect(dialogSvc.openTokenEnrollmentFirstStepDialog).toHaveBeenCalledTimes(1);
    expect(dialogSvc.closeTokenEnrollmentFirstStepDialog).toHaveBeenCalledTimes(1);

    expect(reopenCb).toBeUndefined();
  });
});
