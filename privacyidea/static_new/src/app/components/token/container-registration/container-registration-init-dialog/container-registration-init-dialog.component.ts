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
import { Component, ViewChild } from "@angular/core";
import { MatDialogContent } from "@angular/material/dialog";
import { ContainerRegistrationConfigComponent } from "../container-registration-config/container-registration-config.component";
import { AbstractDialogComponent } from "../../../shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "../../../../models/dialog";

@Component({
  selector: "app-container-registration-init-dialog",
  templateUrl: "./container-registration-init-dialog.component.html",
  styleUrls: ["./container-registration-init-dialog.component.scss"],
  imports: [MatDialogContent, ContainerRegistrationConfigComponent, DialogWrapperComponent]
})
export class ContainerRegistrationInitDialogComponent extends AbstractDialogComponent<any> {
  @ViewChild(ContainerRegistrationConfigComponent)
  registrationConfigComponent!: ContainerRegistrationConfigComponent;

  getAction(): DialogAction<"register" | "rollover"> {
    if (this.data.rollover) {
      return {
        label: $localize`Rollover`,
        value: "rollover",
        type: "confirm",
        disabled: !this.validInput
      };
    } else {
      return {
        label: $localize`Register`,
        value: "register",
        type: "confirm",
        disabled: !this.validInput
      };
    }
  }
  onActionClick(value: "register" | "rollover") {
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
    this.data.registerContainer(
      this.registrationConfigComponent.userStorePassphrase(),
      this.registrationConfigComponent.passphrasePrompt(),
      this.registrationConfigComponent.passphraseResponse(),
      this.data.rollover
    );
  }

  validInput = true;

  onValidInputChange(isValid: boolean) {
    this.validInput = isValid;
  }
}
