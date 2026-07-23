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

// Mirrors the token table's (De)activate action: turn every selected item on,
// off, or flip each relative to its own current state.
export type ConditionalAccessToggleAction = "toggle" | "activate" | "deactivate";

export interface ConditionalAccessToggleDialogData {
  title: string;
  intro: string;
  // Word shown for the two states, e.g. "enabled" / "disabled".
  onWord: string;
  offWord: string;
  items: { label: string; state: boolean }[];
}

@Component({
  selector: "app-conditional-access-toggle-dialog",
  imports: [DialogWrapperComponent],
  template: `
    <app-dialog-wrapper
      [title]="data.title"
      (wrapperClose)="close()"
      [actions]="actions"
      [showCancelButton]="true"
      (actionTriggered)="onAction($event)">
      <div class="margin-right-16">
        <p>{{ data.intro }}</p>
        <ul>
          @for (item of data.items; track item.label) {
            <li>{{ item.label }} ({{ item.state ? onToOff : offToOn }})</li>
          }
        </ul>
      </div>
    </app-dialog-wrapper>
  `
})
export class ConditionalAccessToggleDialogComponent extends AbstractDialogComponent<
  ConditionalAccessToggleDialogData,
  ConditionalAccessToggleAction
> {
  get onToOff(): string {
    return this.data.onWord + " → " + this.data.offWord;
  }

  get offToOn(): string {
    return this.data.offWord + " → " + this.data.onWord;
  }

  actions: DialogAction<ConditionalAccessToggleAction>[] = [
    { label: $localize`Activate`, value: "activate", type: "confirm", primary: false },
    { label: $localize`Deactivate`, value: "deactivate", type: "destruct", primary: false },
    { label: $localize`Toggle`, value: "toggle", type: "confirm", primary: true }
  ];

  onAction(value: ConditionalAccessToggleAction): void {
    this.close(value);
  }
}
