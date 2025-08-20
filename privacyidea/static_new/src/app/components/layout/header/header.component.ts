import { DatePipe, NgClass, NgOptimizedImage } from "@angular/common";
import { Component, inject } from "@angular/core";
import { MatFabAnchor, MatFabButton, MatIconButton } from "@angular/material/button";

import { MatIconModule } from "@angular/material/icon";
import { Router, RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "../../../app.routes";
import { AuditService, AuditServiceInterface } from "../../../services/audit/audit.service";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import {
  ContainerService,
  ContainerServiceInterface,
} from "../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { LocalService, LocalServiceInterface } from "../../../services/local/local.service";
import { MachineService, MachineServiceInterface } from "../../../services/machine/machine.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import {
  SessionTimerService,
  SessionTimerServiceInterface,
} from "../../../services/session-timer/session-timer.service";
import { ChallengesService, ChallengesServiceInterface } from "../../../services/token/challenges/challenges.service";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";
import { UserService, UserServiceInterface } from "../../../services/user/user.service";
import { ThemeSwitcherComponent } from "../../shared/theme-switcher/theme-switcher.component";

@Component({
  selector: "app-header",
  standalone: true,
  imports: [
    NgOptimizedImage,
    MatFabButton,
    MatFabAnchor,
    MatIconModule,
    RouterLink,
    DatePipe,
    NgClass,
    MatIconButton,
    ThemeSwitcherComponent,
  ],
  templateUrl: "./header.component.html",
  styleUrl: "./header.component.scss",
})
export class HeaderComponent {
  protected readonly sessionTimerService: SessionTimerServiceInterface =
    inject(SessionTimerService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly localService: LocalServiceInterface = inject(LocalService);
  protected readonly notificationService: NotificationServiceInterface =
    inject(NotificationService);
  protected readonly router: Router = inject(Router);
  protected readonly AuthService = AuthService;
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly containerService: ContainerServiceInterface = inject(ContainerService);
  private readonly challengeService: ChallengesServiceInterface = inject(ChallengesService);
  private readonly machineService: MachineServiceInterface = inject(MachineService);
  private readonly userService: UserServiceInterface = inject(UserService);
  private readonly auditService: AuditServiceInterface = inject(AuditService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  profileText =
    this.authService.username() +
    " @" +
    this.authService.realm() +
    " (" +
    this.authService.role() +
    ")";

  isActive(link: string) {
    return this.router.url.includes(link);
  }

  refreshPage() {
    if (this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_DETAILS)) {
      this.tokenService.tokenDetailResource.reload();
      this.containerService.containerResource.reload();
    }
    if (this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS)) {
      this.containerService.containerDetailResource.reload();
      this.tokenService.tokenResource.reload();
    }
    switch (this.contentService.routeUrl()) {
      case ROUTE_PATHS.TOKENS:
        this.tokenService.tokenResource.reload();
        break;
      case ROUTE_PATHS.TOKENS_CONTAINERS:
        this.containerService.containerResource.reload();
        break;
      case ROUTE_PATHS.TOKENS_CHALLENGES:
        this.challengeService.challengesResource.reload();
        break;
      case ROUTE_PATHS.TOKENS_APPLICATIONS:
        this.machineService.tokenApplicationResource.reload();
        break;
      case ROUTE_PATHS.TOKENS_ENROLLMENT:
        this.containerService.containerResource.reload();
        this.userService.usersResource.reload();
        break;
      case ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS:
        this.userService.usersResource.reload();
        break;
      case ROUTE_PATHS.AUDIT:
        this.auditService.auditResource.reload();
        break;
      case ROUTE_PATHS.USERS:
        this.userService.usersResource.reload();
        break;
    }
  }

  logout(): void {
    this.localService.removeData(this.localService.bearerTokenKey);
    this.authService.deauthenticate();
    this.router
      .navigate(["login"])
      .then(() => this.notificationService.openSnackBar("Logout successful."));
  }
}
