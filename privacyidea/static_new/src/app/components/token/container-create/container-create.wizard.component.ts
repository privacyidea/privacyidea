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
import { Component, inject, linkedSignal, WritableSignal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatDialog } from "@angular/material/dialog";
import { MatIcon } from "@angular/material/icon";
import { DomSanitizer } from "@angular/platform-browser";
import { map } from "rxjs";
import { ContainerService, ContainerServiceInterface } from "../../../services/container/container.service";
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
  protected override readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected override readonly userService: UserServiceInterface = inject(UserService);
  protected override readonly realmService: RealmServiceInterface = inject(RealmService);
  protected override readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected override readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected override readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected override readonly contentService: ContentServiceInterface = inject(ContentService);
  protected override readonly wizard: boolean = true;

  override generateQRCode: WritableSignal<boolean> = linkedSignal({
      source: this.authService.containerWizard,
      computation: (containerWizard) => containerWizard.registration
    }
  );
  override selectedTemplate = linkedSignal({
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
    .pipe(map((raw) => ({
        hasContent: !!raw && raw.trim().length > 0,
        sanitized: this.sanitizer.bypassSecurityTrustHtml(raw)
      }))
    );

  readonly preBottomHtml$ = this.http
    .get(environment.proxyUrl + this.customizationPath + "container-create.wizard.pre.bottom.html", {
      responseType: "text"
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  constructor(
    private http: HttpClient,
    private sanitizer: DomSanitizer,
    registrationDialog: MatDialog
  ) {
    super(registrationDialog);
  }
}
