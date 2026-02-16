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

import { CommonModule } from "@angular/common";
import { Component, computed, inject, signal } from "@angular/core";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { AuthServiceInterface, AuthService } from "../../../services/auth/auth.service";
import {
  ContainerTemplateServiceInterface,
  ContainerTemplateService
} from "../../../services/container-template/container-template.service";
import { ContainerTemplatesTableComponent } from "./container-templates-table/container-templates-table.component";
import { ContainerTemplatesFilterComponent } from "./container-templates-filter/container-templates-filter.component";
import { ContainerTemplatesTableActionsComponent } from "./container-templates-table-actions/container-templates-table-actions.component";
import { ContainerTemplate } from "../../../services/container/container.service";

@Component({
  selector: "app-container-templates",
  standalone: true,
  imports: [
    CommonModule,
    MatExpansionModule,
    MatIconModule,
    ContainerTemplatesTableComponent,
    ContainerTemplatesFilterComponent,
    ContainerTemplatesTableActionsComponent
  ],
  templateUrl: "./container-templates.component.html",
  styleUrl: "./container-templates.component.scss"
})
export class ContainerTemplatesComponent {
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);
  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly currentFilter = signal<string>("");
  readonly containerTemplates = this.containerTemplateService.templates;
  readonly filteredContainerTemplates = computed(() => {
    return this.containerTemplates().filter((template) => {
      // TODO: Use GenericFilter later
      return template.name.toLowerCase().includes(this.currentFilter().toLowerCase());
    });
  });
  readonly selectedContainerTemplates = signal<ContainerTemplate[]>([]);
}
