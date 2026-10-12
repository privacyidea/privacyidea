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

import { Component, ElementRef, inject, model, viewChild } from "@angular/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";

/**
 * The search field for policy actions. It filters both action panels, and is rendered either at
 * the top of the actions tab or, once the page header reaches it, inside that header - so it lives
 * in two places and keeps no state of its own. Focus, on the input with its caret or on the clear button, is handed over when it moves.
 */
@Component({
  selector: "app-policy-action-search",
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, ClearableInputComponent],
  templateUrl: "./policy-action-search.component.html",
  styleUrl: "./policy-action-search.component.scss"
})
export class PolicyActionSearchComponent {
  readonly actionFilter = model<string>("");

  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly input = viewChild.required<ElementRef<HTMLInputElement>>("input");

  /** Which control in this copy has focus, with the caret range and its direction for the input; null when focus is elsewhere. */
  focusState(): SearchFocus | null {
    const active = document.activeElement;
    const input = this.input().nativeElement;
    if (active === input) {
      const end = input.value.length;
      return {
        start: input.selectionStart ?? end,
        end: input.selectionEnd ?? end,
        direction: input.selectionDirection ?? "none"
      };
    }
    return active && active === this.clearButton() ? "clear-button" : null;
  }

  takeFocus(focus: SearchFocus): void {
    if (focus === "clear-button") {
      this.clearButton()?.focus({ preventScroll: true });
      return;
    }
    const input = this.input().nativeElement;
    input.focus({ preventScroll: true });
    input.setSelectionRange(focus.start, focus.end, focus.direction);
  }

  private clearButton(): HTMLButtonElement | null {
    return this.host.nativeElement.querySelector("app-clear-button button");
  }
}

export interface TextSelection {
  start: number;
  end: number;
  direction: "forward" | "backward" | "none";
}

export type SearchFocus = TextSelection | "clear-button";
