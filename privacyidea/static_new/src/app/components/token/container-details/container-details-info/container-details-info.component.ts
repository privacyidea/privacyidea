/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { Component, inject, Input, linkedSignal, Signal, WritableSignal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatIconButton } from "@angular/material/button";
import { MatDivider } from "@angular/material/divider";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatList, MatListItem } from "@angular/material/list";
import { MatCell, MatColumnDef, MatRow, MatTableModule } from "@angular/material/table";
import { forkJoin, Observable, switchMap } from "rxjs";
import { ContainerService, ContainerServiceInterface } from "../../../../services/container/container.service";
import { OverflowService, OverflowServiceInterface } from "../../../../services/overflow/overflow.service";
import { EditButtonsComponent } from "../../../shared/edit-buttons/edit-buttons.component";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";

export interface ContainerInfoDetail<T = any> {
  value: T;
  keyMap: { label: string; key: string };
  isEditing: WritableSignal<boolean>;
}

@Component({
  selector: "app-container-details-info",
  standalone: true,
  imports: [
    MatTableModule,
    MatColumnDef,
    MatCell,
    MatList,
    MatListItem,
    MatFormField,
    MatInput,
    FormsModule,
    MatIconButton,
    MatLabel,
    MatIcon,
    MatDivider,
    MatRow,
    EditButtonsComponent
  ],
  templateUrl: "./container-details-info.component.html",
  styleUrl: "./container-details-info.component.scss"
})
export class ContainerDetailsInfoComponent {
  private readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  protected readonly Object = Object;
  containerSerial = this.containerService.containerSerial;
  @Input() infoData!: WritableSignal<ContainerInfoDetail[]>;
  @Input() detailData!: WritableSignal<ContainerInfoDetail[]>;
  @Input() isAnyEditingOrRevoked!: Signal<boolean>;
  @Input() isEditingInfo!: WritableSignal<boolean>;
  @Input() isEditingUser!: WritableSignal<boolean>;
  newInfo: WritableSignal<{ key: string; value: string }> = linkedSignal({
    source: this.isEditingInfo,
    computation: () => {
      return { key: "", value: "" };
    }
  });

  toggleInfoEdit(): void {
    this.isEditingInfo.update((b) => !b);
    this.newInfo.set({ key: "", value: "" });
  }

  saveInfo(element: ContainerInfoDetail): void {
    if (this.newInfo().key.trim() !== "" && this.newInfo().value.trim() !== "") {
      element.value[this.newInfo().key] = this.newInfo().value;
    }
    const requests = this.containerService.setContainerInfos(this.containerSerial(), element.value);
    forkJoin(requests).subscribe({
      next: () => {
        this.newInfo.set({ key: "", value: "" });
        this.containerService.containerDetailResource.reload();
      }
    });
    this.isEditingInfo.set(false);
  }

  deleteInfo(key: string): void {
    this.containerService
      .deleteInfo(this.containerSerial(), key)
      .pipe(
        switchMap(() => {
          const info = this.detailData().find((detail) => detail.keyMap.key === "info");
          if (info) {
            this.isEditingInfo.set(true);
          }
          return new Observable<void>((observer) => {
            observer.next();
            observer.complete();
          });
        })
      )
      .subscribe({
        next: () => {
          this.containerService.containerDetailResource.reload();
        }
      });
  }
}
