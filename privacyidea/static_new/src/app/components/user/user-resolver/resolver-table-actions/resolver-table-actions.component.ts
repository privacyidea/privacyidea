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
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { Router } from "@angular/router";
import { AuthService } from "../../../../services/auth/auth.service";
import { ROUTE_PATHS } from "src/app/route_paths";

@Component({
  selector: "app-resolver-table-actions",
  standalone: true,
  imports: [MatButtonModule, MatIconModule],
  templateUrl: "./resolver-table-actions.component.html",
  styleUrl: "./resolver-table-actions.component.scss"
})
export class ResolverTableActionsComponent {
  protected readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  onNewResolver(): void {
    this.router.navigate([ROUTE_PATHS.USERS_RESOLVERS, "new"]);
  }
}
