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
import { Component, input, WritableSignal } from "@angular/core";
import { MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";

export interface EditableElement<V = unknown> {
  keyMap: { key: string };
  isEditing: WritableSignal<boolean>;
  value: V;
}

@Component({
  selector: "app-edit-buttons",
  imports: [MatIconButton, MatIcon],
  templateUrl: "./edit-buttons.component.html",
  styleUrl: "./edit-buttons.component.scss"
})
export class EditButtonsComponent<T extends EditableElement> {
  toggleEdit = input.required<(element: T) => void>();
  saveEdit = input.required<(element: T) => void>();
  cancelEdit = input.required<(element: T) => void>();
  shouldHideEdit = input.required<boolean>();
  isEditingUser = input.required<boolean>();
  isEditingInfo = input.required<boolean>();
  element = input.required<T>();
}
