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
import { Component, computed, effect, Input, Signal, signal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatFormField, MatHint, MatLabel, MatSuffix } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";

@Component({
  selector: "app-container-registration-config",
  templateUrl: "./container-registration-config.component.html",
  styleUrls: ["./container-registration-config.component.scss"],
  imports: [MatFormField, MatInput, MatHint, MatLabel, MatCheckbox, MatIconModule, MatButtonModule, MatSuffix]
})
export class ContainerRegistrationConfigComponent {
  @Input() passphrasePrompt = signal("");
  @Input() passphraseResponse = signal("");
  @Input() userStorePassphrase = signal(false);
  @Input() containerHasOwner = false;
  @Output() validInputChange = new EventEmitter<boolean>();

  defaultPrompt = "Please enter your user store passphrase.";

  showPassphrase = false;
  showRepeatPassphrase = false;
  repeatPassphraseResponse = signal("");

  promptRequired = computed(() => this.userStorePassphrase() || this.passphraseResponse());
  validInput: Signal<boolean> = computed(() => {
    if (this.userStorePassphrase()) {
      return true;
    } else if (this.passphrasePrompt()) {
      return !!this.passphraseResponse() && this.passphraseResponse() === this.repeatPassphraseResponse();
    } else {
      return !this.passphraseResponse() && !this.repeatPassphraseResponse();
    }
  });
  private validInputEffect = effect(() => {
    this.validInputChange.emit(this.validInput());
  });

  get passphraseMismatch(): boolean {
    return !this.userStorePassphrase() && this.passphraseResponse() !== this.repeatPassphraseResponse();
  }

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
}
