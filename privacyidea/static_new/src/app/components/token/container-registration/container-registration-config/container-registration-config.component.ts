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
import { Component, computed, EventEmitter, Input, Output, signal, Signal, effect } from "@angular/core";
import { MatError, MatFormField, MatHint, MatLabel, MatSuffix } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { FormsModule } from "@angular/forms";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";

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
    MatCheckbox,
    MatIconModule,
    MatButtonModule,
    MatSuffix,
    MatError
  ]
})
export class ContainerRegistrationConfigComponent {
  @Input() passphrasePrompt = signal("");
  @Input() passphraseResponse = signal("");
  @Input() userStorePassphrase = signal(false);
  @Input() containerHasOwner: boolean = false;
  @Output() validInputChange = new EventEmitter<boolean>();

  defaultPrompt: string = "Please enter your user store passphrase.";

  showPassphrase: boolean = false;
  showRepeatPassphrase: boolean = false;
  repeatPassphraseResponse = signal("");

  promptRequired = computed(() => this.userStorePassphrase() || this.passphraseResponse());

  private validInputEffect = effect(() => {
    this.validInputChange.emit(this.validInput());
  });

  toggleShowPassphrase() {
    this.showPassphrase = !this.showPassphrase;
  }

  onUserStorePassphraseChange() {
    if (this.userStorePassphrase()) {
      this.passphraseResponse.set("");
      this.repeatPassphraseResponse.set("");
      if (!this.passphrasePrompt()) {
        this.passphrasePrompt.set(this.defaultPrompt);
      }
    }
  }

  validInput: Signal<boolean> = computed(() => {
    if (this.userStorePassphrase()) {
      return true;
    } else if (this.passphrasePrompt()) {
      return !!this.passphraseResponse() && this.passphraseResponse() === this.repeatPassphraseResponse();
    } else {
      return !this.passphraseResponse() && !this.repeatPassphraseResponse();
    }
  });

  get passphraseMismatch(): boolean {
    return (
      !this.userStorePassphrase() &&
      this.passphraseResponse() !== this.repeatPassphraseResponse()
    );
  }
}