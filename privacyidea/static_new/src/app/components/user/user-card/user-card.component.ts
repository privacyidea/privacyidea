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
import { NgClass } from "@angular/common";
import { RouterLink } from "@angular/router";

import { MatCard, MatCardContent } from "@angular/material/card";
import { MatList, MatListItem } from "@angular/material/list";
import { MatIcon } from "@angular/material/icon";
import { MatButton } from "@angular/material/button";
import { MatDivider } from "@angular/material/divider";

import { OverflowService, OverflowServiceInterface } from "../../../services/overflow/overflow.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { VersioningService, VersioningServiceInterface } from "../../../services/version/version.service";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatSelect } from "@angular/material/select";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatOption } from "@angular/material/core";
import { RealmService, RealmServiceInterface } from "../../../services/realm/realm.service";
import { UserService, UserServiceInterface } from "../../../services/user/user.service";
import { ROUTE_PATHS } from "../../../route_paths";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";

@Component({
  selector: "app-user-card",
  standalone: true,
  imports: [
    MatCard,
    MatCardContent,
    MatIcon,
    MatList,
    MatListItem,
    MatButton,
    MatDivider,
    RouterLink,
    NgClass,
    MatSelect,
    MatFormField,
    MatLabel,
    MatSelect,
    MatOption,
    ReactiveFormsModule,
    FormsModule
  ],
  templateUrl: "./user-card.component.html",
  styleUrls: ["./user-card.component.scss"]
})
export class UserCardComponent {
  protected readonly overflowService: OverflowServiceInterface =
    inject(OverflowService);
  protected readonly contentService: ContentServiceInterface =
    inject(ContentService);
  protected readonly versioningService: VersioningServiceInterface =
    inject(VersioningService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
}
