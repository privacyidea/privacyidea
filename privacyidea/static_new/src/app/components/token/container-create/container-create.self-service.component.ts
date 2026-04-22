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
import { Component, computed } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatDialog } from "@angular/material/dialog";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelTitle,
  MatExpansionPanelHeader
} from "@angular/material/expansion";
import { MatIcon } from "@angular/material/icon";
import { MatFormField, MatInput, MatLabel, MatSuffix } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatTooltip } from "@angular/material/tooltip";
import { ClearButtonComponent } from "../../shared/clear-button/clear-button.component";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { ContainerRegistrationConfigComponent } from "../container-registration/container-registration-config/container-registration-config.component";
import { ContainerCreateComponent } from "./container-create.component";

@Component({
  selector: "app-container-create-self-service",
  imports: [
    MatButton,
    MatFormField,
    MatIcon,
    MatOption,
    MatSelect,
    FormsModule,
    MatInput,
    MatLabel,
    MatCheckbox,
    MatIconButton,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelTitle,
    MatExpansionPanelHeader,
    MatTooltip,
    ScrollToTopDirective,
    NgClass,
    ContainerRegistrationConfigComponent,
    ClearButtonComponent,
    MatSuffix
  ],
  templateUrl: "./container-create.self-service.component.html",
  styleUrl: "./container-create.component.scss"
})
export class ContainerCreateSelfServiceComponent extends ContainerCreateComponent {
  constructor(registrationDialog: MatDialog) {
    super(registrationDialog);
  }

  override userSelected = computed(() => true);
}
