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

import { MatButtonModule } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatDivider } from "@angular/material/list";

export interface ApiKeyData {
  apiId: string;
  apiKey: string;
  generateKey: boolean;
}

@Component({
  selector: "app-yubikey-config",
  standalone: true,
  imports: [
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
  formData = input.required<Record<string, string>>();
  yubikeyApiIds = input.required<string[]>();

  yubikeyCreateNewKey = output<ApiKeyData>();
  deleteRequest = output<string>();

  newYubikeyApiId = signal("");
  newYubikeyApiKey = signal("");
  newYubikeyGenKey = signal(true);

  createNewKey() {
    const apiId = this.newYubikeyApiId();
    if (apiId && /^[a-zA-Z0-9._-]*$/.test(apiId)) {
      const newKeyData = {
        apiId: this.newYubikeyApiId(),
        apiKey: this.newYubikeyApiKey(),
        generateKey: this.newYubikeyGenKey()
      };
      this.yubikeyCreateNewKey.emit(newKeyData);
      this.newYubikeyApiId.set("");
      this.newYubikeyApiKey.set("");
    }
  }

  deleteEntry(key: string) {
    this.deleteRequest.emit(key);
  }
}
