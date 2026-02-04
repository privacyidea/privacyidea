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
import { Component, inject, signal } from "@angular/core";
import { MatButton } from "@angular/material/button";
import { CommonModule } from "@angular/common";
import { MatDialogRef } from "@angular/material/dialog";
import { MatIcon } from "@angular/material/icon";

@Component({
  selector: "app-welcome-dialog",
  standalone: true,
  imports: [CommonModule, MatButton, MatIcon],
  templateUrl: "./welcome-dialog.component.html",
  styleUrl: "./welcome-dialog.component.scss"
})
export class WelcomeDialogComponent {
  private dialogRef = inject(MatDialogRef<WelcomeDialogComponent>);
  step = signal<number>(0);

  nextWelcome(): void {
    const nextStep = this.step() + 1;
    if (nextStep >= 5) {
      this.dialogRef.close();
    } else {
      this.step.set(nextStep);
    }
  }

  resetWelcome(): void {
    this.step.set(0);
  }
}
