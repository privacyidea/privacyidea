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
import { Component, inject } from "@angular/core";
import { DatePipe, NgClass, NgOptimizedImage } from "@angular/common";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatInput, MatLabel, MatSuffix } from "@angular/material/input";
import { MatList, MatListItem } from "@angular/material/list";
import { ThemeSwitcherComponent } from "../../shared/theme-switcher/theme-switcher.component";
import { ROUTE_PATHS } from "../../../route_paths";
import { MatAnchor, MatButton, MatFabButton, MatIconButton } from "@angular/material/button";
import { MatFormField } from "@angular/material/form-field";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import { Router, RouterLink } from "@angular/router";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";
import { ContainerService, ContainerServiceInterface } from "../../../services/container/container.service";
import { ChallengesService, ChallengesServiceInterface } from "../../../services/token/challenges/challenges.service";
import { MachineService, MachineServiceInterface } from "../../../services/machine/machine.service";
import { UserService, UserServiceInterface } from "../../../services/user/user.service";
import { AuditService, AuditServiceInterface } from "../../../services/audit/audit.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import {
  SessionTimerService,
  SessionTimerServiceInterface
} from "../../../services/session-timer/session-timer.service";

@Component({
  selector: "app-navigation",
  imports: [
    DatePipe,
    MatAccordion,
    MatButton,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatFabButton,
    MatFormField,
    MatIconModule,
    MatIconButton,
    MatInput,
    MatLabel,
    MatList,
    MatListItem,
    MatSuffix,
    NgOptimizedImage,
    ThemeSwitcherComponent,
    MatIcon,
    RouterLink,
    NgClass,
    MatAnchor
  ],
  templateUrl: "./navigation.component.html",
  styleUrl: "./navigation.component.scss"
})
export class NavigationComponent {
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly containerService: ContainerServiceInterface = inject(ContainerService);
  private readonly challengeService: ChallengesServiceInterface = inject(ChallengesService);
  private readonly machineService: MachineServiceInterface = inject(MachineService);
  private readonly userService: UserServiceInterface = inject(UserService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly auditService: AuditServiceInterface = inject(AuditService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly sessionTimerService: SessionTimerServiceInterface = inject(SessionTimerService);
  protected readonly router: Router = inject(Router);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;

  profileText = this.authService.username() + " @" + this.authService.realm() + " (" + this.authService.role() + ")";

  logout(): void {
    this.authService.logout();
    this.router.navigate(["login"]).then(() => this.notificationService.openSnackBar("Logout successful."));
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
}
