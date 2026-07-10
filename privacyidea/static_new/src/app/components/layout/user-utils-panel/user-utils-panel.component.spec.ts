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

import { provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideLocationMocks } from "@angular/common/testing";
import { MatSnackBar } from "@angular/material/snack-bar";
import { ActivatedRoute, provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { CaConnectorService } from "@services/ca-connector/ca-connector.service";
import { ClientsService } from "@services/clients/clients.service";
import { ContainerTemplateService } from "@services/container-template/container-template.service";
import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
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
  MockLocalService,
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
import { MockSubscriptionService } from "@testing/mock-services/mock-subscription-service";
import { of } from "rxjs";
import { UserUtilsPanelComponent } from "./user-utils-panel.component";

describe("UserUtilsPanelComponent", () => {
  let component: UserUtilsPanelComponent;
  let fixture: ComponentFixture<UserUtilsPanelComponent>;
  let tokenService: MockTokenService;
  let containerService: MockContainerService;
  let challengeService: MockChallengesService;
  let machineService: MockMachineService;
  let userService: MockUserService;
  let auditService: MockAuditService;
  let content: MockContentService;
  let authService: MockAuthService;
  let sessionTimerService: MockSessionTimerService;
  let pendingChangesService: MockPendingChangesService;
  let dialogService: MockDialogService;

  beforeAll(async () => {
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
      imports: [UserUtilsPanelComponent],
      providers: [
        provideRouter([]),
        provideLocationMocks(),
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
        { provide: SystemService, useClass: MockSystemService },
        { provide: MatSnackBar, useValue: { open: jest.fn() } },
        provideZonelessChangeDetection(),
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(UserUtilsPanelComponent);
    component = fixture.componentInstance;

    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
    challengeService = TestBed.inject(ChallengesService) as unknown as MockChallengesService;
    machineService = TestBed.inject(MachineService) as unknown as MockMachineService;
    userService = TestBed.inject(UserService) as unknown as MockUserService;
    auditService = TestBed.inject(AuditService) as unknown as MockAuditService;
    content = TestBed.inject(ContentService) as unknown as MockContentService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    sessionTimerService = TestBed.inject(SessionTimerService) as unknown as MockSessionTimerService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("refreshPage per route", () => {
    beforeEach(() => {
      jest.clearAllMocks();
    });

    it("refreshes token details route", () => {
      content.routeUrl.set(`${ROUTE_PATHS.TOKENS_DETAILS}/123`);
      component.refreshPage();
      expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
      expect(containerService.containersForTokenTypeResource.reload).toHaveBeenCalled();
    });

    it("refreshes tokens containers details route", () => {
      content.routeUrl.set(`${ROUTE_PATHS.CONTAINERS_DETAILS}/abc`);
      component.refreshPage();
      expect(containerService.containerDetailsResource.reload).toHaveBeenCalled();
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
    });

    it("refreshes user details route", () => {
      content.routeUrl.set(`${ROUTE_PATHS.USERS_DETAILS}/alice`);
      component.refreshPage();
      expect(userService.usersResource.reload).toHaveBeenCalled();
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
      expect(tokenService.userTokenResource.reload).toHaveBeenCalled();
      expect(containerService.userContainersResource.reload).toHaveBeenCalled();
    });

    it("refreshes dashboard route", () => {
      content.routeUrl.set(ROUTE_PATHS.DASHBOARD);
      const dataStore = TestBed.inject(DashboardDataStore);
      const refreshSpy = jest.spyOn(dataStore, "refreshAll");
      component.refreshPage();
      expect(refreshSpy).toHaveBeenCalled();
    });

    it("refreshes tokens route", () => {
      content.routeUrl.set(ROUTE_PATHS.TOKENS);
      component.refreshPage();
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
    });

    it("refreshes tokens containers route", () => {
      content.routeUrl.set(ROUTE_PATHS.CONTAINERS);
      component.refreshPage();
      expect(containerService.containerResource.reload).toHaveBeenCalled();
    });

    it("refreshes tokens challenges route", () => {
      content.routeUrl.set(ROUTE_PATHS.TOKENS_CHALLENGES);
      component.refreshPage();
      expect(challengeService.challengesResource.reload).toHaveBeenCalled();
    });

    it("refreshes tokens applications route", () => {
      content.routeUrl.set(ROUTE_PATHS.TOKENS_APPLICATIONS);
      component.refreshPage();
      expect(machineService.tokenApplicationResource.reload).toHaveBeenCalled();
    });

    it("refreshes tokens enrollment route", () => {
      content.routeUrl.set(ROUTE_PATHS.TOKENS_ENROLLMENT);
      component.refreshPage();
      expect(containerService.containersForTokenTypeResource.reload).toHaveBeenCalled();
      expect(userService.usersResource.reload).toHaveBeenCalled();
    });

    it("refreshes audit route", () => {
      content.routeUrl.set(ROUTE_PATHS.AUDIT);
      component.refreshPage();
      expect(auditService.auditResource.reload).toHaveBeenCalled();
    });

    it("refreshes users route", () => {
      content.routeUrl.set(ROUTE_PATHS.USERS);
      component.refreshPage();
      expect(userService.usersResource.reload).toHaveBeenCalled();
    });
  });

  describe("profileText", () => {
    it("returns username if realm and role are not available", () => {
      authService.role.set("");
      authService.realm.set("");
      authService.username.set("bob");
      expect(component.profileText()).toBe("bob");
    });
    it("returns username and realm if available", () => {
      authService.role.set("");
      authService.realm.set("default");
      authService.username.set("alice");
      expect(component.profileText()).toBe("alice @ default");
    });
    it("returns username and role for admin without realm", () => {
      authService.role.set("admin");
      authService.realm.set("");
      authService.username.set("alice");
      expect(component.profileText()).toBe("alice (admin)");
    });
    it("returns complete profile text", () => {
      authService.role.set("admin");
      authService.realm.set("defrealm");
      authService.username.set("alice");
      expect(component.profileText()).toBe("alice @ defrealm (admin)");
    });
  });

  describe("sessionTimeFormat signal", () => {
    it("format less than 10 min is 'm:ss'", () => {
      sessionTimerService.remainingTime.set(10 * 60 * 1000 - 1000);
      expect(component.sessionTimeFormat()).toBe("m:ss");
    });
    it("format less than an hour is 'm min'", () => {
      sessionTimerService.remainingTime.set(59 * 60 * 1000);
      expect(component.sessionTimeFormat()).toBe("m'\u202Fmin'");
    });
    it("format for times equal or larger than an hour is 'H h mm min'", () => {
      sessionTimerService.remainingTime.set(60 * 60 * 1000);
      expect(component.sessionTimeFormat()).toBe("H'\u202Fh' mm'\u202Fmin'");
    });
  });

  describe("logout", () => {
    it("calls authService.logout if no pending changes", async () => {
      pendingChangesService.hasChangesMockValue = false;
      component.logout();
      await fixture.whenStable();
      expect(authService.logout).toHaveBeenCalled();
    });

    it("opens SaveAndExitDialog if there are pending changes", async () => {
      pendingChangesService.hasChangesMockValue = true;
      component.logout();
      await fixture.whenStable();
      expect(dialogService.openDialog).toHaveBeenCalled();
      expect(authService.logout).not.toHaveBeenCalled();
    });

    it("calls authService.logout if pending changes are discarded", async () => {
      pendingChangesService.hasChangesMockValue = true;
      const dialogRef = dialogService.openDialog();
      dialogService.openDialog.mockReturnValue(dialogRef);
      jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of("discard"));

      component.logout();
      await fixture.whenStable();

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(authService.logout).toHaveBeenCalled();
    });

    it("calls pendingChangesService.save and logout if save-exit is chosen", async () => {
      pendingChangesService.hasChangesMockValue = true;
      const dialogRef = dialogService.openDialog();
      dialogService.openDialog.mockReturnValue(dialogRef);
      jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of("save-exit"));
      pendingChangesService.save.mockReturnValue(true);

      component.logout();
      await fixture.whenStable();

      expect(pendingChangesService.save).toHaveBeenCalled();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(authService.logout).toHaveBeenCalled();
    });
  });
});
