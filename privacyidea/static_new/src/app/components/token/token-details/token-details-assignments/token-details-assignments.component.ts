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
import { MatOption } from "@angular/material/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import { DetailsEditRegistry } from "@components/shared/details-shared/details-edit-registry.service";
import { DetailsListDisplayComponent } from "@components/shared/details-shared/details-shared.components";
import { AutofocusDirective } from "@components/shared/directives/app-autofocus.directive";
import { EditableElement, EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { TokenDetails, TokenService, TokenServiceInterface } from "@services/token/token.service";

@Component({
  selector: "app-token-details-assignments",
  standalone: true,
  imports: [
    DetailsCardComponent,
    DetailsListDisplayComponent,
    EditButtonsComponent,
    MatFormFieldModule,
    MatSelectModule,
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
    CopyButtonComponent
  ],
  templateUrl: "./token-details-assignments.component.html",
  styleUrl: "./token-details-assignments.component.scss"
})
export class TokenDetailsAssignmentsComponent implements OnInit, OnDestroy {
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly registry = inject(DetailsEditRegistry);

  readonly tokenDetails = input.required<TokenDetails>();
  readonly userRealm = input("");
  readonly isAnyEditingOrRevoked = input(false);
  readonly selfService = input(false);

  protected readonly containerSerial = computed(() => this.str(this.tokenDetails().container_serial));

  protected readonly realmsIsEditing = signal(false);
  protected readonly tokengroupIsEditing = signal(false);
  protected readonly containerIsEditing = signal(false);

  protected readonly selectedTokengroup = signal<string[]>([]);
  protected readonly tokengroupOptions = signal<string[]>([]);

  protected readonly realmsEditable = computed(() => this.authService.actionAllowed("tokenrealms"));
  protected readonly tokengroupEditable = computed(() => this.authService.actionAllowed("tokengroups"));
  protected readonly containerEditable = computed(() => this.authService.actionAllowed("container_add_token"));
  protected readonly containerCanRemove = computed(() => this.authService.actionAllowed("container_remove_token"));

  protected readonly realmsEditButtonsElement: EditableElement<string[]> = {
    keyMap: { key: "" },
    isEditing: this.realmsIsEditing,
    value: []
  };
  protected readonly tokengroupEditButtonsElement: EditableElement<string[]> = {
    keyMap: { key: "" },
    isEditing: this.tokengroupIsEditing,
    value: []
  };
  protected readonly containerEditButtonsElement: EditableElement<string> = {
    keyMap: { key: "" },
    isEditing: this.containerIsEditing,
    value: ""
  };

  private readonly realmsHandle = {
    isEditing: this.realmsIsEditing,
    save: () => this.commitRealms(),
    cancel: () => this.cancelRealms()
  };
  private readonly tokengroupHandle = {
    isEditing: this.tokengroupIsEditing,
    save: () => this.commitTokengroup(),
    cancel: () => this.cancelTokengroup()
  };
  private readonly containerHandle = {
    isEditing: this.containerIsEditing,
    save: () => this.commitContainer(),
    cancel: () => this.cancelContainer()
  };

  ngOnInit(): void {
    this.registry.register(this.realmsHandle);
    this.registry.register(this.tokengroupHandle);
    this.registry.register(this.containerHandle);
  }

  ngOnDestroy(): void {
    this.registry.unregister(this.realmsHandle);
    this.registry.unregister(this.tokengroupHandle);
    this.registry.unregister(this.containerHandle);
  }

  protected str(value: unknown): string {
    return value === null || value === undefined ? "" : String(value);
  }

  protected readonly toggleRealms = (): void => {
    if (!this.realmsIsEditing()) {
      this.realmService.selectedRealms.set([...this.tokenDetails().realms]);
    }
    this.realmsIsEditing.update((editing) => !editing);
  };

  protected readonly commitRealms = (): void => {
    this.tokenService
      .setTokenRealm(this.tokenService.tokenSerial(), this.realmService.selectedRealms())
      .subscribe({ next: () => this.tokenService.tokenDetailResource.reload() });
    this.realmsIsEditing.set(false);
  };

  protected readonly cancelRealms = (): void => {
    this.realmService.selectedRealms.set([...this.tokenDetails().realms]);
    this.realmsIsEditing.set(false);
  };

  protected readonly toggleTokengroup = (): void => {
    if (!this.tokengroupIsEditing()) {
      this.selectedTokengroup.set([...(this.tokenDetails().tokengroup as unknown as string[])]);
      if (this.tokengroupOptions().length === 0) {
        this.tokenService.getTokengroups().subscribe({
          next: (response) => {
            this.tokengroupOptions.set(Object.keys(response.result?.value || {}));
          }
        });
      }
    }
    this.tokengroupIsEditing.update((editing) => !editing);
  };

  protected readonly commitTokengroup = (): void => {
    this.tokenService
      .setTokengroup(this.tokenService.tokenSerial(), this.selectedTokengroup())
      .subscribe({ next: () => this.tokenService.tokenDetailResource.reload() });
    this.tokengroupIsEditing.set(false);
  };

  protected readonly cancelTokengroup = (): void => {
    this.selectedTokengroup.set([...(this.tokenDetails().tokengroup as unknown as string[])]);
    this.tokengroupIsEditing.set(false);
  };

  protected readonly toggleContainer = (): void => {
    if (!this.containerIsEditing()) {
      this.containerService.selectedContainerSerial.set("");
    }
    this.containerIsEditing.update((editing) => !editing);
  };

  protected readonly commitContainer = (): void => {
    const selected = this.containerService.selectedContainerSerial()?.trim() ?? null;
    this.containerService.selectedContainerSerial.set(selected);
    if (selected) {
      this.containerService.addToken(this.tokenService.tokenSerial(), selected).subscribe({
        next: () => this.tokenService.tokenDetailResource.reload()
      });
    }
    this.containerIsEditing.set(false);
  };

  protected readonly cancelContainer = (): void => {
    this.containerService.selectedContainerSerial.set("");
    this.containerIsEditing.set(false);
  };

  protected removeContainer(): void {
    const current = this.containerSerial();
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
