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
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { RemoteServer } from "@services/privacyidea-server/privacyidea-server.service";
import { EnrollRemoteComponent } from "./enroll-remote.component";
import { PrivacyideaServerService } from "@services/privacyidea-server/privacyidea-server.service";
import { MockPrivacyideaServerService, MockTokenService} from "@testing/mock-services";
import { TokenService } from "@services/token/token.service";

describe("EnrollRemoteComponent", () => {
  let component: EnrollRemoteComponent;
  let fixture: ComponentFixture<EnrollRemoteComponent>;

  const basicOptions: TokenEnrollmentData = {
    type: "remote"
  } as any;

  const mockRemoteServer: RemoteServer = {
    identifier: "remote-1",
    name: "remote-1",
    url: "https://test.example"
  } as any;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollRemoteComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(),
        { provide: PrivacyideaServerService, useClass: MockPrivacyideaServerService },
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollRemoteComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("ngOnInit with enrollmentData input", () => {
    it("should set initial values from enrollmentData", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "remote",
        checkPinLocally: true,
        remoteServer: mockRemoteServer,
        remoteSerial: "S1",
        remoteUser: "u",
        remoteRealm: "r",
        remoteResolver: "res"
      });
      component.ngOnInit();
      expect(component.checkPinLocally()).toBe(true);
      expect(component.remoteServer()).toEqual(mockRemoteServer);
      expect(component.remoteSerial()).toBe("S1");
      expect(component.remoteUser()).toBe("u");
      expect(component.remoteRealm()).toBe("r");
      expect(component.remoteResolver()).toBe("res");
    });

    it("should default fields when enrollmentData fields are missing", () => {
      fixture.componentRef.setInput("enrollmentData", { type: "remote" });
      component.ngOnInit();
      expect(component.checkPinLocally()).toBe(false);
      expect(component.remoteServer()).toBeNull();
      expect(component.remoteSerial()).toBe("");
      expect(component.remoteUser()).toBe("");
      expect(component.remoteRealm()).toBe("");
      expect(component.remoteResolver()).toBe("");
    });
  });

  describe("buildEnrollmentArgs", () => {
    it("should return null when no remoteServer is selected", () => {
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).toBeNull();
    });

    it("should return null and mark fields touched when required fields are empty", () => {
      component.remoteServer.set(mockRemoteServer);
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).toBeNull();
      expect(component.remoteSerialForm().touched()).toBe(true);
      expect(component.remoteUserForm().touched()).toBe(true);
      expect(component.remoteResolverForm().touched()).toBe(true);
    });

    it("should build enrollment data when all required fields are filled", () => {
      component.remoteServer.set(mockRemoteServer);
      component.remoteSerial.set("S1");
      component.remoteUser.set("alice");
      component.remoteResolver.set("res1");
      component.remoteRealm.set("realm1");
      component.checkPinLocally.set(true);

      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).not.toBeNull();
      expect(result!.data.type).toBe("remote");
      expect(result!.data.remoteServer).toEqual(mockRemoteServer);
      expect(result!.data.remoteSerial).toBe("S1");
      expect(result!.data.remoteUser).toBe("alice");
      expect(result!.data.remoteResolver).toBe("res1");
      expect(result!.data.remoteRealm).toBe("realm1");
      expect(result!.data.checkPinLocally).toBe(true);
    });
  });
});
