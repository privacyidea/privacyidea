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
import { Component, computed, signal } from "@angular/core";

import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";

type WelcomeAction = "next" | "restart";

@Component({
  selector: "app-welcome-dialog",
  standalone: true,
  imports: [DialogWrapperComponent],
  templateUrl: "./welcome-dialog.component.html",
  styleUrl: "./welcome-dialog.component.scss"
})
export class WelcomeDialogComponent extends AbstractDialogComponent<void, void> {
  step = signal<number>(0);

  readonly dialogTitle = computed(() => {
    switch (this.step()) {
      case 1:
        return $localize`:@@welcome.valueOpenSource:The value of open source`;
      case 2:
        return $localize`:@@welcome.addedValuePrivacyidea:The added value of privacyIDEA Enterprise Edition`;
      case 3:
        return $localize`:@@welcome.thankYouImproving:Thank you for improving your security!`;
      default:
        return $localize`:@@welcome.welcome:Welcome`;
    }
  });

  readonly dialogActions = computed((): DialogAction<WelcomeAction>[] => {
    if (this.step() === 3) {
      return [
        {
          type: "auxiliary",
          label: $localize`:@@welcome.readAgain:Read again`,
          value: "restart",
          icon: "replay"
        },
        {
          type: "confirm",
          label: $localize`:@@welcome.diveIn:Dive In!`,
          value: "next",
          primary: true,
          icon: "keyboard_arrow_right"
        }
      ];
    }
    return [
      {
        type: "auxiliary",
        label: $localize`:@@common.next:Next`,
        value: "next",
        primary: true
      }
    ];
  });

  onDialogAction(value: WelcomeAction): void {
    if (value === "restart") {
      this.resetWelcome();
    } else {
      this.nextWelcome();
    }
  }

  nextWelcome(): void {
    const nextStep = this.step() + 1;
    if (nextStep > 3) {
      this.close();
    } else {
      this.step.set(nextStep);
    }
  }

  resetWelcome(): void {
    this.step.set(0);
  }
}
