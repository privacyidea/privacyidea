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
import { Component, input, output, signal } from "@angular/core";

import { FormsModule } from "@angular/forms";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatDivider } from "@angular/material/list";
import { MatCheckbox } from "@angular/material/checkbox";

export type ApiKeyData = {
  apiId: string;
  apiKey: string;
  generateKey: boolean;
};

@Component({
  selector: "app-yubikey-config",
  standalone: true,
  imports: [
    FormsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatDivider,
    MatCheckbox
  ],
  templateUrl: "./yubikey-config.component.html",
  styleUrl: "./yubikey-config.component.scss"
})
export class YubikeyConfigComponent {
  formData = input.required<Record<string, any>>();
  yubikeyApiIds = input.required<string[]>();

  onYubikeyCreateNewKey = output<ApiKeyData>();
  onDeleteEntry = output<string>();

  newYubikeyApiId = signal("");
  newYubikeyApiKey = signal("");
  newYubikeyGenKey = signal(true);

  createNewKey() {
    if (this.newYubikeyApiId()) {
      const newKeyData = {
        apiId: this.newYubikeyApiId(),
        apiKey: this.newYubikeyApiKey(),
        generateKey: this.newYubikeyGenKey()
      };
      this.onYubikeyCreateNewKey.emit(newKeyData);
      this.newYubikeyApiId.set("");
      this.newYubikeyApiKey.set("");
    }
  }

  deleteEntry(key: string) {
    this.onDeleteEntry.emit(key);
  }
}
