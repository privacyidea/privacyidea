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

import { CommonModule, NgClass } from "@angular/common";
import { Component, computed, inject, linkedSignal } from "@angular/core";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatOption } from "@angular/material/core";
import { MatFormField } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatSelect } from "@angular/material/select";
import { MatTooltip } from "@angular/material/tooltip";
import { ContainerCreateFormComponent } from "@components/shared/container-create-form/container-create-form.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { UserAssignmentComponent } from "@components/token/user-assignment/user-assignment.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { assert } from "@utils/assert";
import { ContainerCreateComponent } from "./container-create.component";

@Component({
  selector: "app-container-create-self-service",
  imports: [
    MatButton,
    MatFormField,
    MatIcon,
    MatOption,
    MatSelect,
    MatIconButton,
    MatTooltip,
    ScrollToTopDirective,
    StickyHeaderDirective,
    NgClass,
    CommonModule,
    UserAssignmentComponent,
    ContainerCreateFormComponent
  ],
  templateUrl: "./container-create.component.html",
  styleUrl: "./container-create.component.scss"
})
export class ContainerCreateSelfServiceComponent extends ContainerCreateComponent {
  protected override authService: AuthServiceInterface = inject(AuthService);

  override selectedUserRealm = linkedSignal(() => {
    const realm = this.authService.authData()?.realm ?? "";
    assert(realm != "", "User must have a realm to create a container in self-service");
    return realm;
  });
  override selectedUser = computed(() => {
    const userName = this.authService.authData()?.username ?? "";
    assert(userName != "", "User must be authenticated to create a container in self-service");
    return userName;
  });
}
