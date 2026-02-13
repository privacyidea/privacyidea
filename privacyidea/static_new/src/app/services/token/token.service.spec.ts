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
import { HttpClient, HttpErrorResponse, HttpParams, provideHttpClient } from "@angular/common/http";
import { lastValueFrom, of, throwError } from "rxjs";

import { ContentService } from "../content/content.service";
import { NotificationService } from "../notification/notification.service";
import { PiResponse } from "../../app.component";
import { TestBed } from "@angular/core/testing";
import { TokenService } from "./token.service";
import { AuthService } from "../auth/auth.service";
import { FilterValue } from "../../core/models/filter_value";
import { MockContentService } from "../../../testing/mock-services";
import { ROUTE_PATHS } from "../../route_paths";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { environment } from "../../../environments/environment";
import { MockAuthService } from "../../../testing/mock-services/mock-auth-service";
import { DialogService } from "../dialog/dialog.service";
import { MockDialogService } from "../../../testing/mock-services/mock-dialog-service";
import { MockMatDialogRef } from "../../../testing/mock-mat-dialog-ref";

class MockNotificationService {
  openSnackBar = jest.fn();
}

describe("TokenService", () => {
  let tokenService: TokenService;
  let http: HttpClient;
  let postSpy: jest.SpyInstance;
  let deleteSpy: jest.SpyInstance;
  let authService: MockAuthService;
  let notificationService: MockNotificationService;
  let contentServiceMock: MockContentService;
  let dialogServiceMock: MockDialogService;
  let getSpy: jest.SpyInstance;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        TokenService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    });

    tokenService = TestBed.inject(TokenService);
    contentServiceMock = TestBed.inject(ContentService) as unknown as MockContentService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    http = TestBed.inject(HttpClient);
    postSpy = jest.spyOn(http, "post");
    deleteSpy = jest.spyOn(http, "delete");
    authService = TestBed.inject(AuthService) as any;
    notificationService = TestBed.inject(NotificationService) as any;
    getSpy = jest.spyOn(http, "get");

    jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe("toggleActive()", () => {
    it("POSTs to /disable when active=true", () => {
      const backend: PiResponse<boolean> = {
        success: true,
        detail: undefined
      } as any;

      postSpy.mockReturnValue(of(backend));

      let result!: PiResponse<boolean>;
      tokenService.toggleActive("HOTP1", true).subscribe((r) => (result = r));

      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}disable`,
        { serial: "HOTP1" },
        { headers: authService.getHeaders() }
      );
      expect(result).toEqual(backend);
    });

    it("POSTs to /enable when active=false", () => {
      postSpy.mockReturnValue(of({ success: true } as any));

      tokenService.toggleActive("HOTP1", false).subscribe();

      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}enable`,
        { serial: "HOTP1" },
        { headers: authService.getHeaders() }
      );
    });

    it("notifies user and propagates error on failure", (done) => {
      const error = new HttpErrorResponse({
        error: { result: { error: { message: "boom" } } },
        status: 500
      });
      postSpy.mockReturnValue(throwError(() => error));

      tokenService.toggleActive("HOTP1", true).subscribe({
        next: () => {
          fail("expected error");
        },
        error: (err) => {
          expect(err).toBe(error);
          expect(notificationService.openSnackBar).toHaveBeenCalledWith("Failed to toggle active. boom");
          done();
        }
      });
    });
  });

  it("resetFailCount posts /reset with correct body", () => {
    postSpy.mockReturnValue(of({ success: true } as any));

    tokenService.resetFailCount("HOTP2").subscribe();

    expect(postSpy).toHaveBeenCalledWith(
      `${tokenService.tokenBaseUrl}reset`,
      { serial: "HOTP2" },
      { headers: authService.getHeaders() }
    );
  });

  it("deleteToken delegates to HttpClient.delete", () => {
    deleteSpy.mockReturnValue(of({ success: true } as any));

    tokenService.deleteToken("DEL1").subscribe();

    expect(deleteSpy).toHaveBeenCalledWith(`${tokenService.tokenBaseUrl}DEL1`, {
      headers: authService.getHeaders()
    });
  });

  describe("saveTokenDetail()", () => {
    it("maps 'maxfail' to 'max_failcount'", () => {
      postSpy.mockReturnValue(of({ success: true } as any));

      tokenService.saveTokenDetail("serial", "maxfail", 3).subscribe();

      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}set`,
        { serial: "serial", max_failcount: 3 },
        { headers: authService.getHeaders() }
      );
    });

    it("passes other keys through unchanged", () => {
      postSpy.mockReturnValue(of({ success: true } as any));

      tokenService.saveTokenDetail("serial", "description", "A token").subscribe();

      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}set`,
        { serial: "serial", description: "A token" },
        { headers: authService.getHeaders() }
      );
    });
  });

  describe("setTokenInfos()", () => {
    beforeEach(() => postSpy.mockClear());

    it("routes special keys via /set and others via /info", () => {
      const infos = { hashlib: "sha1", custom: "foo" };
      postSpy.mockReturnValue(of({ success: true } as any));

      tokenService.setTokenInfos("serial", infos).subscribe();

      expect(postSpy).toHaveBeenNthCalledWith(
        1,
        `${tokenService.tokenBaseUrl}set`,
        { serial: "serial", hashlib: "sha1" },
        { headers: authService.getHeaders() }
      );
      expect(postSpy).toHaveBeenNthCalledWith(
        2,
        `${tokenService.tokenBaseUrl}info/serial/custom`,
        { value: "foo" },
        { headers: authService.getHeaders() }
      );
    });
  });

  describe("assignUser()", () => {
    it("translates empty strings to null", () => {
      postSpy.mockReturnValue(of({ success: true } as any));

      tokenService
        .assignUser({
          tokenSerial: "serial",
          username: "",
          realm: "",
          pin: "123"
        })
        .subscribe();

      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}assign`,
        { serial: "serial", user: null, realm: null, pin: "123" },
        { headers: authService.getHeaders() }
      );
    });
  });

  describe("unassignUserFromAll()", () => {
    it("returns an empty array for empty input", (done) => {
      tokenService.unassignUserFromAll([]).subscribe((r) => {
        expect(r).toEqual([]);
        done();
      });
    });
  });

  describe("setTokengroup()", () => {
    it("accepts a single string", () => {
      postSpy.mockReturnValue(of({ success: true } as any));
      tokenService.setTokengroup("serial", "group1").subscribe();

      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}group/serial`,
        { groups: ["group1"] },
        { headers: authService.getHeaders() }
      );
    });

    it("accepts an object and flattens values", () => {
      postSpy.mockReturnValue(of({ success: true } as any));
      tokenService.setTokengroup("serial", { a: "g1", b: "g2" } as any).subscribe();

      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}group/serial`,
        { groups: ["g1", "g2"] },
        { headers: authService.getHeaders() }
      );
    });
  });

  describe("pollTokenRolloutState()", () => {
    it("emits error once and stops polling when request fails", async () => {
      jest.useFakeTimers();
      const boom = new HttpErrorResponse({
        error: { result: { error: { message: "poll-error" } } },
        status: 500
      });
      jest.spyOn(tokenService, "getTokenDetails").mockReturnValueOnce(throwError(() => boom));

      const errors: any[] = [];
      tokenService
        .pollTokenRolloutState({ tokenSerial: "serial", initDelay: 0 })
        .subscribe({ error: (e) => errors.push(e) });

      jest.runOnlyPendingTimers();
      await Promise.resolve();

      expect(errors[0]).toBe(boom);
      expect(notificationService.openSnackBar).toHaveBeenCalledWith("Failed to poll token state. poll-error");
    });
    jest.useRealTimers();
  });

  it("polls until rollout_state !== 'clientwait'", async () => {
    jest.useFakeTimers();
    const first = {
      result: { value: { tokens: [{ rollout_state: "clientwait" }] } }
    };
    const second = {
      result: { value: { tokens: [{ rollout_state: "clientwait" }] } }
    };
    const done = {
      result: { value: { tokens: [{ rollout_state: "enrolled" }] } }
    };

    jest
      .spyOn(tokenService, "getTokenDetails")
      .mockReturnValueOnce(of(first as any))
      .mockReturnValueOnce(of(second as any))
      .mockReturnValueOnce(of(done as any));

    const emissions: any[] = [];
    tokenService.pollTokenRolloutState({ tokenSerial: "HOTP3", initDelay: 0 }).subscribe((r) => emissions.push(r));

    // wait four ticks but getTokenDetails should be called three times
    jest.runOnlyPendingTimers();
    await Promise.resolve();

    jest.advanceTimersByTime(2000);
    await Promise.resolve();

    jest.advanceTimersByTime(2000);
    await Promise.resolve();

    jest.advanceTimersByTime(2000);
    await Promise.resolve();

    expect(tokenService.getTokenDetails).toHaveBeenCalledTimes(3);
    expect(emissions.length).toBe(3);
    expect(emissions[2]).toEqual(done);

    jest.advanceTimersByTime(4000);
    expect(tokenService.getTokenDetails).toHaveBeenCalledTimes(3);
    jest.useRealTimers();
  });

  describe("reactive helpers", () => {
    it("filterParams wildcard‑wraps non‑ID fields", () => {
      tokenService.tokenFilter.set(new FilterValue({ value: "serial: otp user: alice description: vpn" }));
      expect(tokenService.filterParams()).toEqual({
        serial: "*otp*",
        // user: "alice",
        description: "*vpn*"
      });
    });
  });

  describe("revokeToken()", () => {
    it("posts /revoke and propagates result", (done) => {
      postSpy.mockReturnValue(of({ success: true } as any));

      tokenService.revokeToken("serial").subscribe((r) => {
        expect(postSpy).toHaveBeenCalledWith(
          `${tokenService.tokenBaseUrl}revoke`,
          { serial: "serial" },
          { headers: authService.getHeaders() }
        );
        expect(r).toEqual({ success: true });
        done();
      });
    });

    it("notifies on error", (done) => {
      const boom = new HttpErrorResponse({
        error: { result: { error: { message: "rvk" } } },
        status: 500
      });
      postSpy.mockReturnValue(throwError(() => boom));

      tokenService.revokeToken("serial").subscribe({
        error: (e) => {
          expect(e).toBe(boom);
          expect(notificationService.openSnackBar).toHaveBeenCalledWith("Failed to revoke token. rvk");
          done();
        }
      });
    });
  });

  describe("PIN helpers", () => {
    it("setPin posts /setpin", () => {
      postSpy.mockReturnValue(of({}));
      tokenService.setPin("serial", "9876").subscribe();
      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}setpin`,
        { serial: "serial", otppin: "9876" },
        { headers: authService.getHeaders() }
      );
    });

    it("setRandomPin posts /setrandompin", () => {
      postSpy.mockReturnValue(of({}));
      tokenService.setRandomPin("serial").subscribe();
      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}setrandompin`,
        { serial: "serial" },
        { headers: authService.getHeaders() }
      );
    });

    it("resyncOTPToken posts /resync", () => {
      postSpy.mockReturnValue(of({}));
      tokenService.resyncOTPToken("S", "111", "222").subscribe();
      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}resync`,
        { serial: "S", otp1: "111", otp2: "222" },
        { headers: authService.getHeaders() }
      );
    });
  });

  describe("realm & lost token", () => {
    it("setTokenRealm posts correct body", () => {
      postSpy.mockReturnValue(of({}));
      tokenService.setTokenRealm("serial", ["r1", "r2"]).subscribe();
      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}realm/serial`,
        { realms: ["r1", "r2"] },
        { headers: authService.getHeaders() }
      );
    });

    it("lostToken hits /lost endpoint", () => {
      postSpy.mockReturnValue(of({}));
      tokenService.lostToken("serial").subscribe();
      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}lost/serial`,
        {},
        { headers: authService.getHeaders() }
      );
    });
  });

  describe("bulk user assign/unassign", () => {
    it("assignUserToAll maps serials to assignUser calls", (done) => {
      const stub = jest.spyOn(tokenService, "assignUser").mockReturnValue(of({ ok: true } as any));

      tokenService
        .assignUserToAll({
          tokenSerials: ["S1", "S2"],
          username: "u",
          realm: "r",
          pin: "p"
        })
        .subscribe((arr) => {
          expect(stub).toHaveBeenCalledTimes(2);
          expect(arr.length).toBe(2);
          done();
        });
    });

    it("unassignUserFromAll maps serials to unassignUser calls", (done) => {
      const un = jest.spyOn(tokenService, "unassignUser").mockReturnValue(of({ ok: true } as any));

      tokenService.unassignUserFromAll(["X", "Y"]).subscribe((arr) => {
        expect(un).toHaveBeenCalledTimes(2);
        expect(arr.length).toBe(2);
        done();
      });
    });
  });

  describe("helper methods – error branches", () => {
    const makeErr = (msg: string) =>
      new HttpErrorResponse({
        error: { result: { error: { message: msg } } },
        status: 500
      });

    afterEach(() => postSpy.mockClear());

    it.each([
      ["setPin", () => tokenService.setPin("X", "1"), "Failed to set PIN. boom"],
      ["setRandomPin", () => tokenService.setRandomPin("X"), "Failed to set random PIN. boom"],
      ["resyncOTPToken", () => tokenService.resyncOTPToken("X", "111", "222"), "Failed to resync OTP token. boom"],
      ["setTokenRealm", () => tokenService.setTokenRealm("X", ["r"]), "Failed to set token realm. boom"],
      ["lostToken", () => tokenService.lostToken("X"), "Failed to mark token as lost. boom"]
    ])("%s() notifies on error", async (_label, call, expected) => {
      postSpy.mockReturnValue(throwError(() => makeErr("boom")));

      await expect(lastValueFrom(call())).rejects.toMatchObject({
        error: { result: { error: { message: "boom" } } }
      });

      expect(notificationService.openSnackBar).toHaveBeenCalledWith(expected);
    });

    it("assignUserToAll stops on first error and shows snackbar", (done) => {
      jest
        .spyOn(tokenService, "assignUser")
        .mockReturnValueOnce(throwError(() => makeErr("first")))
        .mockReturnValue(of({ ok: true } as any));

      tokenService
        .assignUserToAll({
          tokenSerials: ["S1", "S2"],
          username: "u",
          realm: "r"
        })
        .subscribe({
          next: () => fail("should error"),
          error: (e) => {
            expect(e.error.result.error.message).toBe("first");
            expect(notificationService.openSnackBar).toHaveBeenCalledWith("Failed to assign user to all tokens. first");
            done();
          }
        });
    });

    it("unassignUserFromAll propagates error and shows snackbar", (done) => {
      jest
        .spyOn(tokenService, "unassignUser")
        .mockReturnValueOnce(throwError(() => makeErr("oops")))
        .mockReturnValue(of({ ok: true } as any));

      tokenService.unassignUserFromAll(["T1", "T2"]).subscribe({
        next: () => fail("should error"),
        error: (e) => {
          expect(e.error.result.error.message).toBe("oops");
          expect(notificationService.openSnackBar).toHaveBeenCalledWith(
            "Failed to unassign user from all tokens. oops"
          );
          done();
        }
      });
    });
  });

  describe("bulkDeleteTokens()", () => {
    it("DELETEs with body of serials and propagates result", (done) => {
      const backend = { success: true } as any;
      deleteSpy.mockReturnValue(of(backend));

      tokenService.bulkDeleteTokens(["S1", "S2"]).subscribe((r) => {
        expect(deleteSpy).toHaveBeenCalledWith(tokenService.tokenBaseUrl, {
          headers: authService.getHeaders(),
          body: { serials: ["S1", "S2"] }
        });
        expect(r).toBe(backend);
        done();
      });
    });

    it("notifies user on error", (done) => {
      const boom = new HttpErrorResponse({
        error: { result: { error: { message: "bd" } } },
        status: 500
      });
      deleteSpy.mockReturnValue(throwError(() => boom));

      tokenService.bulkDeleteTokens(["S"]).subscribe({
        next: () => fail("expected error"),
        error: (e) => {
          expect(e).toBe(boom);
          // service reads error.result?.error?.message; keep assertion loose
          expect(notificationService.openSnackBar).toHaveBeenCalledWith(
            expect.stringContaining("Failed to delete tokens.")
          );
          done();
        }
      });
    });
  });

  describe("bulkDeleteWithConfirmDialog()", () => {
    let afterDeleteCallback: jest.Mock;

    beforeEach(() => {
      afterDeleteCallback = jest.fn();
      const dialogRefMock = new MockMatDialogRef();
      dialogRefMock.afterClosed.mockReturnValue(of(true));
      dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    });

    it("should open confirmation dialog", () => {
      tokenService.bulkDeleteWithConfirmDialog(["S1"], afterDeleteCallback);
      expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    });

    it("should do nothing if dialog is cancelled", () => {
      dialogServiceMock.openDialog.mockReturnValue({ afterClosed: () => of(false) });
      const bulkDeleteSpy = jest.spyOn(tokenService, "bulkDeleteTokens").mockReturnValue(of());
      tokenService.bulkDeleteWithConfirmDialog(["S1"], afterDeleteCallback);
      expect(bulkDeleteSpy).not.toHaveBeenCalled();
    });

    it("should call bulkDeleteTokens and afterDelete callback on success", (done) => {
      const response = { result: { value: { count_success: 1, failed: [], unauthorized: [] } } };
      const bulkDeleteSpy = jest.spyOn(tokenService, "bulkDeleteTokens").mockReturnValue(of(response as any));

      tokenService.bulkDeleteWithConfirmDialog(["S1"], afterDeleteCallback);

      expect(bulkDeleteSpy).toHaveBeenCalledWith(["S1"]);
      setTimeout(() => {
        expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully deleted 1 token.");
        expect(afterDeleteCallback).toHaveBeenCalled();
        done();
      }, 0);
    });

    it("should show a notification if some tokens failed or were unauthorized", (done) => {
      const response = {
        result: {
          value: {
            count_success: 1,
            failed: ["TOKEN1"],
            unauthorized: ["TOKEN2"]
          }
        }
      };
      jest.spyOn(tokenService, "bulkDeleteTokens").mockReturnValue(of(response as any));

      tokenService.bulkDeleteWithConfirmDialog(["S1", "TOKEN1", "TOKEN2"]);

      setTimeout(() => {
        expect(notificationService.openSnackBar).toHaveBeenCalledWith(
          "Successfully deleted 1 token.\nThe following tokens failed to delete: TOKEN1\nYou are not authorized to delete the following tokens: TOKEN2"
        );
        done();
      }, 0);
    });

    it("should handle API errors gracefully", (done) => {
      const error = new HttpErrorResponse({
        error: { error: { result: { error: { message: "API Error" } } } },
        status: 500
      });
      jest.spyOn(tokenService, "bulkDeleteTokens").mockReturnValue(throwError(() => error));

      tokenService.bulkDeleteWithConfirmDialog(["S1"]);

      setTimeout(() => {
        expect(notificationService.openSnackBar).toHaveBeenCalledWith("An error occurred while deleting tokens.");
        done();
      }, 0);
    });
  });

  describe("deleteInfo()", () => {
    it("DELETEs the /info/:serial/:key endpoint", () => {
      deleteSpy.mockReturnValue(of({}));
      tokenService.deleteInfo("SER", "infokey").subscribe();

      expect(deleteSpy).toHaveBeenCalledWith(`${tokenService.tokenBaseUrl}info/SER/infokey`, {
        headers: authService.getHeaders()
      });
    });

    it("notifies on error", (done) => {
      const boom = new HttpErrorResponse({
        error: { result: { error: { message: "di" } } },
        status: 500
      });
      deleteSpy.mockReturnValue(throwError(() => boom));

      tokenService.deleteInfo("SER", "infokey").subscribe({
        error: (e) => {
          expect(e).toBe(boom);
          expect(notificationService.openSnackBar).toHaveBeenCalledWith("Failed to delete token info. di");
          done();
        }
      });
    });
  });

  describe("unassignUser()", () => {
    it("notifies on error", (done) => {
      const boom = new HttpErrorResponse({
        error: { result: { error: { message: "uu" } } },
        status: 500
      });
      postSpy.mockReturnValue(throwError(() => boom));

      tokenService.unassignUser("SER").subscribe({
        error: (e) => {
          expect(e).toBe(boom);
          expect(notificationService.openSnackBar).toHaveBeenCalledWith("Failed to unassign user. uu");
          done();
        }
      });
    });
  });

  describe("assignUser()", () => {
    it("notifies on error", (done) => {
      const boom = new HttpErrorResponse({
        error: { result: { error: { message: "au" } } },
        status: 500
      });
      postSpy.mockReturnValue(throwError(() => boom));

      tokenService.assignUser({ tokenSerial: "S", username: "u", realm: "r" }).subscribe({
        error: (e) => {
          expect(e).toBe(boom);
          expect(notificationService.openSnackBar).toHaveBeenCalledWith("Failed to assign user. au");
          done();
        }
      });
    });
  });

  describe("resetFailCount()", () => {
    it("notifies on error", (done) => {
      const boom = new HttpErrorResponse({
        error: { result: { error: { message: "rf" } } },
        status: 500
      });
      postSpy.mockReturnValue(throwError(() => boom));

      tokenService.resetFailCount("SER").subscribe({
        error: (e) => {
          expect(e).toBe(boom);
          expect(notificationService.openSnackBar).toHaveBeenCalledWith("Failed to reset fail count. rf");
          done();
        }
      });
    });
  });

  describe("setTokengroup()", () => {
    it("notifies on error", (done) => {
      const boom = new HttpErrorResponse({
        error: { result: { error: { message: "stg" } } },
        status: 500
      });
      postSpy.mockReturnValue(throwError(() => boom));

      tokenService.setTokengroup("SER", ["g"]).subscribe({
        error: (e) => {
          expect(e).toBe(boom);
          expect(notificationService.openSnackBar).toHaveBeenCalledWith("Failed to set token group. stg");
          done();
        }
      });
    });
  });

  describe("setTokenInfos() – error branch", () => {
    it("bubbles error from any request and shows snackbar", (done) => {
      // first call (special key) succeeds, second (/info) fails
      postSpy
        .mockReturnValueOnce(of({ success: true } as any))
        .mockReturnValueOnce(
          throwError(() => new HttpErrorResponse({ error: { result: { error: { message: "oops" } } }, status: 500 }))
        );

      tokenService.setTokenInfos("SER", { hashlib: "sha1", custom: "x" }).subscribe({
        next: () => fail("expected error"),
        error: (e) => {
          expect(notificationService.openSnackBar).toHaveBeenCalledWith("Failed to set token info. oops");
          done();
        }
      });
    });
  });

  describe("getSerial()", () => {
    it("GETs correct URL with params and headers", () => {
      getSpy.mockReturnValue(of({ success: true } as any));
      const params = new HttpParams().set("user", "alice");

      tokenService.getSerial("123456", params).subscribe();

      expect(getSpy).toHaveBeenCalledWith(`${tokenService.tokenBaseUrl}getserial/123456`, {
        params,
        headers: authService.getHeaders()
      });
    });

    it("notifies on error", (done) => {
      const boom = new HttpErrorResponse({
        error: { result: { error: { message: "cnt" } } },
        status: 500
      });
      getSpy.mockReturnValue(throwError(() => boom));

      tokenService.getSerial("111111", new HttpParams()).subscribe({
        error: (e) => {
          expect(e).toBe(boom);
          expect(notificationService.openSnackBar).toHaveBeenCalledWith("Failed to get count. cnt");
          done();
        }
      });
    });
  });

  describe("getTokenDetails()", () => {
    it("GETs /token with serial as HttpParams", () => {
      getSpy.mockReturnValue(of({} as any));
      tokenService.getTokenDetails("ABC").subscribe();

      const call = getSpy.mock.calls[0];
      expect(call[0]).toBe(tokenService.tokenBaseUrl);
      const opts = call[1] as any;
      expect(opts.headers).toEqual(authService.getHeaders());
      expect(opts.params.get("serial")).toBe("ABC");
    });
  });

  describe("getTokengroups()", () => {
    it("GETs /tokengroup", () => {
      getSpy.mockReturnValue(of({} as any));
      tokenService.getTokengroups().subscribe();

      // derive expected URL from known base to avoid importing environment
      const expected = tokenService.tokenBaseUrl.replace("/token/", "/tokengroup/");
      expect(getSpy).toHaveBeenCalledWith(expected, { headers: authService.getHeaders() });
    });

    it("notifies on error", (done) => {
      const boom = new HttpErrorResponse({
        error: { result: { error: { message: "tg" } } },
        status: 500
      });
      getSpy.mockReturnValue(throwError(() => boom));

      tokenService.getTokengroups().subscribe({
        error: (e) => {
          expect(e).toBe(boom);
          expect(notificationService.openSnackBar).toHaveBeenCalledWith("Failed to get tokengroups. tg");
          done();
        }
      });
    });
  });

  describe("saveTokenDetail() – error branch", () => {
    it("notifies on error", (done) => {
      const boom = new HttpErrorResponse({
        error: { result: { error: { message: "std" } } },
        status: 500
      });
      postSpy.mockReturnValue(throwError(() => boom));

      tokenService.saveTokenDetail("S", "description", "d").subscribe({
        error: (e) => {
          expect(e).toBe(boom);
          expect(notificationService.openSnackBar).toHaveBeenCalledWith("Failed to set token detail. std");
          done();
        }
      });
    });
  });

  it("should not include empty filter values in filterParams", () => {
    tokenService.tokenFilter.set(
      new FilterValue({
        value: "serial: '' type: hotp active: '  ' description: * rollout_state: ***"
      })
    );

    const params = tokenService.filterParams();
    expect(params).not.toHaveProperty("serial");
    expect(params).not.toHaveProperty("active");
    expect(params).toHaveProperty("type", "*hotp*");
    expect(params).not.toHaveProperty("description");
    expect(params).not.toHaveProperty("rollout_state");
  });

  describe("userTokenResource", () => {
    it("should return undefined if route is not USER_DETAILS", async () => {
      contentServiceMock.routeUrl.update(() => ROUTE_PATHS.TOKENS);
      const mockBackend = TestBed.inject(HttpTestingController);
      TestBed.flushEffects();

      // Expect and flush the HTTP request
      mockBackend.expectNone(environment.proxyUrl + "/token/");
      await Promise.resolve();

      expect(tokenService.userTokenResource.value()).toBeUndefined();
    });

    it("should do request if route is USER_DETAILS", async () => {
      const realm = "test-realm";
      const user = "alice";
      contentServiceMock.routeUrl.update(() => ROUTE_PATHS.USERS_DETAILS + "/" + user);
      contentServiceMock.detailsUsername.set(user);
      tokenService.userRealm.set(realm);
      const mockBackend = TestBed.inject(HttpTestingController);
      TestBed.flushEffects();

      // Expect and flush the HTTP request
      const req = mockBackend.expectOne(environment.proxyUrl + "/token/?user=" + user + "&realm=" + realm);
      req.flush({ result: {} });
      await Promise.resolve();

      expect(tokenService.userTokenResource.value()).toBeDefined();
    });
  });
});
