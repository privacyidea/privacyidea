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
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatDivider } from "@angular/material/list";

@Component({
  selector: "app-yubikey-config",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatDivider
  ],
  templateUrl: "./yubikey-config.component.html",
  styleUrl: "./yubikey-config.component.scss"
})
export class YubikeyConfigComponent {
  formData = input.required<Record<string, any>>();
  yubikeyApiIds = input.required<string[]>();

  onYubikeyCreateNewKey = output<string>();
  onDeleteEntry = output<string>();

  newYubikeyApiId = signal("");
  newYubikeyApiKey = signal("");

  createNewKey() {
    if (this.newYubikeyApiId()) {
      this.onYubikeyCreateNewKey.emit(this.newYubikeyApiId());
      this.newYubikeyApiId.set("");
      this.newYubikeyApiKey.set("");
    }
  }

  deleteEntry(key: string) {
    this.onDeleteEntry.emit(key);
  }
}
