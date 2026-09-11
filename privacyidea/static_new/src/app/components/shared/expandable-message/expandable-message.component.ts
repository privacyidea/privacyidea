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
import { Component, computed, input, linkedSignal } from "@angular/core";
import { MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";

// Paired with .expandable-message__text max-width in the SCSS: the toggle is offered for text long enough that
// the clamp will actually hide some of it. A rough char count is enough - being one character out only means a
// toggle that expands to the same height, never text the reader cannot get at.
const CLAMP_CHARS = 40;

// Unique per instance, so aria-controls points at this cell's text and not another row's.
let nextId = 0;

/**
 * A one-line piece of text in a dense table, expandable in place.
 *
 * Long text would otherwise stretch its column past every other one, and a tooltip is the wrong answer: it is
 * mouse-only, cannot be selected or copied, and never reaches a keyboard or touch user. This clamps to one line
 * and offers a real button to reveal the rest, so the full text stays reachable and selectable by anyone.
 *
 * Renders an hyphon when there is no text, so an empty value reads as deliberate rather than missing.
 */
@Component({
  selector: "app-expandable-message",
  templateUrl: "./expandable-message.component.html",
  styleUrls: ["./expandable-message.component.scss"],
  imports: [MatIcon, MatIconButton]
})
export class ExpandableMessageComponent {
  readonly text = input.required<string | null>();
  readonly expandLabel = input<string>($localize`Show the full message`);
  readonly collapseLabel = input<string>($localize`Show less`);

  readonly textId = `expandable-message-${nextId++}`;

  // Collapsed again whenever the cell is handed different text: a table row is reused across pages and sorts,
  // and a cell that silently kept its height would describe the previous row's message.
  readonly expanded = linkedSignal<string | null, boolean>({
    source: () => this.text(),
    computation: () => false
  });

  // Only worth a toggle when the clamp actually hides something.
  readonly expandable = computed(() => (this.text() ?? "").length > CLAMP_CHARS);

  toggle(): void {
    this.expanded.set(!this.expanded());
  }
}
