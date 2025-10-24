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
import { Component, Input } from "@angular/core";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { FormsModule } from "@angular/forms";
import { MatCheckbox } from "@angular/material/checkbox";

@Component({
  selector: "app-container-registration-config",
  templateUrl: "./container-registration-config.component.html",
  styleUrls: ["./container-registration-config.component.scss"],
  imports: [
    MatFormField,
    MatInput,
    FormsModule,
    MatHint,
    MatLabel,
    MatCheckbox
  ]
})
export class ContainerRegistrationConfigComponent {
  @Input() passphrasePrompt: string = "";
  @Input() passphraseResponse: string = "";
  @Input() userStorePassphrase: boolean = false;
  @Input() containerHasOwner: boolean = false;

  defaultPrompt: string = "Please enter your user store passphrase.";

  onUserStorePassphraseChange() {
    if (this.userStorePassphrase) {
      this.passphraseResponse = "";
      if (!this.passphrasePrompt) {
        this.passphrasePrompt = this.defaultPrompt;
      }
    }
  }
}