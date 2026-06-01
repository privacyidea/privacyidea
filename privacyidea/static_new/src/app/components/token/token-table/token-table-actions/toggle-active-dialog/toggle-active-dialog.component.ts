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

import { Component } from "@angular/core";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";

export type ToggleActiveAction = "toggle" | "activate" | "deactivate";

export interface ToggleActiveDialogData {
  items: { serial: string; active: boolean }[];
}

@Component({
  selector: "app-toggle-active-dialog",
  imports: [DialogWrapperComponent],
  template: `
    <app-dialog-wrapper
      title="(De)activate Selected Tokens"
      i18n-title
      (close)="close()"
      [actions]="actions"
      [showCancelButton]="true"
      (action)="onAction($event)">
      <div class="margin-right-16">
        <p i18n>The following tokens will be toggled:</p>
        <ul>
          @for (item of data.items; track item.serial) {
            <li>{{ item.serial }} ({{ item.active ? activeToInactive : inactiveToActive }})</li>
          }
        </ul>
      </div>
    </app-dialog-wrapper>
  `
})
export class ToggleActiveDialogComponent extends AbstractDialogComponent<ToggleActiveDialogData, ToggleActiveAction> {
  activeToInactive = $localize`active` + " → " + $localize`inactive`;
  inactiveToActive = $localize`inactive` + " → " + $localize`active`;
  actions: DialogAction<ToggleActiveAction>[] = [
    { label: $localize`Activate`, value: "activate", type: "confirm", primary: false },
    { label: $localize`Deactivate`, value: "deactivate", type: "destruct", primary: false },
    { label: $localize`Toggle`, value: "toggle", type: "confirm", primary: true }
  ];

  onAction(value: ToggleActiveAction): void {
    this.close(value);
  }
}
