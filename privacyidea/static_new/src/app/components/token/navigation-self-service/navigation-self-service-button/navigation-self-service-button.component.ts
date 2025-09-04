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
import { Component, computed, inject, Input } from "@angular/core";
import { RouterLink, RouterLinkActive } from "@angular/router";
import { MatFabAnchor } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";

import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";

@Component({
  selector: "app-navigation-self-service-button",
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatFabAnchor,
    RouterLink,
    RouterLinkActive
  ],
  templateUrl: "./navigation-self-service-button.component.html",
  styleUrl: "./navigation-self-service-button.component.scss"
})
export class NavigationSelfServiceButtonComponent {
  private readonly contentService: ContentServiceInterface =
    inject(ContentService);
  @Input({ required: true }) key!: string;
  @Input({ required: true }) title!: string;
  @Input() matIconName?: string;
  @Input() matIconClass?: string;
  @Input() matIconSize?:
    | "tile-icon-small"
    | "tile-icon-medium"
    | "tile-icon-large";
  routePath = computed(() => this.key);

  isSelected = computed(() => this.contentService.routeUrl() === this.key);
}
