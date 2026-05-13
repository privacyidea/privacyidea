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
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatOption, MatSelect } from "@angular/material/select";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { ResolverService, ResolverServiceInterface } from "@services/resolver/resolver.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { OverflowNavDirective } from "../../../shared/directives/overflow-nav/overflow-nav.directive";

@Component({
  selector: "app-user-table-actions",
  imports: [MatButtonModule, MatFormField, MatLabel, MatOption, MatSelect, FormsModule, MatIcon, OverflowNavDirective],
  templateUrl: "./user-table-actions.component.html",
  styleUrl: "./user-table-actions.component.scss"
})
export class UserTableActionsComponent {
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  private readonly router = inject(Router);
  protected readonly resolverService: ResolverServiceInterface = inject(ResolverService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;

  anyEditableResolver = computed(() => this.resolverService.editableResolvers().length > 0);

  navigateToCreateUser() {
    this.router.navigateByUrl(ROUTE_PATHS.USERS_NEW);
  }
}
