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
import { Component, computed, inject } from "@angular/core";
import { NavigationSelfServiceButtonComponent } from "./navigation-self-service-button/navigation-self-service-button.component";
import { ROUTE_PATHS } from "../../../route_paths";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import { MatIcon } from "@angular/material/icon";
import { UserService, UserServiceInterface } from "../../../services/user/user.service";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";

@Component({
  selector: "app-navigation-self-service",
  standalone: true,
  imports: [
    NavigationSelfServiceButtonComponent,
    MatIcon,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatAccordion
  ],
  templateUrl: "./navigation-self-service.component.html",
  styleUrl: "./navigation-self-service.component.scss"
})
export class NavigationSelfServiceComponent {
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly Boolean = Boolean;
  private readonly userService: UserServiceInterface = inject(UserService);

  readonly labels: Record<string, string> = {
    username: $localize`Username`,
    givenname: $localize`Given name`,
    surname: $localize`Surname`,
    description: $localize`Description`,
    email: $localize`Email`,
    phone: $localize`Phone`,
    mobile: $localize`Mobile`,
    userid: $localize`User ID`,
    resolver: $localize`Resolver`
  };

  readonly excludedKeys = new Set<string>(["editable", "username"]);

  readonly detailOrder: string[] = [
    "givenname",
    "surname",
    "description",
    "email",
    "phone",
    "mobile"
  ];

  userData = this.userService.user;

  detailsEntries = computed(() => {
    const data = this.userData() ?? {};
    const result: { key: string; label: string; value: unknown }[] = [];

    for (const key of this.detailOrder) {
      if (!(key in data)) continue;
      if (this.excludedKeys.has(key)) continue;

      const raw = (data as any)[key];

      result.push({
        key,
        label: this.labels[key] ?? key,
        value: this.normalizeValue(raw)
      });
    }

    for (const [key, raw] of Object.entries(data)) {
      if (this.excludedKeys.has(key)) continue;
      if (this.detailOrder.includes(key)) continue;

      result.push({
        key,
        label: this.labels[key] ?? key,
        value: this.normalizeValue(raw)
      });
    }

    return result;
  });

  isArray(value: unknown): value is string[] {
    return Array.isArray(value);
  }

  private normalizeValue(value: unknown): unknown {
    if (value === null || value === undefined) return "-";
    if (typeof value === "string" && value.trim() === "") return "-";
    return value;
  }
}
