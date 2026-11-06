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
import { COMMA, ENTER } from "@angular/cdk/keycodes";
import { Component, effect, input, output, signal } from "@angular/core";
import { form, FormField } from "@angular/forms/signals";
import { MatChipInputEvent, MatChipsModule } from "@angular/material/chips";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";

/**
 * An editable list of strings, shown as removable chips in front of the input that adds them. Enter and comma add the
 * typed text, split on commas, trimmed, without blanks and without entries the list already holds (case-sensitive).
 * The list itself belongs to the parent: the component emits the new list and shows whatever `values` it is given.
 *
 * Buttons that act on the whole list are projected into the `chipListExtras` slot, which renders below the field.
 */
@Component({
  selector: "app-chip-list-input",
  imports: [FormField, MatChipsModule, MatFormFieldModule, MatIconModule],
  templateUrl: "./chip-list-input.component.html",
  styleUrl: "./chip-list-input.component.scss",
  host: { class: "chip-list-input" }
})
export class ChipListInputComponent {
  readonly values = input.required<string[]>();
  // The floating label of the field.
  readonly label = input.required<string>();
  // The accessible name of the chip grid.
  readonly gridLabel = input.required<string>();
  // Maps an entry onto the text shown on its chip. Defaults to the entry itself.
  readonly chipLabel = input<(value: string) => string>((value) => value);
  // Width utility class applied to the form field (e.g. "input-width-xl"). Defaults to filling the host.
  readonly fieldClass = input<string>("width-full");
  readonly valuesChange = output<string[]>();

  protected readonly separatorKeyCodes = [ENTER, COMMA];

  // The text typed since the last entry was added. Material does not clear the input itself, and a DOM clear does not
  // fire `input`, so the field model is cleared instead.
  readonly draft = signal("");
  protected readonly draftField = form(this.draft);

  // The list as last emitted, until the parent hands the updated `values` back. Entries added within one tick build on it
  // instead of on the stale input.
  private pending: string[] | null = null;

  constructor() {
    effect(() => {
      this.values();
      this.pending = null;
    });
  }

  protected onTokenEnd(event: MatChipInputEvent): void {
    const current = this.pending ?? this.values();
    const next = [...current];
    for (const part of event.value.split(",").map((p) => p.trim())) {
      if (part && !next.includes(part)) {
        next.push(part);
      }
    }
    if (next.length !== current.length) {
      this.pending = next;
      this.valuesChange.emit(next);
    }
    event.chipInput?.clear();
    this.draft.set("");
  }

  protected removeLabel(value: string): string {
    return $localize`:@@common.removeEntry:Remove ${this.chipLabel()(value)}:ENTRY:`;
  }

  protected remove(value: string): void {
    this.valuesChange.emit(this.values().filter((v) => v !== value));
  }
}
