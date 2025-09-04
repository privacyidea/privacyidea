/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { Component } from "@angular/core";
import { MatCardModule } from "@angular/material/card";
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
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { FormsModule } from "@angular/forms";
import { MatInput } from "@angular/material/input";
import { NgClass } from "@angular/common";
import { MatPaginator } from "@angular/material/paginator";
import { MatDrawer, MatDrawerContainer, MatDrawerContent } from "@angular/material/sidenav";
import { MatIcon } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { NavigationSelfServiceComponent } from "../token/navigation-self-service/navigation-self-service.component";
import { RouterLink } from "@angular/router";
import { ClearableInputComponent } from "../shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "../shared/copy-button/copy-button.component";
import { ScrollToTopDirective } from "../shared/directives/app-scroll-to-top.directive";
import { KeywordFilterComponent } from "../shared/keyword-filter/keyword-filter.component";
import { AuditComponent } from "./audit.component";

@Component({
  selector: "app-audit-self-service",
  imports: [
    MatCardModule,
    KeywordFilterComponent,
    MatCell,
    MatFormField,
    FormsModule,
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
    CopyButtonComponent,
    RouterLink,
    MatDrawerContainer,
    MatDrawer,
    MatDrawerContent,
    MatButtonModule,
    MatIcon,
    NavigationSelfServiceComponent,
    ScrollToTopDirective,
    ClearableInputComponent
  ],
  templateUrl: "./audit.self-service.component.html",
  styleUrl: "./audit.component.scss"
})
export class AuditComponentSelfServiceComponent extends AuditComponent {
}
