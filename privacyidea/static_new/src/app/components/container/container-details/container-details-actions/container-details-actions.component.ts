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

import { Component, computed, effect, inject, input, signal, OnDestroy } from "@angular/core";
import { MatButton } from "@angular/material/button";
import { MatDivider } from "@angular/material/divider";
import { MatIcon } from "@angular/material/icon";
import { Router } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { ContainerRegistrationFinalizeDialogComponent } from "@components/container/container-registration/container-registration-finalize-dialog/container-registration-finalize-dialog.component";
import { ContainerRegistrationInitDialogComponent } from "@components/container/container-registration/container-registration-init-dialog/container-registration-init-dialog.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface,
  ContainerUnregisterData
} from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";

export interface ContainerRegisterFinalizeData {
  response: PiResponse<ContainerRegisterData>;
  registerContainer: (
    userStorePW?: boolean,
    passphrasePrompt?: string,
    passphraseResponse?: string,
    rollover?: boolean,
    regenerate?: boolean
  ) => void;
  rollover: boolean;
}

@Component({
  selector: "app-container-details-actions",
  templateUrl: "./container-details-actions.component.html",
  imports: [MatButton, MatIcon, MatDivider],
  styleUrl: "./container-details-actions.component.scss"
})
export class ContainerDetailsActionsComponent implements OnDestroy {
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);

  private router = inject(Router);

  containerSerial = input.required<string>();
  containerType = input.required<string>();

  passphrasePrompt = "";
  passphraseResponse = "";
  userStorePW = false;
  dialogData = signal<ContainerRegisterFinalizeData | undefined>(undefined);
  registrationState = computed(
    () => this.containerService.containerDetails()?.containers[0]?.info?.registration_state ?? ""
  );

  registrationAllowed = computed(
    () => ["client_wait", ""].includes(this.registrationState()) && this.authService.actionAllowed("container_register")
  );
  rolloverAllowed = computed(
    () =>
      ["registered", "rollover", "rollover_completed"].includes(this.registrationState()) &&
      this.authService.actionAllowed("container_rollover")
  );
  unregisterAllowed = computed(
    () => this.registrationState() !== "" && this.authService.actionAllowed("container_unregister")
  );
  anyActionsAllowed = computed(() => {
    const container_delete_allowed = this.authService.actionAllowed("container_delete");
    return (
      container_delete_allowed ||
      (this.containerType() === "smartphone" &&
        (this.registrationAllowed() || this.rolloverAllowed() || this.unregisterAllowed()))
    );
  });

  constructor() {
    effect(() => {
      if (!this.containerService.isPollingActive()) {
        this.dialogService.closeAllDialogs();
      }
    });
  }

  ngOnDestroy(): void {
    this.containerService.stopPolling();
  }


  enrollTokenInContainer() {
    this.containerService.selectedContainerSerial.set(this.containerSerial());
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_ENROLLMENT);
  }

  deleteContainer() {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`Delete Container`,
          confirmAction: {
            label: $localize`Delete`,
            value: true,
            type: "destruct"
          },
          itemType: "container",
          items: [this.containerSerial()]
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          this.containerService.deleteContainer(this.containerSerial()).subscribe(() => {
            const prev = this.contentService.previousUrl();
            this.notificationService.success($localize`Container deleted successfully.`);
            if (prev.startsWith(ROUTE_PATHS.TOKENS_DETAILS)) {
              this.router.navigateByUrl(prev);
            } else {
              this.router.navigateByUrl(ROUTE_PATHS.CONTAINERS);
            }
          });
        }
      });
  }

  openRegisterInitDialog(rollover: boolean) {
    const container = this.containerService.containerDetailsResource.hasValue()
      ? this.containerService.containerDetailsResource.value()?.result?.value?.containers?.[0]
      : undefined;
    this.dialogService.openDialog({
      component: ContainerRegistrationInitDialogComponent,
      data: {
        registerContainer: this.registerContainer.bind(this),
        rollover: rollover,
        containerHasOwner: (container?.users?.length ?? 0) > 0 || false
      }
    });
  }

  registerContainer(
    userStorePW?: boolean,
    passphrasePrompt?: string,
    passphraseResponse?: string,
    rollover?: boolean,
    regenerate = false
  ) {
    this.userStorePW = userStorePW ?? this.userStorePW;
    this.passphrasePrompt = passphrasePrompt ?? this.passphrasePrompt;
    this.passphraseResponse = passphraseResponse ?? this.passphraseResponse;
    if (!regenerate) {
      this.dialogService.closeAllDialogs();
    }
    this.containerService
      .registerContainer({
        container_serial: this.containerSerial(),
        passphrase_user: this.userStorePW,
        passphrase_response: this.passphraseResponse,
        passphrase_prompt: this.passphrasePrompt,
        rollover: rollover ?? false
      })
      .subscribe((registerResponse) => {
        if (regenerate) {
          this.dialogData.update((data) => (data ? { ...data, response: registerResponse } : data));
        } else {
          this.openRegisterFinalizeDialog(registerResponse, rollover);
          this.containerService.startPolling(this.containerSerial());
        }
      });
  }

  unregisterContainer() {
    this.containerService
      .unregister(this.containerSerial())
      .subscribe((unregisterResponse: PiResponse<ContainerUnregisterData>) => {
        if (unregisterResponse?.result?.value?.success) {
          this.notificationService.success($localize`Container unregistered successfully.`);
        } else {
          this.notificationService.error($localize`Failed to unregister container.`);
        }
        this.containerService.containerDetailsResource.reload();
      });
  }

  openRegisterFinalizeDialog(response: PiResponse<ContainerRegisterData>, rollover?: boolean) {
    this.dialogData.set({
      response: response,
      registerContainer: this.registerContainer.bind(this),
      rollover: rollover || false
    });
    const dialogRef = this.dialogService.openDialog({
      component: ContainerRegistrationFinalizeDialogComponent,
      data: this.dialogData
    });
    dialogRef.afterClosed().subscribe(() => {
      this.containerService.stopPolling();
    });
  }
}
