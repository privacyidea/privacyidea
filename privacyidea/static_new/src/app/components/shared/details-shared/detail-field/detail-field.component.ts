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
import { Component, input, signal } from "@angular/core";
import { DetailFieldRowComponent } from "@components/shared/details-shared/field-editing/detail-field-row/detail-field-row.component";
import { DetailsDefaultValueCellComponent } from "@components/shared/details-shared/value-cells/details-default-value-cell/details-default-value-cell.component";
import { injectEditableField } from "@components/shared/details-shared/field-editing/editable-field";
import { EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";

/**
 * Generic, explicitly-listed detail row for genuinely uniform "label: value"
 * fields (text / number, optionally inline-editable).
 */
@Component({
  selector: "app-detail-field",
  standalone: true,
  imports: [DetailFieldRowComponent, DetailsDefaultValueCellComponent, EditButtonsComponent],
  templateUrl: "./detail-field.component.html"
})
export class DetailFieldComponent {
  readonly label = input.required<string>();
  /** Formatted text shown when not editing. */
  readonly displayText = input<string>("");
  /** Initial value loaded into the edit buffer when editing starts. */
  readonly editValue = input<string>("");
  readonly editable = input(false);
  readonly number = input(false);
  /** True while any field/user/info is editing or the entity is revoked; hides the edit affordance of other fields. */
  readonly blockEditing = input(false);
  readonly divClass = input<string>("");
  readonly spanClass = input<string>("");
  /** Persist the edited value. Only invoked for editable fields. */
  readonly save = input<(value: string) => void>(() => undefined);

  readonly draft = signal<string>("");

  protected readonly field = injectEditableField({
    onOpen: () => this.draft.set(this.editValue()),
    onCommit: () => this.save()(this.draft())
  });
}
