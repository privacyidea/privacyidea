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
import { Component, inject, input, output } from "@angular/core";
import { NgClass } from "@angular/common";
import { MatList, MatListItem } from "@angular/material/list";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "../../../../route_paths";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { NavSection } from "../navigation.component";

@Component({
  selector: "app-navigation-sub-drawer",
  imports: [
    MatList,
    MatListItem,
    MatButton,
    MatIconButton,
    MatIcon,
    RouterLink,
    NgClass
  ],
  templateUrl: "./navigation-sub-drawer.component.html",
  styleUrl: "./navigation-sub-drawer.component.scss"
})
export class NavigationSubDrawerComponent {
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;

  activeSection = input.required<NavSection>();
  closed = output<void>();

  close(): void {
    this.closed.emit();
  }
}

