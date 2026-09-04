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
import { Component, computed, inject, linkedSignal } from "@angular/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSelectChange, MatSelectModule } from "@angular/material/select";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import {
  MessageConfirmationDialogComponent,
  MessageConfirmationDialogData
} from "@components/shared/dialog/message-confirmation-dialog/message-confirmation-dialog.component";
import {
  AUTH_SESSION_MODES,
  AuthSessionMode,
  AuthSessionModeService,
  AuthSessionModeServiceInterface,
  isModeAvailable
} from "@services/auth-session-mode/auth-session-mode.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";

const MODE_EXPOSURE: Record<AuthSessionMode, number> = {
  "single-tab": 0,
  "multi-tab-ephemeral": 1,
  "multi-tab-persistent": 2
};

const MODE_HINTS: Record<AuthSessionMode, { title: string; message: string }> = {
  "single-tab": {
    title: $localize`:@@uiSettings.sessionSingleTabTitle:Single Tab Sessions`,
    message: $localize`:@@uiSettings.sessionSingleTabMessage:Only one tab keeps the login. You get logged out when the tab is closed.`
  },
  "multi-tab-ephemeral": {
    title: $localize`:@@uiSettings.sessionMultiTabEphemeralTitle:Multiple Tab Session`,
    message: $localize`:@@uiSettings.sessionMultiTabEphemeralMessage:The session is shared across multiple tabs. You stay logged in until the last tab is closed.`
  },
  "multi-tab-persistent": {
    title: $localize`:@@uiSettings.sessionMultiTabPersistentTitle:Multiple Tab Session (persistent)`,
    message: $localize`:@@uiSettings.sessionMultiTabPersistentMessage:The session is shared across multiple tabs. You stay logged in after closing the browser, until the session expires.`
  }
};

@Component({
  selector: "app-auth-session-mode-card",
  imports: [DetailsCardComponent, MatFormFieldModule, MatSelectModule],
  templateUrl: "./auth-session-mode-card.component.html",
  styleUrl: "./auth-session-mode-card.component.scss"
})
export class AuthSessionModeCardComponent {
  private readonly authSessionModeService: AuthSessionModeServiceInterface = inject(AuthSessionModeService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly mode = this.authSessionModeService.mode;
  protected readonly modeOptions = computed(() => {
    const current = this.mode();
    return AUTH_SESSION_MODES.filter((mode) => isModeAvailable(mode) || mode === current).map((mode) => ({
      value: mode,
      label: MODE_HINTS[mode].title
    }));
  });
  protected readonly selectedMode = linkedSignal(() => this.mode());
  protected readonly modeHint = computed(() => MODE_HINTS[this.selectedMode()].message);

  protected async selectAuthSessionMode(event: MatSelectChange): Promise<void> {
    const target = event.value as AuthSessionMode;
    this.selectedMode.set(target);
    if (MODE_EXPOSURE[target] > MODE_EXPOSURE[this.mode()]) {
      const confirmed = await this.confirmModeChange(MODE_HINTS[target]);
      if (!confirmed) {
        this.selectedMode.set(this.mode());
        return;
      }
    }
    this.authSessionModeService.setMode(target);
    this.selectedMode.set(this.mode());
  }

  private async confirmModeChange(args: { title: string; message: string }): Promise<boolean> {
    const result = await this.dialogService.openDialogAsync<MessageConfirmationDialogData, boolean>({
      component: MessageConfirmationDialogComponent,
      data: {
        title: args.title,
        message: args.message,
        confirmAction: { type: "confirm", label: $localize`:@@common.confirm:Confirm`, value: true }
      }
    });
    return result === true;
  }
}
