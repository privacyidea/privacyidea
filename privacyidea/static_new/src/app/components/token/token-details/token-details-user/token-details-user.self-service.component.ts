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
import { NgClass } from "@angular/common";
import { Component, inject } from "@angular/core";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger, MatOption } from "@angular/material/autocomplete";
import { MatIconButton } from "@angular/material/button";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { MatCell, MatColumnDef, MatTableModule } from "@angular/material/table";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import { OverflowService, OverflowServiceInterface } from "../../../../services/overflow/overflow.service";
import { RealmService, RealmServiceInterface } from "../../../../services/realm/realm.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { UserService, UserServiceInterface } from "../../../../services/user/user.service";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";
import { TokenDetailsUserComponent } from "./token-details-user.component";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";

@Component({
  selector: "app-token-details-user-self-service",
  standalone: true,
  imports: [
    MatTableModule,
    MatColumnDef,
    MatLabel,
    MatCell,
    MatFormField,
    MatInput,
    ReactiveFormsModule,
    MatAutocompleteTrigger,
    MatAutocomplete,
    MatOption,
    FormsModule,
    MatSelect,
    MatIconButton,
    MatIcon,
    NgClass,
    ClearableInputComponent
  ],
  templateUrl: "./token-details-user.self-service.component.html",
  styleUrl: "./token-details-user.component.scss"
})
export class TokenDetailsUserSelfServiceComponent extends TokenDetailsUserComponent {
  protected override tokenService: TokenServiceInterface = inject(TokenService);
  protected override realmService: RealmServiceInterface = inject(RealmService);
  protected override userService: UserServiceInterface = inject(UserService);
  protected override notificationService: NotificationServiceInterface = inject(NotificationService);
  protected override overflowService: OverflowServiceInterface = inject(OverflowService);
  protected  override authService: AuthServiceInterface = inject(AuthService);

  constructor() {
    super();
  }
}
