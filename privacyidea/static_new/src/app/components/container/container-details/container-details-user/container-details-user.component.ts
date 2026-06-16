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
import { NgClass } from "@angular/common";
import { Component, inject, input, WritableSignal } from "@angular/core";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatIconButton } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatCell, MatColumnDef, MatRow, MatTable, MatTableModule } from "@angular/material/table";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import { EditableElement, EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";

export interface ContainerDetailsUserHost {
  isEditingInfo: WritableSignal<boolean>;
  isEditingUser: WritableSignal<boolean>;
  isAnyEditing(): boolean;
  unassignUser(): void;
  cancelContainerEdit(element: EditableElement): void;
  saveContainerEdit(element: EditableElement): void;
  toggleContainerEdit(element: EditableElement): void;
}

@Component({
  selector: "app-container-details-user",
  standalone: true,
  imports: [
    NgClass,
    MatFormFieldModule,
    MatInput,
    MatSelectModule,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatTableModule,
    MatCell,
    MatColumnDef,
    MatRow,
    MatTable,
    MatIcon,
    MatIconButton,
    ClearableInputComponent,
    CopyableComponent,
    EditButtonsComponent,
    DetailsCardComponent
  ],
  templateUrl: "./container-details-user.component.html",
  styleUrl: "./container-details-user.component.scss"
})
export class ContainerDetailsUserComponent {
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  readonly host = input.required<ContainerDetailsUserHost>();
  readonly userData = input.required<EditableElement[]>();
}
