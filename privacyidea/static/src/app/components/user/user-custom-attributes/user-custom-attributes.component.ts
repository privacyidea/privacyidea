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
import { Component, input } from "@angular/core";
import { FormField } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import { DetailFieldRowComponent } from "@components/shared/details-shared/field-editing/detail-field-row/detail-field-row.component";
import { CustomAttributeDraft } from "./custom-attribute-draft";

@Component({
  selector: "app-user-custom-attributes",
  standalone: true,
  imports: [
    FormField,
    MatButtonModule,
    MatIcon,
    MatFormField,
    MatInput,
    MatLabel,
    MatSelectModule,
    DetailsCardComponent,
    DetailFieldRowComponent
  ],
  templateUrl: "./user-custom-attributes.component.html",
  styleUrl: "../user-details/user-details.component.scss"
})
export class UserCustomAttributesComponent {
  draft = input.required<CustomAttributeDraft>();
}
