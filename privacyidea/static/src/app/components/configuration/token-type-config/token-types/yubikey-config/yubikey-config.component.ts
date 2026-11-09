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
import { disabled, form, FormField } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatDivider } from "@angular/material/list";
import { TokenTypeConfigForm } from "@components/configuration/token-type-config/token-type-config.form";
import { ERR, identifierName } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";

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
    MatCheckbox,
    FormField
  ],
  templateUrl: "./yubikey-config.component.html",
  styleUrl: "./yubikey-config.component.scss"
})
export class YubikeyConfigComponent {
  protected readonly ERR = ERR;
  protected readonly hasError = hasError;

  config = input.required<TokenTypeConfigForm>();
  yubikeyApiIds = input.required<string[]>();

  yubikeyCreateNewKey = output<ApiKeyData>();
  deleteRequest = output<string>();

  readonly newKey = signal<ApiKeyData>({ apiId: "", apiKey: "", generateKey: true });
  readonly newKeyForm = form(this.newKey, (path) => {
    identifierName(path.apiId);
    disabled(path.apiKey, () => this.newKey().generateKey);
  });

  createNewKey() {
    if (!this.newKeyForm().valid()) return;
    this.yubikeyCreateNewKey.emit(this.newKey());
    this.newKey.update((key) => ({ ...key, apiId: "", apiKey: "" }));
    this.newKeyForm().reset();
  }

  deleteEntry(key: string) {
    this.deleteRequest.emit(key);
  }
}
