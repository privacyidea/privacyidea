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
import { Component, computed, inject, input, OnDestroy, OnInit, signal } from "@angular/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSelectModule } from "@angular/material/select";
import { DetailsEditRegistry } from "@components/shared/details-shared/details-edit-registry.service";
import { AutofocusDirective } from "@components/shared/directives/app-autofocus.directive";
import { EditableElement, EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  CONTAINER_STATE_OPTIONS,
  ContainerService,
  ContainerServiceInterface
} from "@services/container/container.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";

@Component({
  selector: "app-container-states-field",
  standalone: true,
  imports: [NgClass, MatFormFieldModule, MatSelectModule, AutofocusDirective, EditButtonsComponent],
  templateUrl: "./container-states-field.component.html",
  styleUrl: "./container-states-field.component.scss"
})
export class ContainerStatesFieldComponent implements OnInit, OnDestroy {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly registry = inject(DetailsEditRegistry);

  readonly states = input<string[]>([]);
  readonly blockEditing = input(false);

  protected readonly containerStateOptions = CONTAINER_STATE_OPTIONS;

  readonly isEditing = signal(false);
  readonly selectedStates = signal<string[]>([]);
  protected readonly editable = computed(() => this.authService.actionAllowed("container_state"));
  protected readonly shouldHideEdit = computed(() => this.blockEditing() && !this.isEditing());

  protected readonly editButtonsElement: EditableElement<string[]> = {
    keyMap: { key: "" },
    isEditing: this.isEditing,
    value: []
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

  protected onStatesChange(newStates: string[]): void {
    if (newStates.includes("active") && newStates.includes("disabled")) {
      const prev = this.selectedStates();
      const toRemove = prev.includes("active") ? "active" : "disabled";
      this.selectedStates.set(newStates.filter((state) => state !== toRemove));
    } else {
      this.selectedStates.set(newStates);
    }
  }

  protected readonly toggle = (): void => {
    if (!this.isEditing()) {
      this.selectedStates.set([...this.states()]);
    }
    this.isEditing.update((editing) => !editing);
  };

  protected readonly commit = (): void => {
    if (this.selectedStates().length === 0) {
      this.notificationService.error("At least one state must be selected.");
      return;
    }
    this.containerService
      .setStates(this.containerService.containerSerial(), this.selectedStates())
      .subscribe({ next: () => this.containerService.containerDetailsResource.reload() });
    this.isEditing.set(false);
  };

  protected readonly cancel = (): void => {
    this.selectedStates.set([...this.states()]);
    this.isEditing.set(false);
  };
}
