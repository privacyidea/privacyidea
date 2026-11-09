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
import { Component, signal } from "@angular/core";
import { form } from "@angular/forms/signals";
import {
  ContainerRegistrationConfigComponent,
  emptyRegistration,
  registrationRules
} from "@components/container/container-registration/container-registration-config/container-registration-config.component";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";
import { touchAll } from "@utils/form-state.utils";

export interface ContainerRegistrationInitDialogData {
  rollover: boolean;
  containerHasOwner: boolean;
  registerContainer: (
    userStorePassphrase: boolean,
    passphrasePrompt: string,
    passphraseResponse: string,
    rollover: boolean
  ) => void;
}

@Component({
  selector: "app-container-registration-init-dialog",
  templateUrl: "./container-registration-init-dialog.component.html",
  imports: [ContainerRegistrationConfigComponent, DialogWrapperComponent]
})
export class ContainerRegistrationInitDialogComponent extends AbstractDialogComponent<ContainerRegistrationInitDialogData> {
  readonly registration = signal(emptyRegistration());
  readonly form = form(this.registration, (f) =>
    registrationRules(f, { value: this.registration, hasOwner: () => this.data.containerHasOwner })
  );

  getAction(): DialogAction<"register" | "rollover"> {
    if (this.data.rollover) {
      return {
        label: $localize`:@@common.rollover:Rollover`,
        value: "rollover",
        type: "confirm",
        disabled: !this.form().valid(),
        primary: true
      };
    } else {
      return {
        label: $localize`:@@container.register:Register`,
        value: "register",
        type: "confirm",
        disabled: !this.form().valid(),
        primary: true
      };
    }
  }
  onAction(value: "register" | "rollover") {
    switch (value) {
      case "register":
        this.onRegister();
        break;
      case "rollover":
        this.onRegister();
        break;
      default:
        break;
    }
  }

  onRegister() {
    if (!this.form().valid()) {
      void touchAll(this.form);
      return;
    }
    const registration = this.registration();
    this.data.registerContainer(registration.store, registration.prompt, registration.response, this.data.rollover);
  }
}
