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
import { MatSelectModule } from "@angular/material/select";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";
import { HOTP_HASHLIB, HOTP_OTP_LENGTH } from "../../../../../constants/token.constants";

@Component({
  selector: "app-hotp-config",
  standalone: true,
  imports: [FormsModule, MatExpansionModule, MatFormFieldModule, MatSelectModule, ClearButtonComponent],
  templateUrl: "./hotp-config.component.html",
  styleUrl: "./hotp-config.component.scss"
})
export class HotpConfigComponent {
  formData = input.required<Record<string, any>>();
  hashLibs = input.required<string[]>();
  formDataChange = output<Record<string, any>>();

  updateFormData(fieldName: string, value: any): void {
    const newValue = { ...this.formData(), [fieldName]: value };
    this.formDataChange.emit(newValue);
  }

  clearField(fieldName: string): void {
    this.updateFormData(fieldName, "");
  }

  protected readonly HOTP_HASHLIB = HOTP_HASHLIB;
  protected readonly HOTP_OTP_LENGTH = HOTP_OTP_LENGTH;
}
