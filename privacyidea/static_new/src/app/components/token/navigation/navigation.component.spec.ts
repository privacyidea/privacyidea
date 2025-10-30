import { ComponentFixture, TestBed } from "@angular/core/testing";
import { NavigationComponent } from "./navigation.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ActivatedRoute, provideRouter, Router } from "@angular/router";
import { provideLocationMocks } from "@angular/common/testing";
import { of } from "rxjs";
import { TokenService } from "../../../services/token/token.service";
import { ContainerService } from "../../../services/container/container.service";
import { ChallengesService } from "../../../services/token/challenges/challenges.service";
import { MachineService } from "../../../services/machine/machine.service";
import { UserService } from "../../../services/user/user.service";
import { AuditService } from "../../../services/audit/audit.service";
import { ContentService } from "../../../services/content/content.service";
import { AuthService } from "../../../services/auth/auth.service";
import { SessionTimerService } from "../../../services/session-timer/session-timer.service";
import { NotificationService } from "../../../services/notification/notification.service";
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
import { MatSnackBar } from "@angular/material/snack-bar";

describe("NavigationComponent (async, no RouterTestingModule, no MatSnackBar)", () => {
  let component: NavigationComponent;
  let fixture: ComponentFixture<NavigationComponent>;
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

  afterAll(() => {
    (console.error as jest.Mock)?.mockRestore?.();
  });

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NavigationComponent],
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
      .overrideComponent(NavigationComponent, { set: { template: "" } })
      .compileComponents();


    fixture = TestBed.createComponent(NavigationComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it("covers creation, profileText, logout, and refreshPage branches", async () => {
    expect(component).toBeTruthy();
    expect(component.profileText).toBe("alice @default (admin)");

    const navSpy = jest.spyOn(router, "navigate").mockResolvedValue(true as any);
    component.logout();
    await Promise.resolve();
    expect(navSpy).toHaveBeenCalledWith(["login"]);
    const paths = (component as any).ROUTE_PATHS;

    const tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    const containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
    const challengeService = TestBed.inject(ChallengesService) as unknown as MockChallengesService;
    const machineService = TestBed.inject(MachineService) as unknown as MockMachineService;
    const userService = TestBed.inject(UserService) as unknown as MockUserService;
    const auditService = TestBed.inject(AuditService) as unknown as MockAuditService;
    const content = TestBed.inject(ContentService) as unknown as MockContentService;
    const auth = TestBed.inject(AuthService) as unknown as MockAuthService;

    (auth as any).anyContainerActionAllowed = jest.fn().mockReturnValue(true);
    content.routeUrl.set(`${paths.TOKENS_DETAILS}/123`);
    component.refreshPage();
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
    expect(containerService.containerResource.reload).toHaveBeenCalled();

    jest.clearAllMocks();
    (auth as any).anyContainerActionAllowed = jest.fn().mockReturnValue(false);
    content.routeUrl.set(`${paths.TOKENS_DETAILS}/456`);
    component.refreshPage();
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
    expect(containerService.containerResource.reload).not.toHaveBeenCalled();

    jest.clearAllMocks();
    content.routeUrl.set(`${paths.TOKENS_CONTAINERS_DETAILS}/abc`);
    component.refreshPage();
    expect(containerService.containerDetailResource.reload).toHaveBeenCalled();
    expect(tokenService.tokenResource.reload).toHaveBeenCalled();

    jest.clearAllMocks();
    content.routeUrl.set(paths.TOKENS);
    component.refreshPage();
    expect(tokenService.tokenResource.reload).toHaveBeenCalled();

    jest.clearAllMocks();
    content.routeUrl.set(paths.TOKENS_CONTAINERS);
    component.refreshPage();
    expect(containerService.containerResource.reload).toHaveBeenCalled();

    jest.clearAllMocks();
    content.routeUrl.set(paths.TOKENS_CHALLENGES);
    component.refreshPage();
    expect(challengeService.challengesResource.reload).toHaveBeenCalled();

    jest.clearAllMocks();
    content.routeUrl.set(paths.TOKENS_APPLICATIONS);
    component.refreshPage();
    expect(machineService.tokenApplicationResource.reload).toHaveBeenCalled();

    jest.clearAllMocks();
    content.routeUrl.set(paths.TOKENS_ENROLLMENT);
    component.refreshPage();
    expect(containerService.containerResource.reload).toHaveBeenCalled();
    expect(userService.usersResource.reload).toHaveBeenCalled();

    jest.clearAllMocks();
    content.routeUrl.set(paths.AUDIT);
    component.refreshPage();
    expect(auditService.auditResource.reload).toHaveBeenCalled();

    jest.clearAllMocks();
    content.routeUrl.set(paths.USERS);
    component.refreshPage();
    expect(userService.usersResource.reload).toHaveBeenCalled();

    jest.clearAllMocks();
    content.routeUrl.set(paths.TOKENS_CONTAINERS_DETAILS);
    component.refreshPage();
    expect(userService.usersResource.reload).toHaveBeenCalled();
  });
});
