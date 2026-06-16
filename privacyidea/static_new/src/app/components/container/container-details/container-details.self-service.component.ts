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
import { NgClass, NgTemplateOutlet } from "@angular/common";
import { Component } from "@angular/core";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatIconButton } from "@angular/material/button";
import { MatFormField } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatListItem } from "@angular/material/list";
import { MatSelectModule } from "@angular/material/select";
import { MatCell, MatColumnDef, MatTableModule } from "@angular/material/table";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { ContainerAddTokenComponent } from "@components/shared/container-add-token/container-add-token.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import { DetailsHeaderComponent } from "@components/shared/details-shared/details-header/details-header.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { MasonryDirective } from "@components/shared/directives/masonry/masonry.directive";
import { EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { ContainerDetailsActionsComponent } from "./container-details-actions/container-details-actions.component";
import { ContainerDetailsInfoComponent } from "./container-details-info/container-details-info.component";
import { ContainerDetailsTokenTableComponent } from "./container-details-token-table/container-details-token-table.component";
import { ContainerDetailsComponent } from "./container-details.component";

@Component({
  selector: "app-container-details-self-service",
  standalone: true,
  imports: [
    NgClass,
    NgTemplateOutlet,
    MatTableModule,
    MatCell,
    MatColumnDef,
    MatListItem,
    EditButtonsComponent,
    MatFormField,
    MatSelectModule,
    MatInput,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatIcon,
    MatIconButton,
    ContainerDetailsInfoComponent,
    ClearableInputComponent,
    CopyableComponent,
    ScrollToTopDirective,
    MasonryDirective,
    ContainerDetailsTokenTableComponent,
    ContainerDetailsActionsComponent,
    DetailsHeaderComponent,
    DetailsCardComponent,
    ContainerAddTokenComponent
  ],
  templateUrl: "./container-details.self-service.component.html",
  styleUrls: ["./container-details.component.scss"]
})
export class ContainerDetailsSelfServiceComponent extends ContainerDetailsComponent {}
