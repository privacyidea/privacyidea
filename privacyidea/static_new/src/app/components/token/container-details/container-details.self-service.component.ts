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
import { NgClass } from "@angular/common";
import { Component } from "@angular/core";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatIconButton } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatDivider } from "@angular/material/divider";
import { MatFormField } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatListItem } from "@angular/material/list";
import { MatPaginator } from "@angular/material/paginator";
import { MatSelectModule } from "@angular/material/select";
import { MatCell, MatColumnDef, MatTableModule } from "@angular/material/table";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "../../shared/copy-button/copy-button.component";
import { EditButtonsComponent } from "../../shared/edit-buttons/edit-buttons.component";
import { ContainerDetailsInfoComponent } from "./container-details-info/container-details-info.component";
import { ContainerDetailsComponent } from "./container-details.component";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { ContainerDetailsTokenTableComponent } from "./container-details-token-table/container-details-token-table.component";
import { ContainerDetailsActionsComponent } from "./container-details-actions/container-details-actions.component";
import { ContainerDetailsTokenActionsComponent } from "./container-details-token-actions/container-details-token-actions.component";
import { RouterLink } from "@angular/router";
import { MatTooltip } from "@angular/material/tooltip";

@Component({
  selector: "app-container-details-self-service",
  standalone: true,
  imports: [
    NgClass,
    MatTableModule,
    MatCell,
    MatColumnDef,
    ReactiveFormsModule,
    MatListItem,
    EditButtonsComponent,
    MatFormField,
    FormsModule,
    MatSelectModule,
    MatInput,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatIcon,
    MatIconButton,
    ContainerDetailsInfoComponent,
    MatPaginator,
    MatDivider,
    MatCheckbox,
    CopyButtonComponent,
    ClearableInputComponent,
    ScrollToTopDirective,
    ContainerDetailsTokenTableComponent,
    ContainerDetailsActionsComponent,
    ContainerDetailsTokenActionsComponent,
    RouterLink,
    MatTooltip
  ],
  templateUrl: "./container-details.self-service.component.html",
  styleUrls: ["./container-details.component.scss"]
})
export class ContainerDetailsSelfServiceComponent extends ContainerDetailsComponent {
}
