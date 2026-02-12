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

import { Component, input, output } from "@angular/core";
import { assert } from "../../../../utils/assert";
import { DialogAction } from "../../../../models/dialog";
import { CommonModule } from "@angular/common";
import { MatDialogModule } from "@angular/material/dialog";
import { MatIconModule } from "@angular/material/icon";
import { MatIconButton } from "@angular/material/button";

@Component({
  selector: "app-dialog-wrapper",
  templateUrl: "./dialog-wrapper.component.html",
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatIconModule, MatIconButton],
  styleUrls: ["./dialog-wrapper.component.scss"]
})
export class DialogWrapperComponent<R = any> {
  title = input.required<string>();
  icon = input<string>();
  showCloseButton = input<boolean>(true);
  cancelButtonLabel = input<string>("Cancel");
  actions = input<DialogAction<R>[]>([]);
  onAction = output<R>();
  close = output<void>();
  isDisabled(action: DialogAction<R>): boolean {
    if (typeof action.disabled === "function") {
      return action.disabled();
    }
    return !!action.disabled;
  }
  onActionClick(action: DialogAction<R>): void {
    this.onAction.emit(action.value);
  }

  onCloseClick(): void {
    this.close.emit();
  }

  ngOnInit() {
    assert(
      this.actions().length !== 0 || this.showCloseButton(),
      "Dialog must have at least one action or a close button."
    );
  }
}
