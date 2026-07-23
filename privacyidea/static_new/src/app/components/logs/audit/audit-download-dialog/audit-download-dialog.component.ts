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

@Component({
  selector: "app-audit-download-dialog",
  templateUrl: "./audit-download-dialog.component.html",
  styleUrl: "./audit-download-dialog.component.scss",
  standalone: true,
  imports: [DialogWrapperComponent]
})
export class AuditDownloadDialogComponent extends AbstractDialogComponent<void, boolean> {
  action: DialogAction<true> = {
    label: $localize`Proceed`,
    value: true,
    type: "confirm",
    primary: true
  };

  onAction(value: boolean) {
    this.close(value);
  }
}
