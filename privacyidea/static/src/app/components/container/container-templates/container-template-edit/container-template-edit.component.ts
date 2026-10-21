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

import { Component, computed, inject, input, linkedSignal, model, Signal, viewChild } from "@angular/core";
import { disabled, form, FormField, readonly, required, validate } from "@angular/forms/signals";
import { MatCardModule } from "@angular/material/card";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatListModule } from "@angular/material/list";
import { MatTooltipModule } from "@angular/material/tooltip";
import { TokenEnrollmentPayload } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { ToggleGroupComponent } from "@components/shared/toggle-group/toggle-group.component";

import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "@services/container-template/container-template.service";
import { ContainerTemplate } from "@services/container/container.service";
import { ERR, identifierName } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";
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
    FormField,
    ToggleGroupComponent,
    ContainerTemplateEditBodyComponent
  ],
  templateUrl: "./container-template-edit.component.html",
  styleUrl: "./container-template-edit.component.scss"
})
export class ContainerTemplateEditComponent {
  // An existing template keeps its name: containers are linked to the template, and saving under another name
  // would create a second template
  readonly nameEditable = input(true);
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
  // The empty string is the explicit "None" option, the container type of a template that has none yet.
  readonly containerTypeOptions = computed(() => ["", ...this.containerTypes()]);
  readonly containerTypeLabels = computed(() => [$localize`:@@common.none:None`, ...this.containerTypesTitleCase()]);
  readonly availableTokenTypes = computed(() =>
    this.containerTemplateService.getTokenTypesForContainerType(this.template().container_type)
  );

  readonly tokens = computed(() => this.template().template_options.tokens);
  readonly hasToken = computed(() => this.tokens().length > 0);

  readonly form = form(this.template, (f) => {
    identifierName(f.name);
    readonly(f.name, () => !this.nameEditable());
    validate(f.name, (ctx) => (this.isNameTaken(ctx.value()) ? [{ kind: ERR.nameTaken }] : []));
    required(f.container_type);
    disabled(f.container_type, () => this.hasToken());
    validate(f.template_options.tokens, (ctx) => (ctx.value().length > 0 ? [] : [{ kind: ERR.required }]));
  });

  // The template is saved only when this is true. The container type is a disabled field while tokens exist and is
  // then skipped by validation, so it is checked here as well.
  readonly canSave = computed(() => this.form().valid() && this.template().container_type !== "");
  readonly hasError = hasError;
  readonly ERR = ERR;

  // The name an existing template already has is not a conflict with itself.
  private isNameTaken(name: string): boolean {
    if (name === this.initTemplate().name) return false;
    return this.containerTemplateService.templates().some((t) => t.name === name);
  }

  editTemplate(templateUpdates: Partial<ContainerTemplate>) {
    this.template.set({ ...this.template(), ...templateUpdates });
  }
}
