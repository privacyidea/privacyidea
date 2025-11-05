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
import { CommonModule } from "@angular/common";
import { Component, effect, inject, ViewChild } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatSidenavModule } from "@angular/material/sidenav";
import { ContentService, ContentServiceInterface } from "../../services/content/content.service";
import { OverflowService, OverflowServiceInterface } from "../../services/overflow/overflow.service";
import { UserService, UserServiceInterface } from "../../services/user/user.service";
import { UserDetailsComponent } from "./user-details/user-details.component";
import { UserTableComponent } from "./user-table/user-table.component";

@Component({
  selector: "app-user",
  standalone: true,
  imports: [CommonModule, MatSidenavModule, MatButtonModule],
  templateUrl: "./user.component.html",
  styleUrl: "./user.component.scss"
})
export class UserComponent {
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly userService: UserServiceInterface = inject(UserService);

  @ViewChild("userDetailsComponent")
  userDetailsComponent!: UserDetailsComponent;
  @ViewChild("userTableComponent")
  userTableComponent!: UserTableComponent;

  constructor() {
    effect(() => {
      this.contentService.routeUrl();
    });
  }
}
