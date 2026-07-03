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
import { DetailFieldRowComponent } from "@components/shared/details-shared/field-editing/detail-field-row/detail-field-row.component";
import { injectEditableField } from "@components/shared/details-shared/field-editing/editable-field";
import { DetailsListDisplayComponent } from "@components/shared/details-shared/value-cells/details-list-display/details-list-display.component";
import { DetailsMultiSelectCellComponent } from "@components/shared/details-shared/value-cells/details-multi-select-cell/details-multi-select-cell.component";
import { EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "@services/container/container.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";

@Component({
  selector: "app-container-details-realms",
  standalone: true,
  imports: [
    DetailFieldRowComponent,
    DetailsMultiSelectCellComponent,
    DetailsListDisplayComponent,
    EditButtonsComponent
  ],
  templateUrl: "./container-details-realms.component.html",
  styleUrl: "./container-details-realms.component.scss"
})
export class ContainerDetailsRealmsComponent {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  readonly realms = input<string[]>([]);
  readonly userRealm = input<string>("");
  readonly blockEditing = input(false);

  readonly selectedRealms = signal<string[]>([]);
  protected readonly editable = computed(() => this.authService.actionAllowed("container_realms"));
  protected readonly realmOptions = computed(() =>
    this.realmService
      .realmOptions()
      .map((realm) => ({ value: realm, label: realm, disabled: realm === this.userRealm() }))
  );

  protected readonly field = injectEditableField({
    onOpen: () => this.selectedRealms.set([...this.realms()]),
    onCancel: () => this.selectedRealms.set([...this.realms()]),
    onCommit: () => {
      this.containerService
        .setContainerRealm(this.containerService.containerSerial(), this.selectedRealms())
        .subscribe({ next: () => this.containerService.containerDetailsResource.reload() });
    }
  });
}
