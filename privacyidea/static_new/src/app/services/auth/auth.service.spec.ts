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

import { AuthService, JwtData } from "./auth.service";
import { AppComponent } from "../../app.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("AuthService", () => {
  let authService: AuthService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();
    authService = TestBed.inject(AuthService);
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
      username: "alice", realm: "defrealm", nonce: "fake_nonce",
      role: "user", authtype: "password", exp: 0, rights: ["delete", "enable", "disable"]
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
      username: "alice", realm: "defrealm", nonce: "fake_nonce",
      role: "user", authtype: "password", exp: 0, rights: ["tokenlist"]
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
});
