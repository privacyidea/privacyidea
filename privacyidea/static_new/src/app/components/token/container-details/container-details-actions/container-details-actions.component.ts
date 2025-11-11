/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { Component, computed, effect, inject, Input, signal, WritableSignal } from "@angular/core";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { ContainerRegistrationInitDialogComponent } from "../../container-registration/container-registration-init-dialog/container-registration-init-dialog.component";
import { PiResponse } from "../../../../app.component";
import {
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface,
  ContainerUnregisterData
} from "../../../../services/container/container.service";
import { ContainerRegistrationFinalizeDialogComponent } from "../../container-registration/container-registration-finalize-dialog/container-registration-finalize-dialog.component";
import { MatDialog } from "@angular/material/dialog";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import { MatButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { ROUTE_PATHS } from "../../../../route_paths";
import { Router } from "@angular/router";
import { MatDivider } from "@angular/material/divider";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";

export type ContainerRegisterFinalizeData = {
  response: PiResponse<ContainerRegisterData>,
  registerContainer: (userStorePW?: boolean, passphrasePrompt?: string,
                      passphraseResponse?: string, rollover?: boolean, regenerate?: boolean) => void,
  rollover: boolean
};

@Component({
  selector: "app-container-details-actions",
  templateUrl: "./container-details-actions.component.html",
  imports: [
    MatButton,
    MatIcon,
    MatDivider
  ],
  styleUrl: "./container-details-actions.component.scss"
})
export class ContainerDetailsActionsComponent {
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly dialog: MatDialog = inject(MatDialog);
  private router = inject(Router);

  @Input() containerSerial!: string;
  @Input() containerType!: string;

  passphrasePrompt: string = "";
  passphraseResponse: string = "";
  userStorePW: boolean = false;
  dialogData: WritableSignal<ContainerRegisterFinalizeData | null> = signal(null);
  registrationState = computed(() => {
    return this.containerService.containerDetail()?.containers[0]?.info?.registration_state ?? "";
  });

  registrationAllowed = computed(() => {
    return ["client_wait", ""].includes(this.registrationState()) && this.authService.actionAllowed("container_register");
  });
  rolloverAllowed = computed(() => {
    return ["registered", "rollover", "rollover_completed"].includes(this.registrationState()) &&
      this.authService.actionAllowed("container_rollover");
  });
  unregisterAllowed = computed(() => {
    return this.registrationState() !== "" && this.authService.actionAllowed("container_unregister");
  });
  anyActionsAllowed = computed(() => {
    return this.authService.actionAllowed("container_delete") || (this.containerType === "smartphone" &&
      (this.registrationAllowed() || this.rolloverAllowed() || this.unregisterAllowed()));
  });

  ngOnDestroy(): void {
    this.containerService.stopPolling();
  }

  constructor() {
    // Effect to close dialog when polling stops
    effect(() => {
      if (!this.containerService.isPollingActive()) {
        this.dialog.closeAll();
      }
    });
  }

  deleteContainer() {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: [this.containerSerial],
          title: "Delete Container",
          type: "container",
          action: "delete",
          numberOfTokens: 1
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          this.containerService.deleteContainer(this.containerSerial).subscribe(() => {
            const prev = this.contentService.previousUrl();

            if (prev.startsWith(ROUTE_PATHS.TOKENS_DETAILS)) {
              this.contentService.isProgrammaticTabChange.set(true);
              this.router.navigateByUrl(prev);
            } else {
              this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS);
            }
          });
        }
      });
  }

  openRegisterInitDialog(rollover: boolean) {
    const container = this.containerService.containerDetailResource.value()?.result?.value?.containers?.[0];
    this.dialog.open(ContainerRegistrationInitDialogComponent, {
      data: {
        registerContainer: this.registerContainer.bind(this),
        rollover: rollover,
        containerHasOwner: (container?.users?.length ?? 0) > 0 || false
      }
    });
  }

  registerContainer(userStorePW?: boolean, passphrasePrompt?: string, passphraseResponse?: string, rollover?: boolean,
                    regenerate: boolean = false) {
    this.userStorePW = userStorePW ?? this.userStorePW;
    this.passphrasePrompt = passphrasePrompt ?? this.passphrasePrompt;
    this.passphraseResponse = passphraseResponse ?? this.passphraseResponse;
    if (!regenerate) {
      this.dialog.closeAll();
    }
    this.containerService
      .registerContainer({
        container_serial: this.containerSerial,
        passphrase_user: this.userStorePW,
        passphrase_response: this.passphraseResponse,
        passphrase_prompt: this.passphrasePrompt,
        rollover: rollover ?? false
      })
      .subscribe((registerResponse) => {
        if (regenerate) {
          this.dialogData.update(data => data ? { ...data, response: registerResponse } : data);
        } else {
          this.openRegisterFinalizeDialog(registerResponse, rollover);
          this.containerService.startPolling(this.containerSerial);
        }
      });
  }

  unregisterContainer() {
    this.containerService
      .unregister(this.containerSerial)
      .subscribe((unregisterResponse: PiResponse<ContainerUnregisterData>) => {
        if (unregisterResponse?.result?.value?.success) {
          this.notificationService.openSnackBar("Container unregistered successfully.");
        } else {
          this.notificationService.openSnackBar("Failed to unregister container.");
        }
        this.containerService.containerDetailResource.reload();
      });
  }

  openRegisterFinalizeDialog(response: PiResponse<ContainerRegisterData>, rollover?: boolean) {
    this.dialogData.set({
      response: response,
      registerContainer: this.registerContainer.bind(this),
      rollover: rollover || false
    });
    const dialogRef = this.dialog.open(ContainerRegistrationFinalizeDialogComponent, {
      data: this.dialogData
    });
    dialogRef.afterClosed().subscribe(() => {
      this.containerService.stopPolling();
    });
  }
}