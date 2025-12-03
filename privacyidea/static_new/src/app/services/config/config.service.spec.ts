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
import { AppConfig, ConfigService } from "./config.service";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { provideHttpClient } from "@angular/common/http";
import { VersioningService, VersioningServiceInterface } from "../version/version.service";

describe("ConfigService", () => {
  let service: ConfigService;
  let httpMock: HttpTestingController;
  let versioningService: VersioningServiceInterface;

  const mockConfig: AppConfig = {
    remote_user: "testUser",
    force_remote_user: "forceUser",
    password_reset: true,
    hsm_ready: true,
    customization: "custom",
    realms: "realm1",
    logo: "logo.png",
    show_node: "node1",
    external_links: true,
    has_job_queue: "true",
    login_text: "Welcome",
    gdpr_link: "http://gdpr",
    translation_warning: true
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        ConfigService,
        VersioningService]
    });
    service = TestBed.inject(ConfigService);
    httpMock = TestBed.inject(HttpTestingController);
    versioningService = TestBed.inject(VersioningService);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should have default config values", () => {
    expect(service.config()).toEqual({
      remote_user: "",
      force_remote_user: "",
      password_reset: false,
      hsm_ready: false,
      customization: "",
      realms: "",
      logo: "",
      show_node: "",
      external_links: false,
      has_job_queue: "false",
      login_text: "",
      gdpr_link: "",
      translation_warning: false
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
    expect(versioningService.getVersion()).toBe("3.8");
  });

  it("should handle error and keep default config", () => {
    service.loadConfig();
    const req = httpMock.expectOne(environment.proxyUrl + "/config");
    req.flush(null, { status: 500, statusText: "Server Error" });

    // Should keep the default config values
    expect(service.config()).toEqual({
      remote_user: "",
      force_remote_user: "",
      password_reset: false,
      hsm_ready: false,
      customization: "",
      realms: "",
      logo: "",
      show_node: "",
      external_links: false,
      has_job_queue: "false",
      login_text: "",
      gdpr_link: "",
      translation_warning: false
    });
  });
});
