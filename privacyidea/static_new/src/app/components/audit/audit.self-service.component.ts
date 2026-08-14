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
import { Component } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatCardModule } from "@angular/material/card";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import {
  MatCell,
  MatCellDef,
  MatColumnDef,
  MatHeaderCell,
  MatHeaderCellDef,
  MatHeaderRow,
  MatHeaderRowDef,
  MatNoDataRow,
  MatRow,
  MatRowDef,
  MatTable
} from "@angular/material/table";
import { RouterLink } from "@angular/router";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { FilterAutocompleteDirective } from "@components/shared/directives/filter-autocomplete.directive";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { ScrollEdgesDirective } from "@components/shared/directives/scroll-edges.directive";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { LocalDateTimePipe } from "@components/shared/pipes/local-date-time.pipe";
import { AuditComponent } from "./audit.component";

@Component({
  selector: "app-audit-self-service",
  imports: [
    FilterAutocompleteDirective,
    MatCardModule,
    MatCell,
    MatFormField,
    MatHint,
    MatInput,
    MatPaginator,
    MatHeaderCellDef,
    MatHeaderCell,
    MatTable,
    MatCellDef,
    NgClass,
    MatHeaderRowDef,
    MatHeaderRow,
    MatRowDef,
    MatNoDataRow,
    MatRow,
    MatColumnDef,
    MatLabel,
    CopyableComponent,
    RouterLink,
    MatButtonModule,
    MatIcon,
    ScrollToTopDirective,
    ClearableInputComponent,
    ScrollEdgesDirective,
    LocalDateTimePipe
  ],
  templateUrl: "./audit.self-service.component.html",
  styleUrl: "./audit.component.scss"
})
export class AuditSelfServiceComponent extends AuditComponent {}
