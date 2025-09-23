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
import { CommonModule, NgOptimizedImage } from "@angular/common";
import { Component, effect, inject, signal, ViewChild } from "@angular/core";
import { MatButton, MatFabAnchor, MatFabButton, MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatDrawer, MatDrawerContainer, MatSidenavModule } from "@angular/material/sidenav";
import { Router, RouterLink, RouterOutlet } from "@angular/router";
import { ContentService, ContentServiceInterface } from "../../services/content/content.service";
import { OverflowService, OverflowServiceInterface } from "../../services/overflow/overflow.service";
import { ContainerDetailsComponent } from "./container-details/container-details.component";
import { ContainerTableComponent } from "./container-table/container-table.component";
import { TokenDetailsComponent } from "./token-details/token-details.component";
import { TokenTableComponent } from "./token-table/token-table.component";
import { MatList, MatListItem } from "@angular/material/list";
import { ROUTE_PATHS } from "../../route_paths";
import { MatAccordion, MatExpansionModule } from "@angular/material/expansion";
import { AuthService, AuthServiceInterface } from "../../services/auth/auth.service";
import { VersioningService, VersioningServiceInterface } from "../../services/version/version.service";
import { ThemeSwitcherComponent } from "../shared/theme-switcher/theme-switcher.component";
import { TokenService, TokenServiceInterface } from "../../services/token/token.service";
import { ContainerService, ContainerServiceInterface } from "../../services/container/container.service";
import { SessionTimerService, SessionTimerServiceInterface } from "../../services/session-timer/session-timer.service";
import { LocalService, LocalServiceInterface } from "../../services/local/local.service";
import { NotificationService, NotificationServiceInterface } from "../../services/notification/notification.service";
import { ChallengesService, ChallengesServiceInterface } from "../../services/token/challenges/challenges.service";
import { MachineService, MachineServiceInterface } from "../../services/machine/machine.service";
import { UserService, UserServiceInterface } from "../../services/user/user.service";
import { AuditService, AuditServiceInterface } from "../../services/audit/audit.service";
import { MatFormField, MatInput, MatLabel, MatSuffix } from "@angular/material/input";
import { MatDividerModule } from "@angular/material/divider";

export type TokenTypeOption =
  | "hotp"
  | "totp"
  | "spass"
  | "motp"
  | "sshkey"
  | "yubikey"
  | "remote"
  | "yubico"
  | "radius"
  | "sms"
  | "4eyes"
  | "applspec"
  | "certificate"
  | "daypassword"
  | "email"
  | "indexedsecret"
  | "paper"
  | "push"
  | "question"
  | "registration"
  | "tan"
  | "tiqr"
  | "u2f"
  | "vasco"
  | "webauthn"
  | "passkey";

@Component({
  selector: "app-token",
  standalone: true,
  imports: [
    CommonModule,
    MatDrawerContainer,
    MatDrawer,
    MatSidenavModule,
    MatIcon,
    RouterOutlet,
    MatButton,
    MatList,
    MatListItem,
    RouterLink,
    MatExpansionModule,
    MatAccordion,
    NgOptimizedImage,
    MatFabAnchor,
    MatFabButton,
    MatIconButton,
    ThemeSwitcherComponent,
    MatDividerModule,
    MatLabel,
    MatInput,
    MatSuffix,
    MatLabel,
    MatFormField
  ],
  templateUrl: "./token.component.html",
  styleUrl: "./token.component.scss"
})
export class TokenComponent {
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected readonly sessionTimerService: SessionTimerServiceInterface = inject(SessionTimerService);
  protected readonly localService: LocalServiceInterface = inject(LocalService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly router: Router = inject(Router);
  protected readonly AuthService = AuthService;
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly containerService: ContainerServiceInterface = inject(ContainerService);
  private readonly challengeService: ChallengesServiceInterface = inject(ChallengesService);
  private readonly machineService: MachineServiceInterface = inject(MachineService);
  private readonly userService: UserServiceInterface = inject(UserService);
  private readonly auditService: AuditServiceInterface = inject(AuditService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  profileText = this.authService.username() + " @" + this.authService.realm() + " (" + this.authService.role() + ")";
  tokenTypeOptions = signal([]);
  isTokenDrawerOverflowing = signal(false);
  @ViewChild("tokenDetailsComponent")
  tokenDetailsComponent!: TokenDetailsComponent;
  @ViewChild("containerDetailsComponent")
  containerDetailsComponent!: ContainerDetailsComponent;
  @ViewChild("tokenTableComponent") tokenTableComponent!: TokenTableComponent;
  @ViewChild("containerTableComponent")
  containerTableComponent!: ContainerTableComponent;
  @ViewChild("drawer") drawer!: MatDrawer;

  constructor() {
    effect(() => {
      this.contentService.routeUrl();
      this.updateOverflowState();
    });
  }

  refreshPage() {
    if (this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_DETAILS)) {
      this.tokenService.tokenDetailResource.reload();
      if (this.authService.anyContainerActionAllowed()) {
        this.containerService.containerResource.reload();
      }
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
    this.authService.logout();
    this.router.navigate(["login"]).then(() => this.notificationService.openSnackBar("Logout successful."));
  }

  ngAfterViewInit() {
    window.addEventListener("resize", this.updateOverflowState.bind(this));
    this.updateOverflowState();
  }

  updateOverflowState() {
    setTimeout(() => {
      this.isTokenDrawerOverflowing.set(
        this.overflowService.isHeightOverflowing({
          selector: ".token-layout",
          thresholdSelector: ".drawer"
        })
      );
    }, 400);
  }

  ngOnDestroy() {
    window.removeEventListener("resize", this.updateOverflowState);
  }
}
