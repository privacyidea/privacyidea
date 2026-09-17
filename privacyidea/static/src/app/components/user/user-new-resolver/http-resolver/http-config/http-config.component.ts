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
import { Component, input, model } from "@angular/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { MatCheckboxModule } from "@angular/material/checkbox";

export interface HttpConfigModel {
  method: string;
  endpoint: string;
  headers: string;
  requestMapping: string;
  responseMapping: string;
  hasSpecialErrorHandler: boolean;
  errorResponse: string;
}

@Component({
  selector: "app-http-config",
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, MatSelectModule, MatCheckboxModule, ClearableInputComponent],
  templateUrl: "./http-config.component.html",
  styleUrl: "./http-config.component.scss"
})
export class HttpConfigComponent {
  model = model.required<HttpConfigModel>();
  title = input.required<string>();
  description = input<string>();
  endpointHint = input<string>();
}
