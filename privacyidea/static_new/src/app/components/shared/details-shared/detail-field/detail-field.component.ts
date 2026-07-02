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
import { Component, inject, input, OnDestroy, OnInit, signal } from "@angular/core";
import { EditableElement, EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { DetailsDefaultValueCellComponent } from "@components/shared/details-shared/details-shared.components";
import { DetailsEditRegistry } from "@components/shared/details-shared/details-edit-registry.service";

/**
 * Generic, explicitly-listed detail row for genuinely uniform "label: value"
 * fields (text / number, optionally inline-editable). Renders the 35/65 key/value
 * row, owns its edit state, and registers with the host's DetailsEditRegistry so
 * "is anything editing?" / "save all" work without a central data list.
 */
@Component({
  selector: "app-detail-field",
  standalone: true,
  imports: [DetailsDefaultValueCellComponent, EditButtonsComponent],
  host: {
    "[class.detail-field--editing]": "isEditing()"
  },
  templateUrl: "./detail-field.component.html",
  styleUrl: "./detail-field.component.scss"
})
export class DetailFieldComponent implements OnInit, OnDestroy {
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

  private readonly registry = inject(DetailsEditRegistry);

  readonly isEditing = signal(false);
  readonly draft = signal<string>("");

  protected readonly editButtonsElement: EditableElement<string> = {
    keyMap: { key: "" },
    isEditing: this.isEditing,
    value: ""
  };

  private readonly handle = {
    isEditing: this.isEditing,
    save: () => this.commit(),
    cancel: () => this.cancel()
  };

  ngOnInit(): void {
    this.registry.register(this.handle);
  }

  ngOnDestroy(): void {
    this.registry.unregister(this.handle);
  }

  protected readonly toggle = (): void => {
    if (!this.isEditing()) {
      this.draft.set(this.editValue());
    }
    this.isEditing.update((editing) => !editing);
  };

  protected readonly commit = (): void => {
    this.save()(this.draft());
    this.isEditing.set(false);
  };

  protected readonly cancel = (): void => {
    this.isEditing.set(false);
  };
}
