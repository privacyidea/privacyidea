import { Component, computed } from "@angular/core";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { NAVIGATION_BLOCKING_DIALOG_CLASS } from "@constants/global.constants";
import { DialogAction } from "@models/dialog";

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
export interface SaveAndExitDialogData {
  title?: string;
  message?: string;
  saveButtonText?: string;
  discardButtonText?: string;
  allowSaveExit: boolean;
  saveExitDisabled: boolean;
}

export type SaveAndExitDialogResult = "discard" | "save-exit";

@Component({
  selector: "app-save-and-exit-dialog",
  host: { class: NAVIGATION_BLOCKING_DIALOG_CLASS },
  templateUrl: "./save-and-exit-dialog.component.html",
  styleUrls: ["./save-and-exit-dialog.component.scss"],
  standalone: true,
  imports: [DialogWrapperComponent]
})
export class SaveAndExitDialogComponent extends AbstractDialogComponent<
  SaveAndExitDialogData,
  SaveAndExitDialogResult
> {
  constructor() {
    super();
    this.dialogRef.disableClose = true;
  }

  actions = computed<DialogAction<SaveAndExitDialogResult>[]>(() => [
    {
      label: this.data.saveButtonText || $localize`Save`,
      value: "save-exit",
      type: "confirm",
      disabled: this.data.saveExitDisabled,
      hidden: !this.data.allowSaveExit
    },
    {
      label: this.data.discardButtonText || $localize`Discard`,
      value: "discard",
      type: "destruct",
      primary: true
    }
  ]);

  title = computed(() => this.data.title || $localize`Discard changes`);
  message = computed(
    () => this.data.message || $localize`You have unsaved changes. Do you want to save them before exiting?`
  );

  onAction(result: SaveAndExitDialogResult): void {
    this.dialogRef.close(result);
  }
}
