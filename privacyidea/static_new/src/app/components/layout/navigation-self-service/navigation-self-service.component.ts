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

import { Component, inject } from "@angular/core";
import { MatRippleModule } from "@angular/material/core";
import { MatIconModule } from "@angular/material/icon";
import { RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { NavigationSelfServiceButtonComponent } from "@components/layout/navigation-self-service/navigation-self-service-button/navigation-self-service-button.component";
import { UserUtilsPanelSelfServiceComponent } from "@components/layout/user-utils-panel/user-utils-panel.self-service.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";

@Component({
  selector: "app-navigation-self-service",
  standalone: true,
  imports: [
    NavigationSelfServiceButtonComponent,
    UserUtilsPanelSelfServiceComponent,
    MatIconModule,
    MatRippleModule,
    RouterLink
  ],
  templateUrl: "./navigation-self-service.component.html",
  styleUrl: "./navigation-self-service.component.scss"
})
export class NavigationSelfServiceComponent {
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly Boolean = Boolean;
  userData = this.userService.user;
}
