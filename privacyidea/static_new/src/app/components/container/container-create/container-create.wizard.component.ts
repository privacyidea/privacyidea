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
import { AsyncPipe, NgClass, TitleCasePipe } from "@angular/common";
import { HttpClient } from "@angular/common/http";
import { Component, inject, linkedSignal, SecurityContext, WritableSignal } from "@angular/core";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";
import { DomSanitizer } from "@angular/platform-browser";
import { PiResponse } from "@app/app.component";
import { ContainerCreatedDialogWizardComponent } from "@components/container/container-create/container-created-dialog/container-created-dialog.wizard.component";
import { ContainerRegistrationCompletedDialogData } from "@components/container/container-create/container-registration-completed-dialog/container-registration-completed-dialog.component";
import { ContainerRegistrationCompletedDialogWizardComponent } from "@components/container/container-create/container-registration-completed-dialog/container-registration-completed-dialog.wizard.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { environment } from "@env/environment";
import {
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface
} from "@services/container/container.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { map } from "rxjs";
import { ContainerCreateComponent } from "./container-create.component";

@Component({
  selector: "app-container-create-wizard",
  imports: [MatButton, MatIcon, MatIconButton, AsyncPipe, ScrollToTopDirective, MatTooltip, NgClass, TitleCasePipe],
  templateUrl: "./container-create.wizard.component.html",
  styleUrl: "./container-create.component.scss"
})
export class ContainerCreateWizardComponent extends ContainerCreateComponent {
  protected override readonly userService: UserServiceInterface = inject(UserService);
  protected override readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected override readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected override readonly tokenService: TokenServiceInterface = inject(TokenService);

  override generateQRCode: WritableSignal<boolean> = linkedSignal({
    source: () => ({
      registration: this.authService.containerWizard().registration,
      containerType: this.containerService.selectedContainerType()?.containerType,
      canRegister: this.authService.actionAllowed("container_register")
    }),
    computation: (source) => source.registration && source.containerType === "smartphone" && source.canRegister
  });

  protected override resetCreateOptions = () => {
    this.registerResponse.set(null);
    this.passphrasePrompt.set("");
    this.passphraseResponse.set("");
    this.description.set("");
  };

  private readonly http = inject(HttpClient);
  private readonly sanitizer = inject(DomSanitizer);

  customizationPath = "/static/public/customize/";

  readonly preTopHtml$ = this.http
    .get(environment.proxyUrl + this.customizationPath + "container-create.wizard.pre.top.html", {
      responseType: "text"
    })
    .pipe(
      map((raw) => ({
        hasContent: !!raw && raw.trim().length > 0,
        sanitized: this.sanitizer.sanitize(SecurityContext.HTML, raw)
      }))
    );

  readonly preBottomHtml$ = this.http
    .get(environment.proxyUrl + this.customizationPath + "container-create.wizard.pre.bottom.html", {
      responseType: "text"
    })
    .pipe(map((raw) => this.sanitizer.sanitize(SecurityContext.HTML, raw)));

  protected override onCreationSuccess(serial: string) {
    this.containerSerial.set(serial);
    this.openRegistrationDialog({
      result: { value: { container_serial: serial } }
    } as any);
  }

  protected override openRegistrationDialog(response: PiResponse<ContainerRegisterData>) {
    this.dialogData.set({
      response: response,
      containerSerial: this.containerSerial,
      registerContainer: this.registerContainer.bind(this)
    });

    this.dialogService.openDialog({
      component: ContainerCreatedDialogWizardComponent,
      data: this.dialogData
    });
  }

  protected override openRegistrationCompletedDialog(serial: string) {
    this.dialogService.openDialog({
      component: ContainerRegistrationCompletedDialogWizardComponent,
      data: { containerSerial: serial } as ContainerRegistrationCompletedDialogData
    });
  }
}
