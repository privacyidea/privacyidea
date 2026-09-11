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
  // One name shows inline in the sentence; more than one lists each on its own line instead
  // (the single-name case reads worse in list form for the common single-policy toggle).
  policyNames: string[];
}

// Whether the policy starts counting from the moment it begins enforcing (the default), or counts
// its full time window straight away, including the events already in it. undefined means the
// dialog was cancelled and dry run must stay on.
export type ConditionalAccessDryRunOffDialogResult = { resetCounters: boolean } | undefined;

@Component({
  selector: "app-conditional-access-dry-run-off-dialog",
  imports: [DialogWrapperComponent, MatCheckboxModule],
  templateUrl: "conditional-access-dry-run-off-dialog.component.html",
  styleUrl: "conditional-access-dry-run-off-dialog.component.scss"
})
export class ConditionalAccessDryRunOffDialogComponent extends AbstractDialogComponent<
  ConditionalAccessDryRunOffDialogData,
  ConditionalAccessDryRunOffDialogResult
> {
  title = $localize`Disable Dry Run`;
  countPastEvents = signal(false);

  actions: DialogAction<void>[] = [
    { label: $localize`Disable Dry Run`, value: undefined, type: "confirm", primary: true }
  ];

  confirm(): void {
    this.close({ resetCounters: !this.countPastEvents() });
  }

  cancel(): void {
    this.close(undefined);
  }
}
