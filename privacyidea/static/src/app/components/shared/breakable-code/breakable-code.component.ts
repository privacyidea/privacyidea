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
import { Component, computed, input } from "@angular/core";

// An identifier like WEBUI_PASSKEY_LOGIN_DISABLED has no break opportunity of its own, so a narrow cell would break it
// at an arbitrary character. A <wbr> after each underscore lets it wrap between its words instead, without adding a
// character to what is selected and copied.
@Component({
  selector: "app-breakable-code",
  standalone: true,
  templateUrl: "./breakable-code.component.html"
})
export class BreakableCodeComponent {
  readonly text = input<string | null | undefined>("");

  readonly segments = computed(() => (this.text() ?? "").split(/(?<=_)/));
}
