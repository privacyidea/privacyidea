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

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { ActivatedRoute } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { NavigationSelfServiceButtonComponent } from "@components/layout/navigation-self-service/navigation-self-service-button/navigation-self-service-button.component";
import { NavigationSelfServiceComponent } from "@components/layout/navigation-self-service/navigation-self-service.component";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { UserService } from "@services/user/user.service";
import { MockContentService, MockUserService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { of } from "rxjs";

describe("NavigationSelfServiceComponent", () => {
  let component: NavigationSelfServiceComponent;
  let fixture: ComponentFixture<NavigationSelfServiceComponent>;
  let authServiceMock: MockAuthService;
  let userServiceMock: MockUserService;
  let contentServiceMock: MockContentService;

  beforeAll(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (q: string) => ({
        matches: false,
        media: q,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn()
      })
    });
  });

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NavigationSelfServiceComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { params: of({ id: "123" }) } },
        { provide: AuthService, useClass: MockAuthService },
        { provide: UserService, useClass: MockUserService },
        { provide: ContentService, useClass: MockContentService }
      ]
    }).compileComponents();

    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    userServiceMock = TestBed.inject(UserService) as unknown as MockUserService;
    contentServiceMock = TestBed.inject(ContentService) as unknown as MockContentService;

    (authServiceMock.actionAllowed as jest.Mock).mockReturnValue(true);

    fixture = TestBed.createComponent(NavigationSelfServiceComponent);
    component = fixture.componentInstance;
  });

  afterEach(() => jest.clearAllMocks());

  it("should create", () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it("exposes ROUTE_PATHS and the user signal from UserService", () => {
    expect((component as any).ROUTE_PATHS).toBe(ROUTE_PATHS);
    expect(component.userData).toBe(userServiceMock.user);
  });

  it("renders the username button as a routerLink anchor when not on user-details route", () => {
    userServiceMock.user.set({ ...userServiceMock.user(), username: "alice" });
    userServiceMock.selectedUserRealm.set("realm1");
    contentServiceMock.routeUrl.set("/tokens");

    fixture.detectChanges();

    const anchor = fixture.nativeElement.querySelector("a.username-button");
    const disabled = fixture.nativeElement.querySelector("div.username-button.disabled");
    expect(anchor).toBeTruthy();
    expect(disabled).toBeNull();
    expect(anchor.getAttribute("href")).toBe(ROUTE_PATHS.USERS_DETAILS);
    expect(anchor.textContent).toContain("alice");
    expect(anchor.textContent).toContain("realm1");
  });

  it("renders a disabled username div (no anchor) when on user-details self-service route", () => {
    userServiceMock.user.set({ ...userServiceMock.user(), username: "alice" });
    userServiceMock.selectedUserRealm.set("realm1");
    contentServiceMock.routeUrl.set(ROUTE_PATHS.USERS_DETAILS);

    fixture.detectChanges();

    const anchor = fixture.nativeElement.querySelector("a.username-button");
    const disabled = fixture.nativeElement.querySelector("div.username-button.disabled");
    expect(anchor).toBeNull();
    expect(disabled).toBeTruthy();
    expect(disabled.textContent).toContain("alice");
    expect(disabled.textContent).toContain("realm1");
  });

  it("falls back to '-' when username or realm are empty", () => {
    userServiceMock.user.set({ ...userServiceMock.user(), username: "" });
    userServiceMock.selectedUserRealm.set("");
    contentServiceMock.routeUrl.set("/tokens");

    fixture.detectChanges();

    const anchor = fixture.nativeElement.querySelector("a.username-button");
    expect(anchor.textContent).toContain("-");
  });

  it("renders the username block as disabled (no anchor) when 'userlist' is not allowed", () => {
    (authServiceMock.actionAllowed as jest.Mock).mockImplementation((action) => action !== "userlist");
    contentServiceMock.routeUrl.set("/tokens");

    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("a.username-button")).toBeNull();
    expect(fixture.nativeElement.querySelector("div.username-button.disabled")).toBeTruthy();
  });

  it("hides navigation buttons when token wizard is active", () => {
    authServiceMock.authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      token_wizard: true
    });

    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("app-navigation-self-service-button")).toBeNull();
  });

  it("hides navigation buttons when container wizard is enabled", () => {
    authServiceMock.authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      container_wizard: { enabled: true, type: "", registration: false, template: null }
    });

    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("app-navigation-self-service-button")).toBeNull();
  });

  it("renders standard nav buttons by default", () => {
    fixture.detectChanges();

    const buttons = fixture.nativeElement.querySelectorAll("app-navigation-self-service-button");
    expect(buttons.length).toBeGreaterThan(0);
  });

  it("renders the assign-token button only when 'assign' right is present", () => {
    authServiceMock.authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: ["assign"]
    });
    fixture.detectChanges();

    const keys = fixture.debugElement
      .queryAll(By.directive(NavigationSelfServiceButtonComponent))
      .map((d) => (d.componentInstance as NavigationSelfServiceButtonComponent).key);
    expect(keys).toContain(ROUTE_PATHS.TOKENS_ASSIGN_TOKEN);
  });

  it("does NOT render the assign-token button when 'assign' right is missing", () => {
    authServiceMock.authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: []
    });
    fixture.detectChanges();

    const keys = fixture.debugElement
      .queryAll(By.directive(NavigationSelfServiceButtonComponent))
      .map((d) => (d.componentInstance as NavigationSelfServiceButtonComponent).key);
    expect(keys).not.toContain(ROUTE_PATHS.TOKENS_ASSIGN_TOKEN);
  });

  it("renders audit log button only when 'auditlog' right is present", () => {
    authServiceMock.authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: ["auditlog"]
    });
    fixture.detectChanges();

    const keys = fixture.debugElement
      .queryAll(By.directive(NavigationSelfServiceButtonComponent))
      .map((d) => (d.componentInstance as NavigationSelfServiceButtonComponent).key);
    expect(keys).toContain(ROUTE_PATHS.AUDIT);
  });

  it("renders container overview only when 'container_list' right is present", () => {
    authServiceMock.authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: ["container_list"]
    });
    fixture.detectChanges();

    const keys = fixture.debugElement
      .queryAll(By.directive(NavigationSelfServiceButtonComponent))
      .map((d) => (d.componentInstance as NavigationSelfServiceButtonComponent).key);
    expect(keys).toContain(ROUTE_PATHS.TOKENS_CONTAINERS);
  });
});
