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

import { provideHttpClient } from "@angular/common/http";
import { ApplicationService } from "./application.service";
import { MockPiResponse } from "../../../testing/mock-services";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";

describe("ApplicationService", () => {
  let applicationService: ApplicationService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
    applicationService = TestBed.inject(ApplicationService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it("should be created", () => {
    expect(applicationService).toBeTruthy();
  });

  it("should return value from application resource if available", async () => {
    TestBed.tick();
    const req = httpMock.expectOne((req) => req.url.includes(applicationService.applicationBaseUrl));
    const apiApplications = {
      "luks": {
        "options": {
          "totp": {
            "partition": {
              "type": "str"
            },
            "slot": {
              "type": "int",
              "value": [0, 1, 2, 3, 4, 5, 6, 7]
            }
          }
        }
      },
      "offline": {
        "options": {
          "hotp": {
            "count": {
              "type": "str"
            },
            "rounds": {
              "type": "str"
            }
          },
          "passkey": {},
          "webauthn": {}
        }
      },
      "ssh": {
        "options": {
          "sshkey": {
            "service_id": {
              "description": "The service ID of the SSH server. Several servers can have the same service ID.",
              "type": "str",
              "value": [
                "testID"
              ]
            },
            "user": {
              "description": "The username on the SSH server.",
              "type": "str"
            }
          }
        }
      }
    };
    req.flush(MockPiResponse.fromValue(apiApplications));
    await Promise.resolve();

    let applications = applicationService.applications();
    expect(applications).toEqual(apiApplications);
  });

  it("should handle error response from application resource", async () => {
    TestBed.tick();
    const req = httpMock.expectOne((req) => req.url.includes(applicationService.applicationBaseUrl));
    req.flush("Error", { status: 403, statusText: "No permission" });

    const applications = applicationService.applications();
    const defaultApplications = {
      luks: {
        options: {
          totp: { partition: { type: "" }, slot: { type: "", value: [] } }
        }
      },
      offline: {
        options: {
          hotp: { count: { type: "" }, rounds: { type: "" } },
          passkey: {},
          webauthn: {}
        }
      },
      ssh: {
        options: {
          sshkey: {
            service_id: { description: "", type: "", value: [] },
            user: { description: "", type: "" }
          }
        }
      }
    };
    expect(applications).toEqual(defaultApplications);
  });
});
