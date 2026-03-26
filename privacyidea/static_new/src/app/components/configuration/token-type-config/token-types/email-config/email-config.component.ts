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
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "../../../../../route_paths";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";
import { EMAIL_SMTP_SERVER_KEY, EMAIL_VALIDITY_TIME_KEY } from "../../../../../constants/token.constants";

@Component({
  selector: "app-email-config",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    RouterLink,
    ClearButtonComponent
  ],
  templateUrl: "./email-config.component.html",
  styleUrl: "./email-config.component.scss"
})
export class EmailConfigComponent {
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  formData = input.required<Record<string, any>>();
  formDataChange = output<Record<string, any>>();
  smtpServers = input.required<string[]>();
  expanded = input<boolean>(false);

  updateFormData(fieldName: string, value: any): void {
    const newValue = { ...this.formData(), [fieldName]: value };
    this.formDataChange.emit(newValue);
  }

  clearField(fieldName: string): void {
    this.updateFormData(fieldName, "");
  }

  protected readonly EMAIL_SMTP_SERVER_KEY = EMAIL_SMTP_SERVER_KEY;
  protected readonly EMAIL_VALIDITY_TIME_KEY = EMAIL_VALIDITY_TIME_KEY;
}
