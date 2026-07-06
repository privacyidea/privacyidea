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
import { NgClass } from "@angular/common";
import { Component, input, model, output } from "@angular/core";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatPaginator, PageEvent } from "@angular/material/paginator";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { AuthServiceInterface } from "@services/auth/auth.service";
import { TokenDetails } from "@services/token/token.service";

@Component({
  selector: "app-container-add-token",
  standalone: true,
  imports: [
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatCheckbox,
    MatFormField,
    MatHint,
    MatIcon,
    MatInput,
    MatLabel,
    MatOption,
    MatPaginator,
    NgClass,
    ClearableInputComponent
  ],
  templateUrl: "./container-add-token.component.html"
})
export class ContainerAddTokenComponent {
  authService = input.required<AuthServiceInterface>();
  showOnlyTokenInContainer = model.required<boolean>();
  total = input.required<number>();
  pageIndex = input.required<number>();
  pageSize = input.required<number>();
  filterValue = input.required<string>();
  filterIsNotEmpty = input.required<boolean>();
  tokenOptions = input.required<TokenDetails[]>();
  inputClass = input("margin-bottom-16 input-width-xl");

  pageEvent = output<PageEvent>();
  filterInput = output<Event>();
  clearFilter = output<void>();
  addToken = output<TokenDetails>();
}
