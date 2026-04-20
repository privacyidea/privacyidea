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
import { Component, input, output } from "@angular/core";

import { FormsModule } from "@angular/forms";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";
import {
  TOTP_HASHLIB,
  TOTP_TIME_STEP,
  TOTP_TIME_SHIFT,
  TOTP_TIME_WINDOW
} from "../../../../../constants/token.constants";

@Component({
  selector: "app-totp-config",
  standalone: true,
  imports: [FormsModule, MatExpansionModule, MatFormFieldModule, MatInputModule, MatSelectModule, ClearButtonComponent],
  templateUrl: "./totp-config.component.html",
  styleUrl: "./totp-config.component.scss"
})
export class TotpConfigComponent {
  protected readonly TOTP_TIME_STEP = TOTP_TIME_STEP;
  protected readonly TOTP_TIME_WINDOW = TOTP_TIME_WINDOW;
  protected readonly TOTP_TIME_SHIFT = TOTP_TIME_SHIFT;
  protected readonly TOTP_HASHLIB = TOTP_HASHLIB;

  formData = input.required<Record<string, any>>();
  totpSteps = input.required<string[]>();
  hashLibs = input.required<string[]>();
  formDataChange = output<Record<string, any>>();

  updateFormData(fieldName: string, value: any): void {
    const newValue = { ...this.formData(), [fieldName]: value };
    this.formDataChange.emit(newValue);
  }

  clearField(fieldName: string): void {
    this.updateFormData(fieldName, "");
  }
}
