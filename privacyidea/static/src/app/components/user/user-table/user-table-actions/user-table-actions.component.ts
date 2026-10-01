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
import { Component, computed, inject, input, viewChild } from "@angular/core";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatMenu, MatMenuModule } from "@angular/material/menu";
import { MatOption, MatSelect } from "@angular/material/select";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { ResolverService, ResolverServiceInterface } from "@services/resolver/resolver.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { TableAction, TableActionsComponent } from "../../../shared/table-actions/table-actions.component";
import { TableActionsHost } from "../../../shared/table-actions/table-actions-host";

@Component({
  selector: "app-user-table-actions",
  imports: [MatFormField, MatIcon, MatLabel, MatMenuModule, MatOption, MatSelect, TableActionsComponent],
  templateUrl: "./user-table-actions.component.html"
})
export class UserTableActionsComponent extends TableActionsHost {
  private readonly realmMenu = viewChild.required<MatMenu>("realmMenu");
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  private readonly router = inject(Router);
  protected readonly resolverService: ResolverServiceInterface = inject(ResolverService);

  /** Off where the actions stand in for the table itself, which is no place to start creating a user. */
  readonly showCreateUser = input(true);

  anyEditableResolver = computed(() => this.resolverService.editableResolvers().length > 0);

  protected readonly actions = computed<TableAction[]>(() => [
    {
      id: "select-realm",
      label: $localize`:@@user.selectRealm:Select Realm`,
      tone: "secondary",
      width: "m",
      icon: "public",
      placement: "menu",
      submenu: this.realmMenu()
    },
    {
      id: "create-user",
      label: $localize`:@@common.createUser:Create User`,
      tone: "primary",
      width: "m",
      icon: "person",
      menuIcon: "person_add",
      iconClass: "icon-badge-pad-3",
      badge: true,
      visible: this.showCreateUser() && this.authService.actionAllowed("adduser") && this.anyEditableResolver(),
      run: () => this.navigateToCreateUser()
    }
  ]);

  navigateToCreateUser() {
    this.router.navigateByUrl(ROUTE_PATHS.USERS_NEW);
  }
}
