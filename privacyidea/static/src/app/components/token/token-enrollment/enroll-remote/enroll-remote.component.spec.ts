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
import { MatSelect } from "@angular/material/select";
import { MatTooltip } from "@angular/material/tooltip";
import { By } from "@angular/platform-browser";
import { EnrollRemoteComponent } from "./enroll-remote.component";
import { PrivacyideaServer, PrivacyideaServerService } from "@services/privacyidea-server/privacyidea-server.service";
import { MockPrivacyideaServerService, MockTokenService } from "@testing/mock-services";
import { TokenService } from "@services/token/token.service";

describe("EnrollRemoteComponent", () => {
  let component: EnrollRemoteComponent;
  let fixture: ComponentFixture<EnrollRemoteComponent>;
  let privacyideaServerService: MockPrivacyideaServerService;

  const basicOptions: TokenEnrollmentData = {
    type: "remote"
  } as TokenEnrollmentData;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollRemoteComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PrivacyideaServerService, useClass: MockPrivacyideaServerService },
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();

    privacyideaServerService = TestBed.inject(PrivacyideaServerService) as unknown as MockPrivacyideaServerService;
    fixture = TestBed.createComponent(EnrollRemoteComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should offer the configured servers in a select when the servers can be listed", () => {
    privacyideaServerService.remoteServerOptions.set([
      { id: "1", identifier: "pi-a", name: "pi-a" } as PrivacyideaServer,
      { id: "2", identifier: "pi-b", name: "pi-b" } as PrivacyideaServer
    ]);
    fixture.detectChanges();

    const select: MatSelect = fixture.debugElement.query(By.directive(MatSelect)).componentInstance;
    expect(select.options.map((option) => option.value)).toEqual(["1", "2"]);
    expect(select.options.map((option) => option.viewValue)).toEqual(["pi-a", "pi-b"]);
  });

  describe("when the servers cannot be listed", () => {
    beforeEach(() => {
      privacyideaServerService.canListRemoteServers.set(false);
      fixture.detectChanges();
    });

    it("should disable the server select and name the missing right in its tooltip", () => {
      const select: MatSelect = fixture.debugElement.query(By.directive(MatSelect)).componentInstance;
      expect(select.disabled).toBe(true);

      const tooltip: MatTooltip = fixture.debugElement.query(By.directive(MatTooltip)).injector.get(MatTooltip);
      expect(tooltip.disabled).toBe(false);
      expect(tooltip.message).toContain("privacyideaserver_read");
    });

    it("should report the enrollment as blocked, naming the missing right", () => {
      expect(component.enrollmentBlockedReason()).toContain("privacyideaserver_read");
    });

    it("should not block the enrollment when enrollmentData already names the server", () => {
      fixture.componentRef.setInput("enrollmentData", { type: "remote", remoteServerId: "2" });
      component.ngOnInit();

      expect(component.enrollmentBlockedReason()).toBeNull();
    });

    it("should not build enrollment data without a server", () => {
      component.remoteSerial.set("S1");
      component.remoteUser.set("alice");
      component.remoteResolver.set("res1");

      expect(component.buildEnrollmentArgs(basicOptions)).toBeNull();
    });
  });

  it("should not block the enrollment when the servers can be listed", () => {
    expect(component.enrollmentBlockedReason()).toBeNull();

    const select: MatSelect = fixture.debugElement.query(By.directive(MatSelect)).componentInstance;
    expect(select.disabled).toBe(false);
  });

  it("should show the required error for an empty server on enrollment", () => {
    component.remoteSerial.set("S1");
    component.remoteUser.set("alice");
    component.remoteResolver.set("res1");

    expect(component.buildEnrollmentArgs(basicOptions)).toBeNull();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("Remote Server is required");
  });

  describe("ngOnInit with enrollmentData input", () => {
    it("should set initial values from enrollmentData", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "remote",
        checkPinLocally: true,
        remoteServerId: "remote-1",
        remoteSerial: "S1",
        remoteUser: "u",
        remoteRealm: "r",
        remoteResolver: "res"
      });
      component.ngOnInit();
      expect(component.checkPinLocally()).toBe(true);
      expect(component.remoteServerId()).toBe("remote-1");
      expect(component.remoteSerial()).toBe("S1");
      expect(component.remoteUser()).toBe("u");
      expect(component.remoteRealm()).toBe("r");
      expect(component.remoteResolver()).toBe("res");
    });

    it("should default fields when enrollmentData fields are missing", () => {
      fixture.componentRef.setInput("enrollmentData", { type: "remote" });
      component.ngOnInit();
      expect(component.checkPinLocally()).toBe(false);
      expect(component.remoteServerId()).toBe("");
      expect(component.remoteSerial()).toBe("");
      expect(component.remoteUser()).toBe("");
      expect(component.remoteRealm()).toBe("");
      expect(component.remoteResolver()).toBe("");
    });
  });

  describe("buildEnrollmentArgs", () => {
    it("should return null and mark the server touched when no server is selected", () => {
      component.remoteSerial.set("S1");
      component.remoteUser.set("alice");
      component.remoteResolver.set("res1");

      expect(component.buildEnrollmentArgs(basicOptions)).toBeNull();
      expect(component.remoteServerIdForm().touched()).toBe(true);
    });

    it("should return null and mark fields touched when required fields are empty", () => {
      component.remoteServerId.set("remote-1");
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).toBeNull();
      expect(component.remoteSerialForm().touched()).toBe(true);
      expect(component.remoteUserForm().touched()).toBe(true);
      expect(component.remoteResolverForm().touched()).toBe(true);
    });

    it("should build enrollment data when all required fields are filled", () => {
      component.remoteServerId.set("remote-1");
      component.remoteSerial.set("S1");
      component.remoteUser.set("alice");
      component.remoteResolver.set("res1");
      component.remoteRealm.set("realm1");
      component.checkPinLocally.set(true);

      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).not.toBeNull();
      expect(result!.data.type).toBe("remote");
      expect(result!.data.remoteServerId).toBe("remote-1");
      expect(result!.data.remoteSerial).toBe("S1");
      expect(result!.data.remoteUser).toBe("alice");
      expect(result!.data.remoteResolver).toBe("res1");
      expect(result!.data.remoteRealm).toBe("realm1");
      expect(result!.data.checkPinLocally).toBe(true);
    });
  });
});
