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
  selector: "app-free-tier-dialog",
  standalone: true,
  imports: [DialogWrapperComponent],
  templateUrl: "./free-tier-dialog.component.html",
  styleUrl: "./free-tier-dialog.component.scss"
})
export class FreeTierDialogComponent extends AbstractDialogComponent<void, void> {
  readonly dialogTitle = $localize`:@@welcome.addedValuePrivacyidea:The added value of privacyIDEA Enterprise Edition`;
  readonly dialogActions: DialogAction<"okay">[] = [
    {
      type: "confirm",
      label: $localize`:@@welcome.okay:Okay`,
      value: "okay",
      primary: true,
      icon: "done"
    }
  ];

  onDialogAction(): void {
    this.close();
  }
}
