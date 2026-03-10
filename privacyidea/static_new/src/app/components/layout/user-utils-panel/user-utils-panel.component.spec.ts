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

import { UserUtilsPanelComponent } from "./user-utils-panel.component";
import { ActivatedRoute, provideRouter, Router } from "@angular/router";
import { provideLocationMocks } from "@angular/common/testing";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { of } from "rxjs";
import { TokenService } from "../../../services/token/token.service";
import {
  MockAuditService,
  MockChallengesService,
  MockContainerService,
  MockContentService,
  MockLocalService,
  MockMachineService,
  MockNotificationService,
  MockSessionTimerService,
  MockTokenService,
  MockUserService
} from "../../../../testing/mock-services";
import { ContainerService } from "../../../services/container/container.service";
import { ChallengesService } from "../../../services/token/challenges/challenges.service";
import { MachineService } from "../../../services/machine/machine.service";
import { UserService } from "../../../services/user/user.service";
import { AuditService } from "../../../services/audit/audit.service";
import { ContentService } from "../../../services/content/content.service";
import { AuthService } from "../../../services/auth/auth.service";
import { MockAuthService } from "../../../../testing/mock-services/mock-auth-service";
import { SessionTimerService } from "../../../services/session-timer/session-timer.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { MatSnackBar } from "@angular/material/snack-bar";
import { ROUTE_PATHS } from "../../../route_paths";

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
  let notificationService: MockNotificationService;
  let router: Router;

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
        { provide: AuditService, useClass: MockAuditService },
        { provide: ContentService, useClass: MockContentService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: SessionTimerService, useClass: MockSessionTimerService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: MatSnackBar, useValue: { open: jest.fn() } },
        MockLocalService,
        MockNotificationService
      ]
    })
      .compileComponents();

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
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    router = TestBed.inject(Router);

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
      expect(containerService.containerResource.reload).toHaveBeenCalled();
    });

    it("refreshes tokens containers details route", () => {
      content.routeUrl.set(`${ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS}/abc`);
      component.refreshPage();
      expect(containerService.containerDetailResource.reload).toHaveBeenCalled();
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
    });

    it("refreshes tokens route", () => {
      content.routeUrl.set(ROUTE_PATHS.TOKENS);
      component.refreshPage();
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
    });

    it("refreshes tokens containers route", () => {
      content.routeUrl.set(ROUTE_PATHS.TOKENS_CONTAINERS);
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
      expect(containerService.containerResource.reload).toHaveBeenCalled();
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
    it("calls authService.logout", async () => {
      await component.logout();
      expect(authService.logout).toHaveBeenCalled();
    });
  });
});
