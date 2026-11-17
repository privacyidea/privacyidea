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
import { Component, computed, DestroyRef, inject, signal } from "@angular/core";
import { MatAutocomplete, MatAutocompleteTrigger, MatOption } from "@angular/material/autocomplete";
import { MatButton } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatIcon } from "@angular/material/icon";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { AutofocusDirective } from "@components/shared/directives/app-autofocus.directive";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "@services/container/container.service";

export interface ContainerPickerOwner {
  username: string;
  realm: string;
}

export interface ContainerPickerResult {
  containerSerial: string;
  assignToUser: boolean;
  previousOwner: ContainerPickerOwner | null;
}

@Component({
  selector: "app-container-picker-dialog",
  imports: [
    AutofocusDirective,
    ClearableInputComponent,
    DialogWrapperComponent,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatButton,
    MatCheckbox,
    MatIcon,
    MatFormField,
    MatInput,
    MatLabel,
    MatOption
  ],
  templateUrl: "./container-picker-dialog.component.html",
  styleUrl: "./container-picker-dialog.component.scss"
})
export class ContainerPickerDialogComponent extends AbstractDialogComponent<unknown, ContainerPickerResult> {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);

  readonly containerSerial = signal("");

  readonly title = $localize`:@@common.addTokensToContainer:Add Tokens to Container`;

  protected readonly trimmedSerial = computed(() => this.containerSerial().trim());

  protected readonly ownContainers = this.containerService.userContainerSerials;

  // A list whose only entry is the serial already in the field offers nothing to pick, and its
  // panel would cover the checkbox and the hint below. Without options the panel stays closed.
  protected readonly suggestions = computed(() => {
    const options = this.containerService.pickableContainers();
    return options.length === 1 && options[0] === this.trimmedSerial() ? [] : options;
  });

  // The user's own containers are offered as a shortcut, so they count as valid without waiting
  // for the filtered list the backend returns for the input field.
  protected readonly selectableSerials = computed(() => [
    ...this.ownContainers(),
    ...this.containerService.pickableContainers()
  ]);

  readonly assignToUser = signal(true);

  private readonly chosenContainer = computed(() =>
    this.containerService.pickableContainerDetails().find((container) => container.serial === this.trimmedSerial())
  );

  protected readonly belongsToUser = computed(() => this.ownContainers().includes(this.trimmedSerial()));

  protected readonly previousOwner = computed<ContainerPickerOwner | null>(() => {
    if (!this.trimmedSerial() || this.belongsToUser()) {
      return null;
    }
    const owner = this.chosenContainer()?.users?.[0];
    return owner ? { username: owner.user_name, realm: owner.user_realm } : null;
  });

  protected readonly canAssignUser = computed(
    () => this.authService.actionAllowed("container_assign_user") && !!this.chosenContainer() && !this.belongsToUser()
  );

  protected readonly otherOwnerWarning = computed(() => {
    const owner = this.previousOwner()?.username;
    if (!owner) {
      return "";
    }
    return this.canAssignUser() && this.assignToUser()
      ? $localize`:@@container.willBeReassignedFrom:This container belongs to ${owner}:OWNER: and will be moved to this user.`
      : $localize`:@@container.belongsToOtherUser:This container belongs to ${owner}:OWNER:.`;
  });

  readonly confirmActions = computed<DialogAction<ContainerPickerResult>[]>(() => [
    {
      label: $localize`:@@common.add:Add`,
      value: {
        containerSerial: this.trimmedSerial(),
        assignToUser: this.canAssignUser() && this.assignToUser(),
        previousOwner: this.previousOwner()
      },
      type: "confirm",
      primary: true,
      disabled: !this.selectableSerials().includes(this.trimmedSerial())
    }
  ]);

  constructor() {
    super();
    this.containerService.containerPickerFilter.set("");
    this.destroyRef.onDestroy(() => this.containerService.containerPickerFilter.set(null));
  }

  setContainerSerial(containerSerial: string): void {
    this.containerSerial.set(containerSerial);
    this.containerService.containerPickerFilter.set(containerSerial.trim());
  }

  onAction(result: ContainerPickerResult): void {
    this.close(result);
  }
}
