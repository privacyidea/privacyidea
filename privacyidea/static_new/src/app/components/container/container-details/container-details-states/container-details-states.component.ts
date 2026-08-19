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
import { NgClass } from "@angular/common";
import { Component, computed, inject, input, signal } from "@angular/core";
import { DetailFieldRowComponent } from "@components/shared/details-shared/field-editing/detail-field-row/detail-field-row.component";
import { injectEditableField } from "@components/shared/details-shared/field-editing/editable-field";
import { DetailsMultiSelectCellComponent } from "@components/shared/details-shared/value-cells/details-multi-select-cell/details-multi-select-cell.component";
import { EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  CONTAINER_STATE_OPTIONS,
  ContainerService,
  ContainerServiceInterface
} from "@services/container/container.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";

@Component({
  selector: "app-container-details-states",
  standalone: true,
  imports: [NgClass, EditButtonsComponent, DetailFieldRowComponent, DetailsMultiSelectCellComponent],
  templateUrl: "./container-details-states.component.html",
  styleUrl: "./container-details-states.component.scss"
})
export class ContainerDetailsStatesComponent {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  readonly states = input<string[]>([]);
  readonly blockEditing = input(false);

  protected readonly containerStateOptions = CONTAINER_STATE_OPTIONS;

  readonly selectedStates = signal<string[]>([]);
  protected readonly editable = computed(() => this.authService.actionAllowed("container_state"));

  protected readonly field = injectEditableField({
    onOpen: () => this.selectedStates.set([...this.states()]),
    onCancel: () => this.selectedStates.set([...this.states()]),
    onCommit: async () => {
      if (this.selectedStates().length === 0) {
        this.notificationService.error("At least one state must be selected.");
        return false;
      }
      this.containerService
        .setStates(this.containerService.containerSerial(), this.selectedStates())
        .subscribe({ next: () => this.containerService.containerDetailsResource.reload() });
      return true;
    }
  });

  protected onStatesChange(newStates: string[]): void {
    if (newStates.includes("active") && newStates.includes("disabled")) {
      const prev = this.selectedStates();
      const toRemove = prev.includes("active") ? "active" : "disabled";
      this.selectedStates.set(newStates.filter((state) => state !== toRemove));
    } else {
      this.selectedStates.set(newStates);
    }
  }
}
