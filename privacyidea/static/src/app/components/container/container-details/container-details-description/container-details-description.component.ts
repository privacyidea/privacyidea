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
import { Component, computed, inject, input, signal } from "@angular/core";
import { form, FormField } from "@angular/forms/signals";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import { injectEditableField } from "@components/shared/details-shared/field-editing/editable-field";
import { EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "@services/container/container.service";

@Component({
  selector: "app-container-details-description",
  standalone: true,
  imports: [MatFormFieldModule, MatInput, FormField, DetailsCardComponent, EditButtonsComponent],
  templateUrl: "./container-details-description.component.html",
  styleUrl: "./container-details-description.component.scss"
})
export class ContainerDetailsDescriptionComponent {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  readonly description = input("");
  readonly blockEditing = input(false);

  protected readonly editable = computed(() => this.authService.actionAllowed("container_description"));

  /** The text being edited; the shown description stays untouched until the save has been reloaded. */
  protected readonly draft = signal("");
  protected readonly descriptionForm = form(this.draft);

  protected readonly field = injectEditableField({
    valid: computed(() => this.descriptionForm().valid()),
    onOpen: () => this.descriptionForm().reset(this.description()),
    onCommit: async () => {
      this.containerService
        .setContainerDescription(this.containerService.containerSerial(), this.draft())
        .subscribe({ next: () => this.containerService.containerDetailsResource.reload() });
    }
  });
}
