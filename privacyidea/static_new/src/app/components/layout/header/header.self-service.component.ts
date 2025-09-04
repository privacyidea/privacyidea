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
import { DatePipe, NgClass, NgOptimizedImage } from "@angular/common";
import { Component, inject } from "@angular/core";
import { MatFabAnchor, MatFabButton, MatIconButton } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatMenu, MatMenuTrigger } from "@angular/material/menu";
import { Router } from "@angular/router";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import { LocalService, LocalServiceInterface } from "../../../services/local/local.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import {
  SessionTimerService,
  SessionTimerServiceInterface
} from "../../../services/session-timer/session-timer.service";
import { ThemeSwitcherComponent } from "../../shared/theme-switcher/theme-switcher.component";
import { UserSelfServiceComponent } from "../../user/user.self-service.component";
import { HeaderComponent } from "./header.component";

@Component({
  selector: "app-header-self-service",
  standalone: true,
  imports: [
    NgOptimizedImage,
    MatFabButton,
    MatFabAnchor,
    MatIconModule,
    DatePipe,
    NgClass,
    MatIconButton,
    MatMenuTrigger,
    MatMenu,
    UserSelfServiceComponent,
    ThemeSwitcherComponent
  ],
  templateUrl: "./header.self-service.component.html",
  styleUrl: "./header.component.scss"
})
export class HeaderSelfServiceComponent extends HeaderComponent {
  protected override readonly sessionTimerService: SessionTimerServiceInterface =
    inject(SessionTimerService);
  protected override readonly authService: AuthServiceInterface =
    inject(AuthService);
  protected override readonly localService: LocalServiceInterface =
    inject(LocalService);
  protected override readonly notificationService: NotificationServiceInterface =
    inject(NotificationService);
  protected override readonly router: Router = inject(Router);

  constructor() {
    super();
  }
}
