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

import { Component, signal } from "@angular/core";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";

export interface ConditionalAccessDryRunOffDialogData {
  policyName: string;
}

// Whether the failure counters accumulated during the trial are cleared once the policy starts
// enforcing (the default), or kept so it enforces immediately against what the trial already
// recorded. undefined means the dialog was cancelled and dry run must stay on.
export type ConditionalAccessDryRunOffDialogResult = { resetCounters: boolean } | undefined;

@Component({
  selector: "app-conditional-access-dry-run-off-dialog",
  imports: [DialogWrapperComponent, MatCheckboxModule],
  template: `
    <app-dialog-wrapper
      [title]="title"
      (wrapperClose)="cancel()"
      [actions]="actions"
      [showCloseButton]="true"
      (actionTriggered)="confirm()">
      <div class="margin-right-16">
        <p i18n>
          Turning dry run off starts enforcing "{{ data.policyName }}" immediately. By default the
          failure counters from the trial are reset, so the policy is judged only on failures from
          now on.
        </p>
        <mat-checkbox [checked]="keepCounters()" (change)="keepCounters.set($event.checked)">
          <span i18n>Keep the counters accumulated during the trial</span>
        </mat-checkbox>
      </div>
    </app-dialog-wrapper>
  `
})
export class ConditionalAccessDryRunOffDialogComponent extends AbstractDialogComponent<
  ConditionalAccessDryRunOffDialogData,
  ConditionalAccessDryRunOffDialogResult
> {
  title = $localize`Disable Dry Run`;
  keepCounters = signal(false);

  actions: DialogAction<void>[] = [{ label: $localize`Disable Dry Run`, value: undefined, type: "confirm", primary: true }];

  confirm(): void {
    this.close({ resetCounters: !this.keepCounters() });
  }

  cancel(): void {
    this.close(undefined);
  }
}
