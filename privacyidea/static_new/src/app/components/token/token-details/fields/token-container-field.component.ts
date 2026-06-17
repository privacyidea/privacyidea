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
import { Component, computed, inject, input, OnDestroy, OnInit, signal } from "@angular/core";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatIconButton } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatOption } from "@angular/material/core";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { DetailsEditRegistry } from "@components/shared/details-shared/details-edit-registry.service";
import { AutofocusDirective } from "@components/shared/directives/app-autofocus.directive";
import { EditableElement, EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

@Component({
  selector: "app-token-container-field",
  standalone: true,
  imports: [
    MatFormFieldModule,
    MatInput,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatOption,
    MatCheckbox,
    MatIcon,
    MatIconButton,
    AutofocusDirective,
    ClearableInputComponent,
    CopyableComponent,
    CopyButtonComponent,
    EditButtonsComponent
  ],
  templateUrl: "./token-container-field.component.html",
  styleUrl: "./token-container-field.component.scss"
})
export class TokenContainerFieldComponent implements OnInit, OnDestroy {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly registry = inject(DetailsEditRegistry);

  readonly container = input<string>("");
  readonly tokenHasUser = input(false);
  readonly blockEditing = input(false);
  readonly selfService = input(false);

  readonly isEditing = signal(false);
  protected readonly editable = computed(() => this.authService.actionAllowed("container_add_token"));
  protected readonly canRemove = computed(() => this.authService.actionAllowed("container_remove_token"));

  protected readonly editButtonsElement: EditableElement<string> = {
    keyMap: { key: "" },
    isEditing: this.isEditing,
    value: ""
  };

  private readonly handle = {
    isEditing: this.isEditing,
    save: () => this.commit(),
    cancel: () => this.cancel()
  };

  ngOnInit(): void {
    this.registry.register(this.handle);
  }

  ngOnDestroy(): void {
    this.registry.unregister(this.handle);
  }

  protected readonly toggle = (): void => {
    if (!this.isEditing()) {
      this.containerService.selectedContainerSerial.set("");
    }
    this.isEditing.update((editing) => !editing);
  };

  protected readonly commit = (): void => {
    const selected = this.containerService.selectedContainerSerial()?.trim() ?? null;
    this.containerService.selectedContainerSerial.set(selected);
    if (selected) {
      this.containerService.addToken(this.tokenService.tokenSerial(), selected).subscribe({
        next: () => this.tokenService.tokenDetailResource.reload()
      });
    }
    this.isEditing.set(false);
  };

  protected readonly cancel = (): void => {
    this.containerService.selectedContainerSerial.set("");
    this.isEditing.set(false);
  };

  protected remove(): void {
    const current = this.container();
    if (!current) {
      return;
    }
    this.containerService.removeToken(this.tokenService.tokenSerial(), current).subscribe({
      next: () => {
        this.containerService.selectedContainerSerial.set("");
        this.tokenService.tokenDetailResource.reload();
      }
    });
  }
}
