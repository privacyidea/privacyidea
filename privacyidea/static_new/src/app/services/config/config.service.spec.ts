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
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { ConfigService, AppConfig } from "./config.service";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { provideHttpClient } from "@angular/common/http";

describe("ConfigService", () => {
  let service: ConfigService;
  let httpMock: HttpTestingController;

  const mockConfig: AppConfig = {
    remoteUser: "testUser",
    forceRemoteUser: "forceUser",
    passwordReset: true,
    hsmReady: true,
    customization: "custom",
    realms: "realm1",
    logo: "logo.png",
    showNode: "node1",
    externalLinks: true,
    hasJobQueue: "true",
    loginText: "Welcome",
    logoutRedirectUrl: "http://logout",
    gdprLink: "http://gdpr",
    privacyideaVersionNumber: "3.8",
    translationWarning: true,
    otpPinSetRandomUser: 1
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        ConfigService]
    });
    service = TestBed.inject(ConfigService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should have default config values", () => {
    expect(service.config()).toEqual({
      remoteUser: "",
      forceRemoteUser: "",
      passwordReset: false,
      hsmReady: false,
      customization: "",
      realms: "",
      logo: "",
      showNode: "",
      externalLinks: false,
      hasJobQueue: "false",
      loginText: "",
      logoutRedirectUrl: "",
      gdprLink: "",
      privacyideaVersionNumber: "",
      translationWarning: false
    });
  });

  it("should load config from API", () => {
    service.loadConfig();
    const req = httpMock.expectOne(environment.proxyUrl + "/config");
    expect(req.request.method).toBe("GET");

    const mockResponse: PiResponse<Record<any, any>> = {
      id: 1,
      jsonrpc: "2.0",
      detail: {},
      result: { status: true, value: mockConfig },
      signature: "",
      time: Date.now(),
      version: "3.8",
      versionnumber: "3.8"
    };

    req.flush(mockResponse);

    expect(service.config()).toEqual(mockConfig);
  });

  it("should handle error and keep default config", () => {
    service.loadConfig();
    const req = httpMock.expectOne(environment.proxyUrl + "/config");
    req.flush(null, { status: 500, statusText: "Server Error" });

    // Should keep the default config values
    expect(service.config()).toEqual({
      remoteUser: "",
      forceRemoteUser: "",
      passwordReset: false,
      hsmReady: false,
      customization: "",
      realms: "",
      logo: "",
      showNode: "",
      externalLinks: false,
      hasJobQueue: "false",
      loginText: "",
      logoutRedirectUrl: "",
      gdprLink: "",
      privacyideaVersionNumber: "",
      translationWarning: false
    });
  });
});
