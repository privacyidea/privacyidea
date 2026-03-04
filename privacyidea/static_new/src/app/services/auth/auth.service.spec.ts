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

import { AuthData, AuthResponse, AuthService, JwtData } from "./auth.service";
import { AppComponent } from "../../app.component";
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { LocalService } from "../local/local.service";
import { VersioningService } from "../version/version.service";
import { MockLocalService, MockNotificationService, MockVersioningService } from "../../../testing/mock-services";
import { Router } from "@angular/router";
import { NotificationService } from "../notification/notification.service";

const b64url = (obj: any) =>
  Buffer.from(JSON.stringify(obj))
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");

const ensureAtob = () => {
  if (!(global as any).atob) {
    (global as any).atob = (s: string) => Buffer.from(s, "base64").toString("binary");
  }
};

describe("AuthService", () => {
  let authService: AuthService;
  let httpMock: HttpTestingController;
  let mockLocal: MockLocalService;
  let mockVersioning: MockVersioningService;
  let routerMock: { url: string; navigate: jest.Mock };
  let notifications: MockNotificationService;

  beforeEach(() => {
    routerMock = {
      url: "/",
      navigate: jest.fn().mockResolvedValue(true)
    };

    TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: LocalService, useClass: MockLocalService },
        { provide: VersioningService, useClass: MockVersioningService },
        { provide: Router, useValue: routerMock },
        MockNotificationService,
        { provide: NotificationService, useExisting: MockNotificationService }
      ]
    }).compileComponents();

    authService = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
    mockLocal = TestBed.inject(LocalService) as any;
    mockVersioning = TestBed.inject(VersioningService) as any;
    notifications = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    jest.spyOn(console, "error").mockImplementation(() => {});
    ensureAtob();
  });

  afterEach(() => {
    httpMock.verify();
    jest.restoreAllMocks();
  });

  it("should be created", () => {
    expect(authService).toBeTruthy();
  });

  describe("rights if token is not set", () => {
    it("actionAllowed should return false if jwt data is not available", () => {
      expect(authService.actionAllowed("enable")).toBe(false);
    });

    it("actionsAllowed should return false if jwt data is not available", () => {
      expect(authService.actionsAllowed(["enable", "disable"])).toBe(false);
    });

    it("oneActionAllowed should return false if jwt data is not available", () => {
      expect(authService.oneActionAllowed(["enable", "disable"])).toBe(false);
    });

    it("anyContainerActionAllowed should return false if jwt data is not available", () => {
      expect(authService.anyContainerActionAllowed()).toBe(false);
    });

    it("tokenEnrollmentAllowed should return false if jwt data is not available", () => {
      expect(authService.tokenEnrollmentAllowed()).toBe(false);
    });

    it("anyTokenActionAllowed should return false if jwt data is not available", () => {
      expect(authService.anyTokenActionAllowed()).toBe(false);
    });
  });

  describe("check rights", () => {
    let jwtData = {
      username: "alice",
      realm: "defrealm",
      nonce: "fake_nonce",
      role: "user",
      authtype: "password",
      exp: 0,
      rights: ["delete", "enable", "disable"]
    };

    it("actionAllowed should return true if right is set and false otherwise", () => {
      authService.jwtData.set(jwtData as JwtData);
      expect(authService.actionAllowed("enable")).toBe(true);
      expect(authService.actionAllowed("reset")).toBe(false);
    });

    it("actionsAllowed should return true if all rights are set", () => {
      authService.jwtData.set(jwtData as JwtData);
      expect(authService.actionsAllowed(["enable", "disable"])).toBe(true);
    });

    it("actionsAllowed should return false if at least one right is not set", () => {
      authService.jwtData.set(jwtData as JwtData);
      expect(authService.actionsAllowed(["enable", "disable", "reset"])).toBe(false);
    });

    it("oneActionAllowed should return true if at least one right is set", () => {
      authService.jwtData.set(jwtData as JwtData);
      expect(authService.oneActionAllowed(["reset", "disable"])).toBe(true);
    });

    it("oneActionAllowed should return false if none of the rights are set", () => {
      authService.jwtData.set(jwtData as JwtData);
      expect(authService.oneActionAllowed(["assign", "unassign", "reset"])).toBe(false);
    });

    it("anyContainerActionAllowed should return false if no container action is set", () => {
      authService.jwtData.set(jwtData as JwtData);
      expect(authService.anyContainerActionAllowed()).toBe(false);
    });

    it("anyContainerActionAllowed should return true if at least one container right is set", () => {
      jwtData.rights.push("container_create");
      authService.jwtData.set(jwtData as JwtData);
      expect(authService.anyContainerActionAllowed()).toBe(true);
    });

    it("anyTokenActionAllowed should return false if no main token action is set", () => {
      authService.jwtData.set(jwtData as JwtData);
      expect(authService.anyTokenActionAllowed()).toBe(false);
    });

    it("anyTokenActionAllowed should return true if at least one mein token action is set", () => {
      jwtData.rights.push("tokenlist");
      authService.jwtData.set(jwtData as JwtData);
      expect(authService.anyTokenActionAllowed()).toBe(true);
    });

    it("tokenEnrollment should return false if no enrollment right is set", () => {
      authService.jwtData.set(jwtData as JwtData);
      expect(authService.tokenEnrollmentAllowed()).toBe(false);
    });

    it("tokenEnrollment should return true if at least one enrollment right is set", () => {
      jwtData.rights.push("enrollTOTP");
      authService.jwtData.set(jwtData as JwtData);
      expect(authService.tokenEnrollmentAllowed()).toBe(true);
    });
  });

  describe("checkForceServerGenerateOTPKey", () => {
    let jwtData = {
      username: "alice",
      realm: "defrealm",
      nonce: "fake_nonce",
      role: "user",
      authtype: "password",
      exp: 0,
      rights: ["tokenlist"]
    };

    it("checkForceServerGenerateOTPKey should return false if right is not set", () => {
      authService.jwtData.set(jwtData as JwtData);
      expect(authService.checkForceServerGenerateOTPKey("totp")).toBe(false);
      expect(authService.checkForceServerGenerateOTPKey("hotp")).toBe(false);
      expect(authService.checkForceServerGenerateOTPKey("daypassword")).toBe(false);
    });

    it("checkForceServerGenerateOTPKey should return true only for the respective token type", () => {
      jwtData.rights.push("totp_force_server_generate");
      authService.jwtData.set(jwtData as JwtData);
      expect(authService.checkForceServerGenerateOTPKey("totp")).toBe(true);
      expect(authService.checkForceServerGenerateOTPKey("hotp")).toBe(false);
      expect(authService.checkForceServerGenerateOTPKey("daypassword")).toBe(false);
    });
  });

  it("getHeaders returns PI-Authorization from LocalService", () => {
    mockLocal.getData.mockReturnValueOnce("tk-xyz");
    const headers = authService.getHeaders();
    expect(headers.get("PI-Authorization")).toBe("tk-xyz");
    expect(mockLocal.getData).toHaveBeenCalled();
  });

  it("acceptAuthentication + logout lifecycle flips isAuthenticated and clears state", async () => {
    expect(authService.isAuthenticated()).toBe(false);

    authService.acceptAuthentication();
    expect(authService.isAuthenticated()).toBe(false);

    (authService as any).authData.set({
      token: "t",
      realm: "",
      rights: [],
      role: "",
      username: "",
      menus: [],
      log_level: 0,
      logout_time: 0,
      audit_page_size: 10,
      token_page_size: 10,
      user_page_size: 10,
      policy_template_url: "",
      default_tokentype: "",
      default_container_type: "",
      user_details: false,
      token_wizard: false,
      token_wizard_2nd: false,
      admin_dashboard: false,
      dialog_no_token: false,
      search_on_enter: false,
      timeout_action: "",
      token_rollover: {},
      hide_welcome: false,
      hide_buttons: false,
      deletion_confirmation: false,
      show_seed: false,
      show_node: "",
      subscription_status: 0,
      subscription_status_push: 0,
      qr_image_android: null,
      qr_image_ios: null,
      qr_image_custom: null,
      logout_redirect_url: "",
      require_description: [],
      rss_age: 0,
      container_wizard: { enabled: false }
    });
    expect(authService.isAuthenticated()).toBe(true);

    authService.logout();
    expect(authService.isAuthenticated()).toBe(false);
    expect((authService as any).authData()).toBeNull();
    expect((authService as any).jwtData()).toBeNull();
    expect(mockLocal.removeData).toHaveBeenCalled();
    expect(routerMock.navigate).toHaveBeenCalledWith(["login"]);
    await (routerMock.navigate as jest.Mock).mock.results[0].value;
    expect(notifications.openSnackBar).toHaveBeenCalledWith("Logout successful.");
    expect(notifications.openSnackBar).toHaveBeenCalledTimes(1);
  });

  it("authtype, jwtExpDate and logoutTimeSeconds compute correctly", () => {
    jest.useFakeTimers().setSystemTime(new Date("2025-01-01T00:00:00Z"));

    expect(authService.authtype()).toBe("none");
    expect(authService.jwtExpDate()).toBeNull();

    const jwt: JwtData = {
      username: "bob",
      realm: "r",
      nonce: "n",
      role: "admin",
      authtype: "cookie",
      exp: Math.floor(Date.now() / 1000) + 120,
      rights: []
    };
    (authService as any).jwtData.set(jwt);

    expect(authService.authtype()).toBe("cookie");
    expect(authService.jwtExpDate()).toEqual(new Date(jwt.exp * 1000));

    (authService as any).authData.set({ ...(authService as any).authData(), logout_time: 300 } as any);
    expect(authService.logoutTimeSeconds()).toBe(120);

    (authService as any).authData.set({ ...(authService as any).authData(), logout_time: 60 } as any);
    expect(authService.logoutTimeSeconds()).toBe(60);

    jest.useRealTimers();
  });

  it("decodeJwtPayload returns null and logs error for invalid token", () => {
    const res = authService.decodeJwtPayload("nope.invalid.jwt");
    expect(res).toBeNull();
    expect(console.error).toHaveBeenCalled();
  });

  it("authenticate(): saves token, decodes jwt, sets isAuthenticated", () => {
    const payload: JwtData = {
      username: "alice",
      realm: "def",
      nonce: "zz",
      role: "user",
      authtype: "cookie",
      exp: Math.floor(Date.now() / 1000) + 3600,
      rights: ["tokenlist"]
    };
    const jwt = ["hdr", b64url(payload), "sig"].join(".");

    const sub = authService.authenticate({ user: "alice", pass: "x" }).subscribe();

    const req = httpMock.expectOne((r) => r.method === "POST" && r.url.includes("/auth"));
    const body: AuthResponse = {
      id: 0,
      jsonrpc: "2.0",
      signature: "",
      time: Date.now(),
      version: "1.0",
      versionnumber: "3.12.4",
      detail: {},
      result: {
        status: true,
        value: {
          log_level: 0,
          menus: [],
          realm: "def",
          rights: payload.rights,
          role: payload.role,
          token: jwt,
          username: payload.username,
          logout_time: 1800,
          audit_page_size: 10,
          token_page_size: 10,
          user_page_size: 10,
          policy_template_url: "",
          default_tokentype: "hotp",
          default_container_type: "generic",
          user_details: false,
          token_wizard: false,
          token_wizard_2nd: false,
          admin_dashboard: false,
          dialog_no_token: false,
          search_on_enter: false,
          timeout_action: "",
          token_rollover: {},
          hide_welcome: false,
          hide_buttons: false,
          deletion_confirmation: false,
          show_seed: false,
          show_node: "",
          subscription_status: 0,
          subscription_status_push: 0,
          qr_image_android: null,
          qr_image_ios: null,
          qr_image_custom: null,
          logout_redirect_url: "",
          require_description: [],
          rss_age: 0,
          container_wizard: { enabled: false, type: "generic", registration: false, template: null }
        }
      }
    };
    req.flush(body);

    expect(mockLocal.saveData).toHaveBeenCalled();
    expect((authService as any).authData()).not.toBeNull();
    expect((authService as any).jwtData()).toMatchObject(payload);
    expect(authService.isAuthenticated()).toBe(true);

    sub.unsubscribe();
  });

  it("authenticate(): propagates error via catchError", (done) => {
    const sub = authService.authenticate({}).subscribe({
      next: () => fail("expected error"),
      error: (e) => {
        expect(e.status).toBe(401);
        done();
      }
    });
    const req = httpMock.expectOne((r) => r.method === "POST" && r.url.includes("/auth"));
    req.flush({ message: "nope" }, { status: 401, statusText: "unauthorized" });
    sub.unsubscribe();
  });

  it("isSelfServiceUser reflects role === 'user'", () => {
    expect(authService.isSelfServiceUser()).toBe(false);
    (authService as any).jwtData.set({
      username: "u",
      realm: "r",
      nonce: "n",
      role: "user",
      authtype: "cookie",
      exp: 0,
      rights: []
    } as JwtData);
    expect(authService.isSelfServiceUser()).toBe(true);
  });

  it("should extract token types from rollover policy", () => {
    authService.authData.set({token_rollover: {hotp: [], totp: []}} as unknown as AuthData);
    expect(authService.tokenRollover()).toEqual(["hotp", "totp"]);

    // token_rollover data not set
    authService.authData.set({} as unknown as AuthData);
    expect(authService.tokenRollover()).toEqual([]);
  });
});
