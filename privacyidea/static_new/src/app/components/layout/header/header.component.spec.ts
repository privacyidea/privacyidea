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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ActivatedRoute, Router } from "@angular/router";
import { of } from "rxjs";
import { HeaderComponent } from "./header.component";
import { SessionTimerService } from "../../../services/session-timer/session-timer.service";
import { AuthService } from "../../../services/auth/auth.service";
import { LocalService } from "../../../services/local/local.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { ContentService } from "../../../services/content/content.service";
import { TokenService } from "../../../services/token/token.service";
import { ContainerService } from "../../../services/container/container.service";
import { ChallengesService } from "../../../services/token/challenges/challenges.service";
import { MachineService } from "../../../services/machine/machine.service";
import { UserService } from "../../../services/user/user.service";
import { AuditService } from "../../../services/audit/audit.service";
import {
  MockAuditService,
  MockAuthService,
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

describe("HeaderComponent (with provided mocks)", () => {
  let fixture: ComponentFixture<HeaderComponent>;
  let component: HeaderComponent;

  let routerMock: { url: string; navigate: jest.Mock };
  let auth: MockAuthService;
  let content: MockContentService;
  let tokens: MockTokenService;
  let containers: MockContainerService;
  let challenges: MockChallengesService;
  let machine: MockMachineService;
  let users: MockUserService;
  let audit: MockAuditService;
  let notifications: MockNotificationService;

  beforeAll(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn()
      })
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  beforeEach(async () => {
    routerMock = {
      url: "/",
      navigate: jest.fn().mockResolvedValue(true)
    };

    await TestBed.configureTestingModule({
      imports: [HeaderComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: routerMock },

        MockLocalService,
        MockNotificationService,

        { provide: LocalService, useExisting: MockLocalService },
        { provide: NotificationService, useExisting: MockNotificationService },
        { provide: SessionTimerService, useClass: MockSessionTimerService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ChallengesService, useClass: MockChallengesService },
        { provide: MachineService, useClass: MockMachineService },
        { provide: UserService, useClass: MockUserService },
        { provide: AuditService, useClass: MockAuditService },

        { provide: ActivatedRoute, useValue: { params: of({ id: "123" }) } }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(HeaderComponent);
    component = fixture.componentInstance;

    auth = TestBed.inject(AuthService) as unknown as MockAuthService;
    content = TestBed.inject(ContentService) as unknown as MockContentService;
    tokens = TestBed.inject(TokenService) as unknown as MockTokenService;
    containers = TestBed.inject(ContainerService) as unknown as MockContainerService;
    challenges = TestBed.inject(ChallengesService) as unknown as MockChallengesService;
    machine = TestBed.inject(MachineService) as unknown as MockMachineService;
    users = TestBed.inject(UserService) as unknown as MockUserService;
    audit = TestBed.inject(AuditService) as unknown as MockAuditService;
    notifications = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    if (!(auth as any).anyContainerActionAllowed) {
      (auth as any).anyContainerActionAllowed = jest.fn().mockReturnValue(true);
    }
    if (!(auth as any).logout) {
      (auth as any).logout = jest.fn();
    }

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("builds profileText from AuthService signals", () => {
    expect(component.profileText).toBe("alice @default (admin)");
  });

  it("isActive() returns true when router.url contains link; false otherwise", () => {
    routerMock.url = "/tokens/123";
    expect(component.isActive("tokens")).toBe(true);
    expect(component.isActive("/users")).toBe(false);
  });

  describe("refreshPage()", () => {
    const setRouteUrl = (url: string) => {
      (content as any).routeUrl.set(url);
    };

    it("startsWith TOKENS_DETAILS → reloads tokenDetail and containerResource when allowed", () => {
      const { TOKENS_DETAILS } = (component as any).ROUTE_PATHS;
      (content as any).routeUrl.set(`${TOKENS_DETAILS}/ABC`);

      jest.spyOn(auth as any, "anyContainerActionAllowed").mockReturnValue(true);

      component.refreshPage();

      expect(tokens.tokenDetailResource.reload).toHaveBeenCalledTimes(1);
      expect(containers.containerResource.reload).toHaveBeenCalledTimes(1);
    });

    it("startsWith TOKENS_DETAILS but no container permission → skips containerResource", () => {
      const { TOKENS_DETAILS } = (component as any).ROUTE_PATHS;
      (content as any).routeUrl.set(`${TOKENS_DETAILS}/XYZ`);

      jest.spyOn(auth as any, "anyContainerActionAllowed").mockReturnValue(false);

      component.refreshPage();

      expect(tokens.tokenDetailResource.reload).toHaveBeenCalledTimes(1);
      expect(containers.containerResource.reload).not.toHaveBeenCalled();
    });

    it("startsWith TOKENS_CONTAINERS_DETAILS → reload containerDetail + tokenResource", () => {
      const { TOKENS_CONTAINERS_DETAILS } = (component as any).ROUTE_PATHS;
      setRouteUrl(`${TOKENS_CONTAINERS_DETAILS}/42`);

      component.refreshPage();

      expect(containers.containerDetailResource.reload).toHaveBeenCalledTimes(1);
      expect(tokens.tokenResource.reload).toHaveBeenCalledTimes(1);
    });

    it("route == TOKENS → reload tokenResource", () => {
      const { TOKENS } = (component as any).ROUTE_PATHS;
      setRouteUrl(TOKENS);

      component.refreshPage();

      expect(tokens.tokenResource.reload).toHaveBeenCalledTimes(1);
    });

    it("route == TOKENS_CONTAINERS → reload containerResource", () => {
      const { TOKENS_CONTAINERS } = (component as any).ROUTE_PATHS;
      setRouteUrl(TOKENS_CONTAINERS);

      component.refreshPage();

      expect(containers.containerResource.reload).toHaveBeenCalledTimes(1);
    });

    it("route == TOKENS_CHALLENGES → reload challengesResource", () => {
      const { TOKENS_CHALLENGES } = (component as any).ROUTE_PATHS;
      setRouteUrl(TOKENS_CHALLENGES);

      component.refreshPage();

      expect(challenges.challengesResource.reload).toHaveBeenCalledTimes(1);
    });

    it("route == TOKENS_APPLICATIONS → reload tokenApplicationResource", () => {
      const { TOKENS_APPLICATIONS } = (component as any).ROUTE_PATHS;
      setRouteUrl(TOKENS_APPLICATIONS);

      component.refreshPage();

      expect(machine.tokenApplicationResource.reload).toHaveBeenCalledTimes(1);
    });

    it("route == TOKENS_ENROLLMENT → reload containerResource + usersResource", () => {
      const { TOKENS_ENROLLMENT } = (component as any).ROUTE_PATHS;
      setRouteUrl(TOKENS_ENROLLMENT);

      component.refreshPage();

      expect(containers.containerResource.reload).toHaveBeenCalledTimes(1);
      expect(users.usersResource.reload).toHaveBeenCalledTimes(1);
    });

    it("route == AUDIT → reload auditResource", () => {
      const { AUDIT } = (component as any).ROUTE_PATHS;
      setRouteUrl(AUDIT);

      component.refreshPage();

      expect(audit.auditResource.reload).toHaveBeenCalledTimes(1);
    });

    it("route == USERS → reload usersResource", () => {
      const { USERS } = (component as any).ROUTE_PATHS;
      setRouteUrl(USERS);

      component.refreshPage();

      expect(users.usersResource.reload).toHaveBeenCalledTimes(1);
    });

    it("route == TOKENS_CONTAINERS_DETAILS (exact) → triggers both startsWith-block and switch-case", () => {
      const { TOKENS_CONTAINERS_DETAILS } = (component as any).ROUTE_PATHS;
      setRouteUrl(TOKENS_CONTAINERS_DETAILS);

      component.refreshPage();

      expect(containers.containerDetailResource.reload).toHaveBeenCalledTimes(1);
      expect(tokens.tokenResource.reload).toHaveBeenCalledTimes(1);
      expect(users.usersResource.reload).toHaveBeenCalledTimes(1);
    });
  });

  describe("logout()", () => {
    it("calls auth.logout, navigates to login, then shows a snackbar", async () => {
      (auth as any).logout = jest.fn();

      component.logout();

      expect((auth as any).logout).toHaveBeenCalledTimes(1);
      expect(routerMock.navigate).toHaveBeenCalledWith(["login"]);

      await (routerMock.navigate as jest.Mock).mock.results[0].value;

      expect(notifications.openSnackBar).toHaveBeenCalledWith("Logout successful.");
      expect(notifications.openSnackBar).toHaveBeenCalledTimes(1);
    });
  });
});
