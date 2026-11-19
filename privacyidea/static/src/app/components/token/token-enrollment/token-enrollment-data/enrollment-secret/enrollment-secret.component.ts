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

import { Component, computed, input, output, signal } from "@angular/core";
import { MatIcon } from "@angular/material/icon";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";

@Component({
  selector: "app-enrollment-secret",
  imports: [CopyButtonComponent, MatIcon],
  templateUrl: "./enrollment-secret.component.html",
  styleUrl: "./enrollment-secret.component.scss"
})
export class EnrollmentSecretComponent {
  label = input.required<string>();
  value = input.required<string>();
  // Asks to save the secret now; empty shows the secret alone.
  hint = input<string>("");
  // Emitted when the secret is revealed or copied.
  saved = output<void>();

  protected readonly visible = signal(false);
  protected readonly masked = computed(() => "•".repeat(this.value().length));
  protected readonly toggleLabel = computed(() =>
    this.visible()
      ? $localize`:@@token.hideSecret:Hide ${this.label()}:label:`
      : $localize`:@@token.showSecret:Show ${this.label()}:label:`
  );

  toggleVisible(): void {
    const visible = !this.visible();
    this.visible.set(visible);
    if (visible) {
      this.saved.emit();
    }
  }
}
