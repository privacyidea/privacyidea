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

import { Component, computed, inject } from "@angular/core";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import { TableAction, TableActionsComponent } from "../../../shared/table-actions/table-actions.component";
import { TableActionsHost } from "../../../shared/table-actions/table-actions-host";

@Component({
  selector: "app-resolver-table-actions",
  standalone: true,
  imports: [TableActionsComponent],
  templateUrl: "./resolver-table-actions.component.html"
})
export class ResolverTableActionsComponent extends TableActionsHost {
  protected readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly actions = computed<TableAction[]>(() => [
    {
      id: "new",
      label: $localize`:@@resolver.newResolver:New Resolver`,
      tone: "primary",
      width: "m",
      fontIcon: "ms--database",
      iconClass: "icon-badge-pad-3",
      badge: true,
      visible: this.authService.actionAllowed("resolverwrite"),
      run: () => this.onNewResolver()
    }
  ]);

  onNewResolver(): void {
    this.router.navigate([ROUTE_PATHS.USERS_RESOLVERS, "new"]);
  }
}
