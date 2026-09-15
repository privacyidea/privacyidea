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

import { CommonModule } from "@angular/common";
import { Component, input } from "@angular/core";
import { MatCardModule } from "@angular/material/card";
import { MatListModule } from "@angular/material/list";
import { TokenEnrollmentPayload } from "@app/mappers/token-api-payload/_token-api-payload.mapper";

type TemplateTokenValue = TokenEnrollmentPayload[keyof TokenEnrollmentPayload];

@Component({
  selector: "app-view-template-tokens",
  standalone: true,
  imports: [CommonModule, MatCardModule, MatListModule],
  templateUrl: "./view-template-tokens.component.html",
  styleUrl: "./view-template-tokens.component.scss"
})
export class ViewTemplateTokensComponent {
  readonly templateTokens = input.required<TokenEnrollmentPayload[] | undefined>();

  isObject(value: TemplateTokenValue): boolean {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  asObject(value: TemplateTokenValue): Record<string, TemplateTokenValue> {
    return value as unknown as Record<string, TemplateTokenValue>;
  }

  isValidValue(val: TemplateTokenValue): boolean {
    return val !== null && val !== undefined && val !== "" && typeof val !== "function";
  }
}
