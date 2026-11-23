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
import { Component, computed, inject, linkedSignal, signal } from "@angular/core";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  ContainerCreateData,
  ContainerService,
  ContainerServiceInterface,
  ContainerType
} from "@services/container/container.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

export interface ContainerCreateDialogData {
  // Optional user the new container can be assigned to.
  username?: string;
  userRealm?: string;
  // Whether the user assignment checkbox is initially checked.
  checkUserAssignment?: boolean;
}

/**
 * Dialog for a basic container creation (type, description and optional user assignment).
 * It closes with the serial of the created container or undefined if the creation was cancelled.
 */
@Component({
  selector: "app-container-create-dialog",
  standalone: true,
  imports: [MatFormField, MatLabel, MatSelect, MatOption, MatInput, MatCheckbox, DialogWrapperComponent],
  templateUrl: "./container-create-dialog.component.html",
  styleUrl: "./container-create-dialog.component.scss"
})
export class ContainerCreateDialogComponent extends AbstractDialogComponent<
  ContainerCreateDialogData | undefined,
  string
> {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  readonly description = signal("");
  readonly assignUser = signal(this.data?.checkUserAssignment ?? false);
  readonly isCreating = signal(false);

  // Only container types that support the currently relevant token type can be created.
  readonly typeOptions = computed<ContainerType[]>(() => {
    const options = this.containerService.containerTypeOptions();
    const tokenType = this.containerService.compatibleWithSelectedTokenType();
    if (!tokenType) return options;
    return options.filter((option) => (option.token_types ?? []).includes(tokenType));
  });

  readonly selectedType = linkedSignal<ContainerType[], ContainerType | undefined>({
    source: this.typeOptions,
    computation: (options) =>
      options.find((option) => option.containerType === this.authService.defaultContainerType()) ?? options[0]
  });

  readonly supportedTokenTypes = computed<string>(() => {
    const tokenTypes = this.selectedType()?.token_types ?? [];
    const allTokenTypes = this.tokenService.tokenTypeOptions().length;
    if (allTokenTypes > 0 && tokenTypes.length >= allTokenTypes) {
      return $localize`:@@common.all:All`;
    }
    return tokenTypes.join(", ");
  });

  readonly showUserAssignment = computed(
    () => !!this.data?.username && this.authService.actionAllowed("container_assign_user")
  );

  readonly actions = computed<DialogAction<"create">[]>(() => [
    {
      label: $localize`:@@common.createContainer:Create Container`,
      value: "create",
      type: "confirm",
      primary: true,
      disabled: !this.selectedType() || this.isCreating()
    }
  ]);

  onAction(action: "create"): void {
    if (action === "create") {
      this.createContainer();
    }
  }

  createContainer(): void {
    const type = this.selectedType();
    if (!type || this.isCreating()) return;

    const createData: ContainerCreateData = {
      type: type.containerType,
      description: this.description()
    };
    if (this.showUserAssignment() && this.assignUser() && this.data?.username) {
      createData.user = this.data.username;
      createData.realm = this.data.userRealm ?? "";
    }

    this.isCreating.set(true);
    this.containerService.createContainer(createData).subscribe({
      next: (response) => {
        const serial = response.result?.value?.container_serial;
        if (serial) {
          this.dialogRef.close(serial);
        } else {
          this.isCreating.set(false);
        }
      },
      error: () => this.isCreating.set(false)
    });
  }
}
