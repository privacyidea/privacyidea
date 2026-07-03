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
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatIconButton } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { DetailFieldRowComponent } from "@components/shared/details-shared/field-editing/detail-field-row/detail-field-row.component";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import { DetailsListDisplayComponent } from "@components/shared/details-shared/value-cells/details-list-display/details-list-display.component";
import { DetailsMultiSelectCellComponent } from "@components/shared/details-shared/value-cells/details-multi-select-cell/details-multi-select-cell.component";
import { injectEditableField } from "@components/shared/details-shared/field-editing/editable-field";
import { AutofocusDirective } from "@components/shared/directives/app-autofocus.directive";
import { EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
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
    DetailFieldRowComponent,
    DetailsListDisplayComponent,
    DetailsMultiSelectCellComponent,
    EditButtonsComponent,
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
    CopyButtonComponent
  ],
  templateUrl: "./token-details-assignments.component.html",
  styleUrl: "./token-details-assignments.component.scss"
})
export class TokenDetailsAssignmentsComponent {
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);

  readonly tokenDetails = input.required<TokenDetails>();
  readonly userRealm = input("");
  readonly isAnyEditingOrRevoked = input(false);
  readonly selfService = input(false);

  protected readonly containerSerial = computed(() => this.str(this.tokenDetails().container_serial));

  protected readonly selectedTokengroup = signal<string[]>([]);
  protected readonly tokengroupOptions = signal<string[]>([]);

  protected readonly realmOptions = computed(() =>
    this.realmService
      .realmOptions()
      .map((realm) => ({ value: realm, label: realm, disabled: realm === this.userRealm() }))
  );
  protected readonly tokengroupSelectOptions = computed(() =>
    this.tokengroupOptions().map((group) => ({ value: group, label: group, disabled: group === this.userRealm() }))
  );

  protected readonly realmsEditable = computed(() => this.authService.actionAllowed("tokenrealms"));
  protected readonly tokengroupEditable = computed(() => this.authService.actionAllowed("tokengroups"));
  protected readonly containerEditable = computed(() => this.authService.actionAllowed("container_add_token"));
  protected readonly containerCanRemove = computed(() => this.authService.actionAllowed("container_remove_token"));

  protected readonly realmsField = injectEditableField({
    onOpen: () => this.realmService.selectedRealms.set([...this.tokenDetails().realms]),
    onCancel: () => this.realmService.selectedRealms.set([...this.tokenDetails().realms]),
    onCommit: () => {
      this.tokenService
        .setTokenRealm(this.tokenDetails().serial, this.realmService.selectedRealms())
        .subscribe({ next: () => this.tokenService.tokenDetailResource.reload() });
    }
  });

  protected readonly tokengroupField = injectEditableField({
    onOpen: () => {
      this.selectedTokengroup.set([...(this.tokenDetails().tokengroup as unknown as string[])]);
      if (this.tokengroupOptions().length === 0) {
        this.tokenService.getTokengroups().subscribe({
          next: (response) => {
            this.tokengroupOptions.set(Object.keys(response.result?.value || {}));
          }
        });
      }
    },
    onCancel: () => this.selectedTokengroup.set([...(this.tokenDetails().tokengroup as unknown as string[])]),
    onCommit: () => {
      this.tokenService
        .setTokengroup(this.tokenDetails().serial, this.selectedTokengroup())
        .subscribe({ next: () => this.tokenService.tokenDetailResource.reload() });
    }
  });

  protected readonly containerField = injectEditableField({
    onOpen: () => this.containerService.selectedContainerSerial.set(""),
    onCancel: () => this.containerService.selectedContainerSerial.set(""),
    onCommit: () => {
      const selected = this.containerService.selectedContainerSerial()?.trim() ?? null;
      this.containerService.selectedContainerSerial.set(selected);
      if (selected) {
        this.containerService.addToken(this.tokenDetails().serial, selected).subscribe({
          next: () => this.tokenService.tokenDetailResource.reload()
        });
      }
    }
  });

  protected str(value: unknown): string {
    return value === null || value === undefined ? "" : String(value);
  }

  protected removeContainer(): void {
    const current = this.containerSerial();
    if (!current) {
      return;
    }
    this.containerService.removeToken(this.tokenDetails().serial, current).subscribe({
      next: () => {
        this.containerService.selectedContainerSerial.set("");
        this.tokenService.tokenDetailResource.reload();
      }
    });
  }
}
