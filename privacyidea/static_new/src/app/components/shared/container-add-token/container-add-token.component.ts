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
import { Component, EventEmitter, Input, Output, WritableSignal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatOption } from "@angular/material/core";
import { MatPaginator, PageEvent } from "@angular/material/paginator";
import { NgClass } from "@angular/common";
import { ClearableInputComponent } from "../clearable-input/clearable-input.component";
import { AuthServiceInterface } from "../../../services/auth/auth.service";

@Component({
  selector: "app-container-add-token",
  standalone: true,
  imports: [
    FormsModule,
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
  @Input({ required: true }) authService!: AuthServiceInterface;
  @Input({ required: true }) showOnlyTokenNotInContainer!: WritableSignal<boolean>;
  @Input({ required: true }) total!: number;
  @Input({ required: true }) pageIndex!: number;
  @Input({ required: true }) pageSize!: number;
  @Input({ required: true }) filterValue!: string;
  @Input({ required: true }) filterIsNotEmpty!: boolean;
  @Input({ required: true }) tokenOptions!: any[];
  @Input() inputClass = "margin-bottom-16 input-width-xl";

  @Output() pageEvent = new EventEmitter<PageEvent>();
  @Output() filterInput = new EventEmitter<Event>();
  @Output() clearFilter = new EventEmitter<void>();
  @Output() addToken = new EventEmitter<any>();
}

