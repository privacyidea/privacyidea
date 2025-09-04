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
import { Component, computed, inject, Input, signal, Signal, WritableSignal } from "@angular/core";
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
import { EditableElement, EditButtonsComponent } from "../../../shared/edit-buttons/edit-buttons.component";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";

@Component({
  selector: "app-token-details-user",
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
    EditButtonsComponent,
    NgClass,
    ClearableInputComponent
  ],
  templateUrl: "./token-details-user.component.html",
  styleUrl: "./token-details-user.component.scss"
})
export class TokenDetailsUserComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  @Input() userData = signal<EditableElement[]>([]);
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() isEditingUser!: WritableSignal<boolean>;
  @Input() isEditingInfo!: WritableSignal<boolean>;
  @Input() isAnyEditingOrRevoked!: Signal<boolean>;
  tokenType = computed(() => {
    const tokenDetail = this.tokenService.tokenDetailResource.value();
    return tokenDetail?.result?.value?.tokens?.[0].tokentype;
  });

  unassignUser() {
    this.tokenService.unassignUser(this.tokenSerial()).subscribe({
      next: () => {
        this.tokenService.tokenDetailResource.reload();
      }
    });
  }

  toggleUserEdit(): void {
    this.isEditingUser.update((b) => !b);
    this.realmService.defaultRealmResource.reload();
  }

  cancelUserEdit(): void {
    this.isEditingUser.update((b) => !b);
    this.userService.selectionFilter.set("");
  }

  saveUser() {
    this.tokenService
      .assignUser({
        tokenSerial: this.tokenSerial(),
        username: this.userService.selectionUsernameFilter(),
        realm: this.userService.selectedUserRealm()
      })
      .subscribe({
        next: () => {
          this.userService.selectionFilter.set("");
          this.userService.selectedUserRealm.set("");
          this.isEditingUser.update((b) => !b);
          this.tokenService.tokenDetailResource.reload();
        }
      });
  }
}
