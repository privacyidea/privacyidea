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
import { form, FormField, maxLength } from "@angular/forms/signals";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import { injectEditableField } from "@components/shared/details-shared/field-editing/editable-field";
import { AutofocusDirective } from "@components/shared/directives/app-autofocus.directive";
import { EditableElement, EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { ERR } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";

@Component({
  selector: "app-token-details-description",
  standalone: true,
  imports: [MatInput, MatFormFieldModule, FormField, AutofocusDirective, EditButtonsComponent, DetailsCardComponent],
  templateUrl: "./token-details-description.component.html",
  styleUrl: "./token-details-description.component.scss"
})
export class TokenDetailsDescriptionComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly hasError = hasError;
  protected readonly ERR = ERR;

  readonly element = input.required<EditableElement<string>>();
  readonly editable = input(false);
  readonly isAnyEditingOrRevoked = input(false);
  readonly selfService = input(false);

  /** The text being edited; the shown description stays untouched until the save has been reloaded. */
  protected readonly draft = signal("");
  protected readonly descriptionForm = form(this.draft, (f) => {
    maxLength(f, this.tokenService.maxDescriptionLength);
  });

  protected readonly field = injectEditableField({
    valid: computed(() => this.descriptionForm().valid()),
    onOpen: () => this.descriptionForm().reset(this.element().value ?? ""),
    onInvalid: () => this.descriptionForm().markAsTouched(),
    onCommit: async () => {
      this.tokenService
        .saveTokenDetail(this.tokenService.tokenSerial(), this.element().keyMap.key, this.draft())
        .subscribe({ next: () => this.tokenService.tokenDetailResource.reload() });
    }
  });
}
