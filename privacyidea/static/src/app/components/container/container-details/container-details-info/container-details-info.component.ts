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
import { Component, computed, inject, input, linkedSignal, model, WritableSignal } from "@angular/core";
import { form, FormField } from "@angular/forms/signals";
import { MatIconButton } from "@angular/material/button";
import { MatDivider } from "@angular/material/divider";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import {
  INFO_KEY_EXISTS,
  InfoEntry,
  infoEntryRules
} from "@components/shared/details-shared/field-editing/info-entry.rules";
import { EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "@services/container/container.service";
import { ERR } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";
import { forkJoin, Observable, switchMap } from "rxjs";

export interface ContainerInfoDetail<T = unknown> {
  value: T;
  keyMap: { label: string; key: string };
  isEditing: WritableSignal<boolean>;
}

@Component({
  selector: "app-container-details-info",
  standalone: true,
  imports: [
    MatFormFieldModule,
    MatInput,
    FormField,
    MatIconButton,
    MatIcon,
    MatDivider,
    EditButtonsComponent
  ],
  templateUrl: "./container-details-info.component.html",
  styleUrl: "./container-details-info.component.scss"
})
export class ContainerDetailsInfoComponent {
  private readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  protected readonly Object = Object;
  protected readonly hasError = hasError;
  protected readonly ERR = ERR;
  protected readonly INFO_KEY_EXISTS = INFO_KEY_EXISTS;
  private readonly hiddenInfoKeys = ["registration_state"];
  containerSerial = this.containerService.containerSerial;
  infoData = input.required<ContainerInfoDetail[]>();
  detailData = input.required<ContainerInfoDetail[]>();
  isAnyEditingOrRevoked = input.required<boolean>();
  isEditingInfo = model.required<boolean>();
  isEditingUser = input.required<boolean>();
  newInfo: WritableSignal<InfoEntry> = linkedSignal({
    source: this.isEditingInfo,
    computation: () => {
      return { key: "", value: "" };
    }
  });
  protected readonly newInfoForm = form(this.newInfo, (path) => {
    infoEntryRules(path, () => Object.keys(this.asMap(this.infoData()[0]?.value)));
  });
  /** Whether the entries may be saved: the "add" row is empty or complete and names a new key. */
  readonly canSave = computed(() => !this.isEditingInfo() || this.newInfoForm().valid());
  /** The info element for the edit buttons, which disable Save while the "add" row is incomplete. */
  protected readonly editButtonsElement = computed(() => {
    const element = this.infoData()[0] as ContainerInfoDetail<Record<string, string>> | undefined;
    return element ? { ...element, valid: this.canSave } : undefined;
  });

  protected asMap(value: unknown): Record<string, string> {
    return (value ?? {}) as Record<string, string>;
  }

  displayInfoKeys(value: Record<string, unknown>): string[] {
    return Object.keys(value).filter((key) => !this.hiddenInfoKeys.includes(key));
  }

  toggleInfoEdit(): void {
    this.isEditingInfo.update((b) => !b);
    this.newInfoForm().reset({ key: "", value: "" });
  }

  saveInfo(element: ContainerInfoDetail<Record<string, string>>): void {
    if (!this.canSave()) {
      this.newInfoForm.key().markAsTouched();
      this.newInfoForm.value().markAsTouched();
      return;
    }
    const { key, value } = this.newInfo();
    if (key.trim() !== "" && value.trim() !== "") {
      element.value[key.trim()] = value;
    }
    const requests = this.containerService.setContainerInfos(this.containerSerial(), element.value);
    forkJoin(requests).subscribe({
      next: () => {
        this.newInfoForm().reset({ key: "", value: "" });
        this.containerService.containerDetailsResource.reload();
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
          this.containerService.containerDetailsResource.reload();
        }
      });
  }
}
