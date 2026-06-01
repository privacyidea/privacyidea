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
import { ActivatedRoute, provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { NavigationSelfServiceButtonComponent } from "@components/layout/navigation-self-service/navigation-self-service-button/navigation-self-service-button.component";
import { NavigationSelfServiceComponent } from "@components/layout/navigation-self-service/navigation-self-service.component";
import { AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { CaConnectorService } from "@services/ca-connector/ca-connector.service";
import { ClientsService } from "@services/clients/clients.service";
import { ContainerTemplateService } from "@services/container-template/container-template.service";
import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { DocumentationService } from "@services/documentation/documentation.service";
import { EventService } from "@services/event/event.service";
import { MachineResolverService } from "@services/machine-resolver/machine-resolver.service";
import { MachineService } from "@services/machine/machine.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { PeriodicTaskService } from "@services/periodic-task/periodic-task.service";
import { PolicyService } from "@services/policies/policies.service";
import { PrivacyideaServerService } from "@services/privacyidea-server/privacyidea-server.service";
import { RadiusServerService } from "@services/radius-server/radius-server.service";
import { RealmService } from "@services/realm/realm.service";
import { ResolverService } from "@services/resolver/resolver.service";
import { ServiceIdService } from "@services/service-id/service-id.service";
import { SessionTimerService } from "@services/session-timer/session-timer.service";
import { SmsGatewayService } from "@services/sms-gateway/sms-gateway.service";
import { SmtpService } from "@services/smtp/smtp.service";
import { SubscriptionService } from "@services/subscription/subscription.service";
import { SystemService } from "@services/system/system.service";
import { ChallengesService } from "@services/token/challenges/challenges.service";
import { TokenService } from "@services/token/token.service";
import { TokengroupService } from "@services/tokengroup/tokengroup.service";
import { UserService } from "@services/user/user.service";
import { VersioningService } from "@services/version/version.service";
import {
  MockAuditService,
  MockCaConnectorService,
  MockChallengesService,
  MockClientsService,
  MockContainerService,
  MockContainerTemplateService,
  MockContentService,
  MockDialogService,
  MockDocumentationService,
  MockMachineResolverService,
  MockMachineService,
  MockNotificationService,
  MockPendingChangesService,
  MockPeriodicTaskService,
  MockPolicyService,
  MockPrivacyideaServerService,
  MockRadiusService,
  MockRealmService,
  MockServiceIdService,
  MockSessionTimerService,
  MockSmsGatewayService,
  MockSmtpService,
  MockSystemService,
  MockTokenService,
  MockTokengroupService,
  MockUserService,
  MockVersioningService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockEventService } from "@testing/mock-services/mock-event-service";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { MockSubscriptionService } from "@testing/mock-services/mock-subscription-serivce";
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
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { params: of({ id: "123" }) } },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ChallengesService, useClass: MockChallengesService },
        { provide: MachineService, useClass: MockMachineService },
        { provide: UserService, useClass: MockUserService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: VersioningService, useClass: MockVersioningService },
        { provide: DocumentationService, useClass: MockDocumentationService },
        { provide: AuditService, useClass: MockAuditService },
        { provide: ClientsService, useClass: MockClientsService },
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: SubscriptionService, useClass: MockSubscriptionService },
        { provide: MachineResolverService, useClass: MockMachineResolverService },
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService },
        { provide: ContentService, useClass: MockContentService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: SessionTimerService, useClass: MockSessionTimerService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: ResolverService, useClass: MockResolverService },
        { provide: SmtpService, useClass: MockSmtpService },
        { provide: RadiusServerService, useClass: MockRadiusService },
        { provide: SmsGatewayService, useClass: MockSmsGatewayService },
        { provide: PrivacyideaServerService, useClass: MockPrivacyideaServerService },
        { provide: TokengroupService, useClass: MockTokengroupService },
        { provide: CaConnectorService, useClass: MockCaConnectorService },
        { provide: ServiceIdService, useClass: MockServiceIdService },
        { provide: PeriodicTaskService, useClass: MockPeriodicTaskService },
        { provide: EventService, useClass: MockEventService },
        { provide: SystemService, useClass: MockSystemService }
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
      .map((d) => (d.componentInstance as NavigationSelfServiceButtonComponent).key());
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
      .map((d) => (d.componentInstance as NavigationSelfServiceButtonComponent).key());
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
      .map((d) => (d.componentInstance as NavigationSelfServiceButtonComponent).key());
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
      .map((d) => (d.componentInstance as NavigationSelfServiceButtonComponent).key());
    expect(keys).toContain(ROUTE_PATHS.CONTAINERS);
  });
});
