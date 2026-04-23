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
import { AsyncPipe, NgClass, TitleCasePipe } from "@angular/common";
import { HttpClient } from "@angular/common/http";
import { Component, effect, inject, linkedSignal, SecurityContext, Signal, WritableSignal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatDialog } from "@angular/material/dialog";
import { MatIcon } from "@angular/material/icon";
import { DomSanitizer } from "@angular/platform-browser";
import { map } from "rxjs";
import {
  ContainerCreateData,
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface
} from "../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import { RealmService, RealmServiceInterface } from "../../../services/realm/realm.service";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";
import { UserService, UserServiceInterface } from "../../../services/user/user.service";
import { VersioningService, VersioningServiceInterface } from "../../../services/version/version.service";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { ContainerCreateComponent } from "./container-create.component";
import { MatTooltip } from "@angular/material/tooltip";
import { environment } from "../../../../environments/environment";
import { PiResponse } from "src/app/app.component";
import {
  ContainerRegistrationCompletedDialogComponent,
  ContainerRegistrationCompletedDialogData
} from "./container-registration-completed-dialog/container-registration-completed-dialog.component";
import { ContainerRegistrationCompletedDialogWizardComponent } from "./container-registration-completed-dialog/container-registration-completed-dialog.wizard.component";
import { ContainerCreatedDialogWizardComponent } from "./container-created-dialog/container-created-dialog.wizard.component";
import { ContainerCreationDialogData } from "./container-created-dialog/container-created-dialog.component";

@Component({
  selector: "app-container-create-wizard",
  imports: [
    MatButton,
    MatIcon,
    FormsModule,
    MatIconButton,
    AsyncPipe,
    ScrollToTopDirective,
    MatTooltip,
    NgClass,
    TitleCasePipe
  ],
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
    computation: (source) => {
      console.log("Computing generateQRCode with source:", source);
      return source.registration && source.containerType === "smartphone" && source.canRegister;
    }
  });
  override selectedTemplateName = linkedSignal({
    source: this.authService.containerWizard,
    computation: (containerWizard) => containerWizard.template || ""
  });

  protected override resetCreateOptions = () => {
    this.registerResponse.set(null);
    this.pollResponse.set(null);
    this.passphrasePrompt.set("");
    this.passphraseResponse.set("");
    this.description.set("");
  };

  // TODO: Get custom path from pi.cfg
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

  constructor(
    private http: HttpClient,
    private sanitizer: DomSanitizer
  ) {
    super();
  }

  override createContainer() {
    this.registerResponse.set(null);
    const containerType = this.containerService.selectedContainerType()?.containerType;
    if (!containerType) return;
    const createData: ContainerCreateData = {
      container_type: containerType,
      description: this.description(),
      user: this.userService.selectionUsernameFilter()
    };
    if (createData.user || this.userAssignmentComponent?.onlyAddToRealm()) {
      createData.realm = this.userService.selectedUserRealm();
    }
    if (this.selectedTemplateName()) {
      createData.template_name = this.selectedTemplateName();
    }
    console.log("Creating container with data:", createData);
    this.containerService.createContainer(createData).subscribe({
      next: (
        response: PiResponse<{
          container_serial: string;
        }>
      ) => {
        const containerSerial = response.result?.value?.container_serial;
        if (!containerSerial) {
          this.notificationService.openSnackBar("Container creation failed. No container serial returned.");
          return;
        }
        if (this.generateQRCode()) {
          this.registerContainer(containerSerial);
        } else {
          this.containerSerial.set(containerSerial);
        }
      }
    });
  }

  protected override openRegistrationDialog(response: PiResponse<ContainerRegisterData>) {
    this.dialogData.set({
      response: response,
      containerSerial: this.containerSerial,
      registerContainer: this.registerContainer.bind(this)
    });
    this.dialogService.openDialog({
      component: ContainerCreatedDialogWizardComponent,
      data: this.dialogData as Signal<ContainerCreationDialogData>
    });
  }

  protected override openRegistrationCompletedDialog(serial: string) {
    this.dialogService.openDialog({
      component: ContainerRegistrationCompletedDialogWizardComponent,
      data: { containerSerial: serial } as ContainerRegistrationCompletedDialogData
    });
  }
}
