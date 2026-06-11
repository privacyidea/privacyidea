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

import { NO_ERRORS_SCHEMA } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthData, AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockContentService } from "@testing/mock-services/mock-content-service";
import { TokenEnrolledTextComponent } from "./token-enrolled-text.component";

describe("TokenEnrolledTextComponent", () => {
  let component: TokenEnrolledTextComponent;
  let fixture: ComponentFixture<TokenEnrolledTextComponent>;
  let mockContentService: MockContentService;
  let mockAuthService: MockAuthService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenEnrolledTextComponent],
      providers: [
        { provide: ContentService, useClass: MockContentService },
        { provide: AuthService, useClass: MockAuthService }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();
    fixture = TestBed.createComponent(TokenEnrolledTextComponent);
    component = fixture.componentInstance;
    mockContentService = TestBed.inject(ContentService) as unknown as MockContentService;
    mockContentService.router = { navigateByUrl: jest.fn() } as unknown as Router;
    mockAuthService = TestBed.inject(AuthService) as unknown as MockAuthService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit switchRoute and call contentService.tokenSelected if serial is set", () => {
    const switchRouteSpy = jest.fn();
    fixture.componentRef.setInput("serial", "SERIAL123");
    fixture.detectChanges();
    component.switchRoute.subscribe(switchRouteSpy);
    component.tokenSelected();
    expect(switchRouteSpy).toHaveBeenCalled();
    expect(mockContentService.tokenSelected).toHaveBeenCalledWith("SERIAL123");
  });

  it("should do nothing if serial is not set", () => {
    const switchRouteSpy = jest.fn();
    component.switchRoute.subscribe(switchRouteSpy);
    component.tokenSelected();
    expect(switchRouteSpy).not.toHaveBeenCalled();
    expect(mockContentService.tokenSelected).not.toHaveBeenCalled();
  });

  it("natigateContainerDetails emits switchRoute and calls contentService.navigateContainerDetails if containerSerial is set", () => {
    const switchRouteSpy = jest.fn();
    fixture.componentRef.setInput("containerSerial", "CONT123");
    component.switchRoute.subscribe(switchRouteSpy);
    component.natigateContainerDetails();
    expect(switchRouteSpy).toHaveBeenCalled();
    expect(mockContentService.navigateContainerDetails).toHaveBeenCalledWith("CONT123");
  });

  it("natigateContainerDetails does nothing if containerSerial is not set", () => {
    const switchRouteSpy = jest.fn();
    component.switchRoute.subscribe(switchRouteSpy);
    component.natigateContainerDetails();
    expect(switchRouteSpy).not.toHaveBeenCalled();
    expect(mockContentService.navigateContainerDetails).not.toHaveBeenCalled();
  });

  describe("navigateUserDetails", () => {
    it("emits switchRoute and calls contentService.userSelected when username and userRealm are set", () => {
      fixture.componentRef.setInput("username", "alice");
      fixture.componentRef.setInput("userRealm", "realm1");
      const switchRouteSpy = jest.fn();
      component.switchRoute.subscribe(switchRouteSpy);
      component.navigateUserDetails();
      expect(switchRouteSpy).toHaveBeenCalled();
      expect(mockContentService.userSelected).toHaveBeenCalledWith("alice", "realm1");
    });

    it("does nothing when username is not set", () => {
      fixture.componentRef.setInput("userRealm", "realm1");
      const switchRouteSpy = jest.fn();
      component.switchRoute.subscribe(switchRouteSpy);
      component.navigateUserDetails();
      expect(switchRouteSpy).not.toHaveBeenCalled();
      expect(mockContentService.userSelected).not.toHaveBeenCalled();
    });

    it("does nothing when userRealm is not set", () => {
      fixture.componentRef.setInput("username", "alice");
      const switchRouteSpy = jest.fn();
      component.switchRoute.subscribe(switchRouteSpy);
      component.navigateUserDetails();
      expect(switchRouteSpy).not.toHaveBeenCalled();
      expect(mockContentService.userSelected).not.toHaveBeenCalled();
    });
  });

  describe("navigateRealms", () => {
    it("emits switchRoute and navigates to the realms page", () => {
      const switchRouteSpy = jest.fn();
      component.switchRoute.subscribe(switchRouteSpy);
      component.navigateRealms();
      expect(switchRouteSpy).toHaveBeenCalled();
      expect(mockContentService.router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.USERS_REALMS);
    });
  });

  describe("success message rendering", () => {
    it("renders the enrolled success text with the serial number when rollover is false", () => {
      fixture.componentRef.setInput("serial", "SPASS0001");
      fixture.detectChanges();
      const text = fixture.nativeElement.textContent;
      expect(text).toContain("successfully enrolled");
      expect(text).toContain("SPASS0001");
    });

    it("renders the rollover success text with the serial number when rollover is true", () => {
      fixture.componentRef.setInput("serial", "SPASS0001");
      fixture.componentRef.setInput("rollover", true);
      fixture.detectChanges();
      const text = fixture.nativeElement.textContent;
      expect(text).toContain("successfully rolled over");
      expect(text).toContain("SPASS0001");
    });
  });

  describe("user and realm link rendering", () => {
    beforeEach(() => {
      fixture.componentRef.setInput("username", "alice");
      fixture.componentRef.setInput("userRealm", "realm1");
      fixture.componentRef.setInput("onlyAddToRealm", false);
    });

    it("renders username as links when userlist right is granted", () => {
      mockAuthService.actionAllowed.mockReturnValue(true);
      fixture.detectChanges();
      const links: HTMLAnchorElement[] = Array.from(fixture.nativeElement.querySelectorAll("a"));
      expect(links.some((a) => a.textContent?.trim() === "alice")).toBe(true);
    });

    it("renders realm as links when user is admin", () => {
      mockAuthService.authData.set({ ...mockAuthService.authData(), role: "admin" } as AuthData);
      fixture.detectChanges();
      const links: HTMLAnchorElement[] = Array.from(fixture.nativeElement.querySelectorAll("a"));
      expect(links.some((a) => a.textContent?.trim() === "realm1")).toBe(true);
    });

    it("renders username as plain text when userlist right is not granted", () => {
      mockAuthService.actionAllowed.mockReturnValue(false);
      fixture.detectChanges();
      const links: HTMLAnchorElement[] = Array.from(fixture.nativeElement.querySelectorAll("a"));
      expect(links.some((a) => a.textContent?.trim() === "alice")).toBe(false);
      const spans: HTMLSpanElement[] = Array.from(fixture.nativeElement.querySelectorAll("span"));
      expect(spans.some((s) => s.textContent?.trim() === "alice")).toBe(true);
    });

    it("renders realm as plain text when user has role user", () => {
      mockAuthService.authData.set({ ...mockAuthService.authData(), role: "user" } as AuthData);
      fixture.detectChanges();
      const links: HTMLAnchorElement[] = Array.from(fixture.nativeElement.querySelectorAll("a"));
      expect(links.some((a) => a.textContent?.trim() === "realm1")).toBe(false);
      const spans: HTMLSpanElement[] = Array.from(fixture.nativeElement.querySelectorAll("span"));
      expect(spans.some((s) => s.textContent?.trim() === "realm1")).toBe(true);
    });

    it("renders realm as a link in onlyAddToRealm mode when user is admin", () => {
      fixture.componentRef.setInput("onlyAddToRealm", true);
      mockAuthService.authData.set({ ...mockAuthService.authData(), role: "admin" } as AuthData);
      fixture.detectChanges();
      const links: HTMLAnchorElement[] = Array.from(fixture.nativeElement.querySelectorAll("a"));
      expect(links.some((a) => a.textContent?.trim() === "realm1")).toBe(true);
    });

    it("renders realm as plain text in onlyAddToRealm mode when user has only user role", () => {
      fixture.componentRef.setInput("onlyAddToRealm", true);
      mockAuthService.authData.set({ ...mockAuthService.authData(), role: "user" } as AuthData);
      fixture.detectChanges();
      const links: HTMLAnchorElement[] = Array.from(fixture.nativeElement.querySelectorAll("a"));
      expect(links.some((a) => a.textContent?.trim() === "realm1")).toBe(false);
      const spans: HTMLSpanElement[] = Array.from(fixture.nativeElement.querySelectorAll("span"));
      expect(spans.some((s) => s.textContent?.trim() === "realm1")).toBe(true);
    });
  });
});
