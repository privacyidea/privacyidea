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
import { Component, Input, Signal, WritableSignal, output } from "@angular/core";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatFormField, MatLabel, MatSuffix } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";
import { ContainerRegistrationConfigComponent } from "@components/container/container-registration/container-registration-config/container-registration-config.component";
import { ContainerTemplateEditBodyComponent } from "@components/container/container-templates/container-template-edit/container-template-edit-body/container-template-edit-body.component";
import { AuthServiceInterface } from "@services/auth/auth.service";
import { ContainerServiceInterface, ContainerTemplate } from "@services/container/container.service";
import { TokenServiceInterface } from "@services/token/token.service";

@Component({
  selector: "app-container-create-form",
  standalone: true,
  imports: [
    MatFormField,
    MatLabel,
    MatInput,
    MatSelect,
    MatOption,
    MatCheckbox,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatSuffix,
    ClearButtonComponent,
    ContainerRegistrationConfigComponent,
    ContainerTemplateEditBodyComponent
  ],
  templateUrl: "./container-create-form.component.html"
})
export class ContainerCreateFormComponent {
  @Input({ required: true }) containerService!: ContainerServiceInterface;
  @Input({ required: true }) tokenService!: TokenServiceInterface;
  @Input({ required: true }) authService!: AuthServiceInterface;
  @Input({ required: true }) description!: WritableSignal<string>;
  @Input({ required: true }) selectedTemplate!: WritableSignal<ContainerTemplate>;
  @Input({ required: true }) templateOptions!: WritableSignal<ContainerTemplate[]>;
  @Input({ required: true }) generateQRCode!: WritableSignal<boolean>;
  @Input({ required: true }) passphrasePrompt!: WritableSignal<string>;
  @Input({ required: true }) passphraseResponse!: WritableSignal<string>;
  @Input({ required: true }) userStorePassphrase!: WritableSignal<boolean>;
  @Input({ required: true }) availableTokenTypes!: Signal<string[]>;
  @Input() showRegistration = false;
  @Input() containerHasOwner = false;
  @Input() templateFieldClass = "input-width-l";

  validInputChange = output<boolean>();
  clearTemplate = output<void>();
  templateChange = output<ContainerTemplate>();

  compareTemplates(t1: ContainerTemplate | null, t2: ContainerTemplate | null): boolean {
    return t1?.name === t2?.name;
  }

  clearTemplateSelection() {
    this.clearTemplate.emit();
  }

  get templateIsSelected(): boolean {
    return !!this.selectedTemplate?.()?.name;
  }
}
