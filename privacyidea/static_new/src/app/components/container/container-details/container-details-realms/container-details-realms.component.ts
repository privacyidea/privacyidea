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
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatListItem } from "@angular/material/list";
import { MatSelectModule } from "@angular/material/select";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { DetailsEditRegistry } from "@components/shared/details-shared/details-edit-registry.service";
import { AutofocusDirective } from "@components/shared/directives/app-autofocus.directive";
import { EditableElement, EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "@services/container/container.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";

@Component({
  selector: "app-container-details-realms",
  standalone: true,
  imports: [
    MatFormFieldModule,
    MatSelectModule,
    MatListItem,
    AutofocusDirective,
    CopyableComponent,
    EditButtonsComponent
  ],
  templateUrl: "./container-details-realms.component.html",
  styleUrl: "./container-details-realms.component.scss"
})
export class ContainerDetailsRealmsComponent implements OnInit, OnDestroy {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly registry = inject(DetailsEditRegistry);

  readonly realms = input<string[]>([]);
  readonly userRealm = input<string>("");
  readonly blockEditing = input(false);

  readonly isEditing = signal(false);
  readonly selectedRealms = signal<string[]>([]);
  protected readonly editable = computed(() => this.authService.actionAllowed("container_realms"));

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

  protected readonly toggle = (): void => {
    if (!this.isEditing()) {
      this.selectedRealms.set([...this.realms()]);
    }
    this.isEditing.update((editing) => !editing);
  };

  protected readonly commit = (): void => {
    this.containerService
      .setContainerRealm(this.containerService.containerSerial(), this.selectedRealms())
      .subscribe({ next: () => this.containerService.containerDetailsResource.reload() });
    this.isEditing.set(false);
  };

  protected readonly cancel = (): void => {
    this.selectedRealms.set([...this.realms()]);
    this.isEditing.set(false);
  };
}
