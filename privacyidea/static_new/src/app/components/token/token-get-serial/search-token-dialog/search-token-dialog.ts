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
import { DialogWrapperComponent } from "../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { AbstractDialogComponent } from "../../../shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogAction } from "../../../../models/dialog";

@Component({
  selector: "app-search-token-dialog",
  templateUrl: "./search-token-dialog.html",
  styleUrl: "./search-token-dialog.scss",
  standalone: true,
  imports: [DialogWrapperComponent]
})
export class SearchTokenDialogComponent extends AbstractDialogComponent<string> {
  action: DialogAction<true> = {
    label: $localize`Start Search`,
    value: true,
    type: "confirm"
  };
  onAction(value: boolean) {
    this.close(value);
  }
}
