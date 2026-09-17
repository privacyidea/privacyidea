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
import { Directive, effect, ElementRef, inject, input } from "@angular/core";

/**
 * Restores focus to the filter input once the list resource it drives finishes reloading. Bind it
 * to the resource's own `isLoading()` (`[appRefocusAfterReload]="tokenResource.isLoading()"`) -
 * whatever redraws the table on a resolved load takes focus with it, and this puts it back where
 * the user left it instead of them having to click back in mid-word.
 *
 * Only refocuses if this input still had focus when the load started, so a load kicked off from
 * elsewhere (pagination, a column filter button) never steals focus into the filter box.
 */
@Directive({
  selector: "[appRefocusAfterReload]",
  standalone: true
})
export class RefocusAfterReloadDirective {
  readonly isLoading = input.required<boolean>({ alias: "appRefocusAfterReload" });

  private readonly el = inject(ElementRef<HTMLInputElement>);
  private hadFocus = false;

  constructor() {
    effect(() => {
      if (this.isLoading()) {
        this.hadFocus = document.activeElement === this.el.nativeElement;
        return;
      }
      if (this.hadFocus) {
        this.hadFocus = false;
        queueMicrotask(() => this.el.nativeElement.focus());
      }
    });
  }
}
