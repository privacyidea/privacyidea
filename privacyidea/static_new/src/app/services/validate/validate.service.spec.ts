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
import { HttpClient, HttpHeaders, provideHttpClient } from "@angular/common/http";
import { TestBed } from "@angular/core/testing";
import { of, throwError } from "rxjs";

import { PiResponse } from "@app/app.component";
import { AuthResponse, AuthService } from "@services/auth/auth.service";
import { Base64Service } from "@services/base64/base64.service";
import { NotificationService } from "@services/notification/notification.service";
import { MockBase64Service, MockLocalService, MockNotificationService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { PasskeyCheckParams, ValidateCheckResponse, ValidateService, WebAuthnSignRequest } from "./validate.service";

interface PasskeyShim {
  isConditionalMediationAvailable?: jest.Mock | (() => Promise<boolean>);
}
interface WindowWithPasskey extends Omit<Window, "PublicKeyCredential"> {
  PublicKeyCredential?: PasskeyShim;
}
describe("ValidateService", () => {
  let validateService: ValidateService;
  let http: HttpClient;
  let postSpy: jest.SpyInstance;
  let consoleErrorSpy: jest.SpyInstance;

  let notif: MockNotificationService;
  let b64: MockBase64Service;
  let auth: MockAuthService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        ValidateService,
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: Base64Service, useClass: MockBase64Service },
        { provide: AuthService, useClass: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    });

    validateService = TestBed.inject(ValidateService);
    http = TestBed.inject(HttpClient);
    postSpy = jest.spyOn(http, "post");

    consoleErrorSpy = jest.spyOn(console, "error").mockReturnValue();

    notif = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    b64 = TestBed.inject(Base64Service) as unknown as MockBase64Service;
    auth = TestBed.inject(AuthService) as unknown as MockAuthService;
  });

  afterEach(() => {
    jest.restoreAllMocks();
    consoleErrorSpy.mockRestore();
  });

  it("should be created", () => {
    expect(validateService).toBeTruthy();
  });

  it("testToken should POST correct payload and return API result", () => {
    const apiResp: ValidateCheckResponse = {
      success: true,
      detail: { message: "OK" }
    } as unknown as ValidateCheckResponse;
    postSpy.mockReturnValue(of(apiResp));

    let result!: ValidateCheckResponse;
    validateService.testToken("HOTP1", "000000", "1").subscribe((r) => (result = r));

    const [url, body, opts] = (http.post as jest.Mock).mock.calls[0];
    expect(url).toBe("/validate/check");
    expect(body).toEqual({ otponly: "1", pass: "000000", serial: "HOTP1" });
    expect(opts.headers instanceof HttpHeaders).toBe(true);
    expect(result).toEqual(apiResp);
  });

  describe("authenticatePasskey", () => {
    it("should error and notify when WebAuthn is unsupported", async () => {
      const win = window as WindowWithPasskey;
      const original = win.PublicKeyCredential;
      win.PublicKeyCredential = undefined;
      const restore = () => {
        win.PublicKeyCredential = original;
      };

      validateService.authenticatePasskey().subscribe({
        next: () => fail("expected error"),
        error: (err) => {
          expect(err.message).toMatch(/WebAuthn is not supported/i);
          expect(notif.error).toHaveBeenCalledWith("WebAuthn is not supported by this browser.");
        }
      });

      restore();
    });

    it("should initialise, collect credentials, then POST /check when isTest=true", async () => {
      const credGet = jest.fn().mockResolvedValue({
        id: "cred-1",
        response: {
          authenticatorData: new ArrayBuffer(2),
          clientDataJSON: new ArrayBuffer(2),
          signature: new ArrayBuffer(2),
          userHandle: new ArrayBuffer(2)
        }
      });

      const win = window as WindowWithPasskey;
      const pkc: PasskeyShim = win.PublicKeyCredential ?? {};
      pkc.isConditionalMediationAvailable = jest.fn().mockResolvedValue(true);
      if (!win.PublicKeyCredential) {
        win.PublicKeyCredential = pkc;
      }

      Object.defineProperty(navigator, "credentials", {
        value: { get: credGet },
        configurable: true
      });

      const initResp = {
        detail: {
          passkey: {
            challenge: "abc",
            rpId: "example.com",
            transaction_id: "tid-42"
          }
        }
      };
      let capturedCheckBody: PasskeyCheckParams | undefined;

      postSpy
        .mockImplementationOnce(() => of(initResp))
        .mockImplementationOnce((_url, body) => {
          capturedCheckBody = body as PasskeyCheckParams;
          return of({ success: true });
        });

      let final!: AuthResponse;
      validateService.authenticatePasskey({ isTest: true }).subscribe((r) => (final = r as AuthResponse));

      jest.runOnlyPendingTimers();
      await Promise.resolve();

      jest.runOnlyPendingTimers();
      await Promise.resolve();

      expect(postSpy).toHaveBeenCalledTimes(2);
      expect(postSpy.mock.calls[0][0]).toMatch(/\/validate\/initialize$/);
      expect(postSpy.mock.calls[1][0]).toMatch(/\/validate\/check$/);
      expect(capturedCheckBody).toMatchObject({
        transaction_id: "tid-42",
        credential_id: "cred-1"
      });

      expect(b64.bytesToBase64).toHaveBeenCalled();
      expect(auth.authenticate).not.toHaveBeenCalled();
      expect(final).toEqual({ success: true });
    });

    describe("testToken (errors)", () => {
      it("notifies and rethrows when POST /check fails with API message", (done) => {
        postSpy.mockReturnValueOnce(throwError(() => ({ error: { result: { error: { message: "Bad OTP" } } } })));

        validateService.testToken("HOTP1", "000000").subscribe({
          next: () => done.fail("expected error"),
          error: (err) => {
            expect(consoleErrorSpy).toHaveBeenCalled();
            expect((notif.error as jest.Mock).mock.calls[0][0]).toContain("Failed to test token. Bad OTP");
            expect(err).toBeTruthy();
            done();
          }
        });
      });

      it("falls back to generic message when no API message is present", (done) => {
        postSpy.mockReturnValueOnce(throwError(() => new Error("boom")));

        validateService.testToken("HOTP1", "000000").subscribe({
          next: () => done.fail("expected error"),
          error: () => {
            expect((notif.error as jest.Mock).mock.calls[0][0]).toContain("Failed to test token.");
            done();
          }
        });
      });
    });

    describe("authenticatePasskey (more branches)", () => {
      const setupWebAuthn = (credGetImpl: () => Promise<unknown>) => {
        const win = window as WindowWithPasskey;
        const pkc: PasskeyShim = win.PublicKeyCredential ?? {};
        pkc.isConditionalMediationAvailable = jest.fn().mockResolvedValue(true);
        win.PublicKeyCredential = pkc;

        Object.defineProperty(navigator, "credentials", {
          value: { get: jest.fn().mockImplementation(credGetImpl) },
          configurable: true
        });
      };

      it("handles initialize error (POST /initialize fails)", (done) => {
        setupWebAuthn(async () => ({}));
        postSpy.mockReturnValueOnce(throwError(() => ({ error: { result: { error: { message: "no init" } } } })));

        validateService.authenticatePasskey().subscribe({
          next: () => done.fail("expected error"),
          error: (err) => {
            expect(err.message).toBe("no init");
            expect(notif.error).toHaveBeenCalledWith("no init");
            done();
          }
        });
      });

      it("handles credential collection failure (navigator.credentials.get rejects)", async () => {
        setupWebAuthn(() => Promise.reject(new Error("user dismissed")));

        postSpy.mockImplementationOnce(() =>
          of({
            detail: {
              passkey: { challenge: "abc", rpId: "site", transaction_id: "tid-1" }
            }
          })
        );

        let caught: Error | undefined;
        await new Promise<void>((resolve) => {
          validateService.authenticatePasskey().subscribe({
            next: () => resolve(),
            error: (err) => {
              caught = err;
              resolve();
            }
          });
        });

        expect(caught?.message).toBe("user dismissed");
        expect(notif.error).toHaveBeenCalledWith("user dismissed");
      });

      it("when isTest=false uses authenticationService.authenticate instead of /check", async () => {
        const credGet = jest.fn().mockResolvedValue({
          id: "cred-xyz",
          response: {
            authenticatorData: new ArrayBuffer(1),
            clientDataJSON: new ArrayBuffer(1),
            signature: new ArrayBuffer(1),
            userHandle: new ArrayBuffer(1)
          }
        });
        const win = window as WindowWithPasskey;
        const pkc: PasskeyShim = win.PublicKeyCredential ?? {};
        pkc.isConditionalMediationAvailable = jest.fn().mockResolvedValue(true);
        win.PublicKeyCredential = pkc;

        Object.defineProperty(navigator, "credentials", {
          value: { get: credGet },
          configurable: true
        });

        postSpy.mockImplementationOnce(() =>
          of({ detail: { passkey: { challenge: "x", rpId: "r", transaction_id: "t" } } })
        );

        const authSpy = jest
          .spyOn(auth, "authenticate")
          .mockReturnValue(of({ success: true } as unknown as AuthResponse));

        let final: AuthResponse | undefined;
        await new Promise<void>((resolve) => {
          validateService.authenticatePasskey({ isTest: false }).subscribe((r) => {
            final = r;
            resolve();
          });
        });

        expect(postSpy).toHaveBeenCalledTimes(1);
        expect(authSpy).toHaveBeenCalledTimes(1);
        expect(final).toEqual({ success: true });

        expect(b64.bytesToBase64).toHaveBeenCalledTimes(4);
      });
    });

    describe("authenticateWebAuthn", () => {
      const okSignRequest = {
        challenge: "abc",
        allowCredentials: [{ id: "idA" }],
        rpId: "example.com",
        userVerification: "preferred",
        timeout: 60000
      };

      const setWebAuthn = (getImpl: () => Promise<unknown>) => {
        const win = window as WindowWithPasskey;
        win.PublicKeyCredential = win.PublicKeyCredential ?? {};
        Object.defineProperty(navigator, "credentials", {
          value: { get: jest.fn().mockImplementation(getImpl) },
          configurable: true
        });
      };

      it("errors early on invalid signRequest (try/catch path)", (done) => {
        const win = window as WindowWithPasskey;
        win.PublicKeyCredential = win.PublicKeyCredential ?? {};
        const bad = { ...okSignRequest, allowCredentials: undefined };

        validateService
          .authenticateWebAuthn({
            signRequest: bad as unknown as WebAuthnSignRequest,
            transaction_id: "T",
            username: "u",
            isTest: true
          })
          .subscribe({
            next: () => done.fail("expected error"),
            error: (err) => {
              expect(err.message).toBe("Invalid WebAuthn challenge data received from server.");
              expect(notif.error).toHaveBeenCalledWith("Invalid WebAuthn challenge data received from server.");
              done();
            }
          });
      });

      it("isTest=true: builds payload, posts /check, uses encoders", async () => {
        setWebAuthn(() =>
          Promise.resolve({
            id: "cred-id",
            response: {
              authenticatorData: new ArrayBuffer(1),
              clientDataJSON: new ArrayBuffer(1),
              signature: new ArrayBuffer(1),
              userHandle: new Uint8Array([117, 115, 101, 114]).buffer
            }
          })
        );

        let captured: Record<string, unknown> | undefined;
        postSpy.mockImplementationOnce((url, body) => {
          captured = body as Record<string, unknown>;
          return of({ success: true });
        });

        let final: AuthResponse | undefined;
        await new Promise<void>((resolve) => {
          validateService
            .authenticateWebAuthn({
              signRequest: okSignRequest as unknown as WebAuthnSignRequest,
              transaction_id: "T-1",
              username: "alice",
              isTest: true
            })
            .subscribe((r) => {
              final = r;
              resolve();
            });
        });

        expect(postSpy).toHaveBeenCalledTimes(1);
        expect(postSpy.mock.calls[0][0]).toMatch(/\/validate\/check$/);
        expect(captured).toMatchObject({
          transaction_id: "T-1",
          username: "alice",
          credential_id: "cred-id",
          authenticatorData: "enc",
          clientDataJSON: "enc",
          signature: "enc",
          userHandle: "user"
        });
        expect(b64.webAuthnBase64DecToArr).toHaveBeenCalled();
        expect(b64.webAuthnBase64EncArr).toHaveBeenCalledTimes(3);
        expect(b64.utf8ArrToStr).toHaveBeenCalled();
        expect(final).toEqual({ success: true });
      });

      it("isTest=false: uses authenticationService.authenticate instead of POST /check", async () => {
        setWebAuthn(() =>
          Promise.resolve({
            id: "cred-id",
            response: {
              authenticatorData: new ArrayBuffer(1),
              clientDataJSON: new ArrayBuffer(1),
              signature: new ArrayBuffer(1),
              userHandle: null
            }
          })
        );

        const authSpy = jest
          .spyOn(auth, "authenticate")
          .mockReturnValue(of({ ok: 1 } as unknown as AuthResponse));
        postSpy.mockImplementation(() => {
          throw new Error("should not POST in this branch");
        });

        let final: AuthResponse | undefined;
        await new Promise<void>((resolve) => {
          validateService
            .authenticateWebAuthn({
              signRequest: okSignRequest as unknown as WebAuthnSignRequest,
              transaction_id: "T-2",
              username: "bob",
              isTest: false
            })
            .subscribe((r) => {
              final = r;
              resolve();
            });
        });

        expect(authSpy).toHaveBeenCalledTimes(1);
        expect(final).toEqual({ ok: 1 });
      });

      it("handles navigator.credentials.get rejection (catchError path)", async () => {
        setWebAuthn(() => Promise.reject({ error: { result: { error: { message: "nope" } } } }));

        let caught: Error | undefined;
        await new Promise<void>((resolve) => {
          validateService
            .authenticateWebAuthn({
              signRequest: okSignRequest as unknown as WebAuthnSignRequest,
              transaction_id: "T-3",
              username: "eve",
              isTest: true
            })
            .subscribe({
              next: () => resolve(),
              error: (e) => {
                caught = e;
                resolve();
              }
            });
        });

        expect(caught?.message).toBe("nope");
        expect(notif.error).toHaveBeenCalledWith("nope");
      });

      it("unsupported WebAuthn shows snack and throws", (done) => {
        (window as WindowWithPasskey).PublicKeyCredential = undefined;

        validateService
          .authenticateWebAuthn({
            signRequest: okSignRequest as unknown as WebAuthnSignRequest,
            transaction_id: "T-4",
            username: "mallory",
            isTest: true
          })
          .subscribe({
            next: () => done.fail("expected error"),
            error: (err) => {
              expect(err.message).toMatch(/not supported/i);
              expect(notif.error).toHaveBeenCalled();
              done();
            }
          });
      });
    });

    describe("pollTransaction", () => {
      it("returns true only when authentication=ACCEPT and value=true", (done) => {
        const httpGet = jest.spyOn(TestBed.inject(HttpClient), "get");

        httpGet.mockReturnValueOnce(
          of({ result: { authentication: "ACCEPT", value: true } } as unknown as PiResponse<boolean>)
        );

        validateService.pollTransaction("tid").subscribe((res) => {
          expect(res).toBe(true);
          done();
        });
      });

      it("returns false for other combinations", (done) => {
        const httpGet = jest.spyOn(TestBed.inject(HttpClient), "get");

        httpGet.mockReturnValueOnce(
          of({ result: { authentication: "ACCEPT", value: false } } as unknown as PiResponse<boolean>)
        );

        validateService.pollTransaction("tid").subscribe((res) => {
          expect(res).toBe(false);
          done();
        });
      });

      it("notifies and rethrows on GET failure", (done) => {
        const httpGet = jest.spyOn(TestBed.inject(HttpClient), "get");
        httpGet.mockReturnValueOnce(throwError(() => ({ error: { result: { error: { message: "poll failed" } } } })));

        validateService.pollTransaction("tid").subscribe({
          next: () => done.fail("expected error"),
          error: (err) => {
            expect(consoleErrorSpy).toHaveBeenCalled();
            expect(notif.error).toHaveBeenCalledWith("poll failed");
            expect(err).toBeTruthy();
            done();
          }
        });
      });
    });
  });
});
