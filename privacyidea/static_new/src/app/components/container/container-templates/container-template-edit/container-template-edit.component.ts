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

import { Component, computed, inject, linkedSignal, model, Signal, viewChild } from "@angular/core";
import { MatCardModule } from "@angular/material/card";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatListModule } from "@angular/material/list";
import { MatTooltipModule } from "@angular/material/tooltip";
import { TokenEnrollmentPayload } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { SelectorButtonsComponent } from "@components/policies/policy-edit-page/policy-panels/edit-action-tab/selector-buttons/selector-buttons.component";

import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "@services/container-template/container-template.service";
import { ContainerTemplate } from "@services/container/container.service";
import { ContainerTemplateEditBodyComponent } from "./container-template-edit-body/container-template-edit-body.component";

@Component({
  selector: "app-container-template-edit",
  standalone: true,
  imports: [
    MatInputModule,
    MatCardModule,
    MatIconModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatListModule,
    MatCheckboxModule,
    SelectorButtonsComponent,
    ContainerTemplateEditBodyComponent
  ],
  templateUrl: "./container-template-edit.component.html",
  styleUrl: "./container-template-edit.component.scss"
})
export class ContainerTemplateEditComponent {
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);

  private readonly editBody = viewChild(ContainerTemplateEditBodyComponent);

  // Called by the page at save time. Returns null if any token row's strategy form is invalid.
  collectTokens(): TokenEnrollmentPayload[] | null {
    const body = this.editBody();
    if (!body) return null;
    return body.collectTokens();
  }

  scrollToFirstInvalid(): void {
    this.editBody()?.scrollToFirstInvalid();
  }

  readonly template = model<ContainerTemplate>({
    container_type: "",
    name: "",
    template_options: {
      tokens: []
    },
    default: false
  });

  readonly initTemplate: Signal<ContainerTemplate> = linkedSignal({
    source: this.template,
    computation: (template, previous) => {
      if (previous?.value) return previous.value;
      return template;
    }
  });

  readonly containerTypes = computed(() => this.containerTemplateService.availableContainerTypes());
  readonly containerTypesTitleCase = computed(() =>
    this.containerTemplateService.availableContainerTypes().map((type) => type.charAt(0).toUpperCase() + type.slice(1))
  );
  readonly availableTokenTypes = computed(() =>
    this.containerTemplateService.getTokenTypesForContainerType(this.template().container_type)
  );

  readonly tokens = computed(() => this.template().template_options.tokens);
  readonly hasToken = computed(() => this.tokens().length > 0);

  readonly nameConflict = computed(() => {
    if (this.template().name == this.initTemplate().name) {
      return false;
    }
    return this.containerTemplateService.templates().some((t) => t.name === this.template().name);
  });
  readonly canSaveTemplate = computed<boolean>(() => {
    return this.containerTemplateService.canSaveTemplate(this.template()) && !this.nameConflict();
  });
  readonly nameErrorMatcher = {
    isErrorState: () => this.nameConflict()
  };

  editTemplate(templateUpdates: Partial<ContainerTemplate>) {
    this.template.set({ ...this.template(), ...templateUpdates });
  }
}
