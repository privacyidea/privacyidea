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
import { AsyncPipe } from "@angular/common";
import { HttpClient } from "@angular/common/http";
import { Component, computed, inject, SecurityContext, Signal } from "@angular/core";
import { MatDialogContent } from "@angular/material/dialog";
import { DomSanitizer } from "@angular/platform-browser";
import { map } from "rxjs";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { OtpKeyComponent } from "@components/token/token-enrollment/token-enrollment-data/otp-key/otp-key.component";
import { TiqrEnrollUrlComponent } from "@components/token/token-enrollment/token-enrollment-data/tiqr-enroll-url/tiqr-enroll-url.component";
import { RegistrationCodeComponent } from "@components/token/token-enrollment/token-enrollment-data/registration-code/registration-code.component";
import { OtpValuesComponent } from "@components/token/token-enrollment/token-enrollment-data/otp-values/otp-values.component";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { Router, RouterLink } from "@angular/router";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import { ROUTE_PATHS } from "../../../../route_paths";
import { StringUtils } from "../../../../utils/string.utils";
import { environment } from "../../../../../environments/environment";
import { DialogWrapperComponent } from "../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { TokenEnrollmentLastStepDialogComponent } from "./token-enrollment-last-step-dialog.component";
import { DialogAction } from "../../../../models/dialog";
import { MatButtonModule } from "@angular/material/button";
import { TokenEnrolledTextComponent } from "@components/token/token-enrollment/token-enrolled-text/token-enrolled-text.component";

@Component({
  selector: "app-token-enrollment-last-step-dialog-wizard",
  imports: [
    MatDialogContent,
    AsyncPipe,
    OtpKeyComponent,
    TiqrEnrollUrlComponent,
    RegistrationCodeComponent,
    OtpValuesComponent,
    DialogWrapperComponent,
    MatButtonModule,
    TokenEnrolledTextComponent
  ],
  templateUrl: "./token-enrollment-last-step-dialog.wizard.component.html",
  styleUrl: "./token-enrollment-last-step-dialog.component.scss"
})
export class TokenEnrollmentLastStepDialogWizardComponent extends TokenEnrollmentLastStepDialogComponent {
  protected readonly actions = computed(() => {
    const actions: DialogAction<"create_container" | "logout">[] = [];
    if (this.authService.containerWizard().enabled) {
      actions.push({
        type: "auxiliary",
        label: "Create Container",
        value: "create_container",
        className: "button-width-m"
      });
    }
    actions.push({
      type: "auxiliary",
      label: "Logout",
      value: "logout",
      primary: true,
    });
    return actions;
  });

  protected override readonly Object = Object;
  private readonly http: HttpClient = inject(HttpClient);
  private readonly sanitizer: DomSanitizer = inject(DomSanitizer);
  protected override readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected override readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly router: Router = inject(Router);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  tagData: Signal<Record<string, string>> = computed(() => ({
    serial: this.serial,
    qrCode: this.qrCode,
    url: this.url
  }));
  // TODO: Get custom path from pi.cfg
  customizationPath = "/static/public/customize/";
  readonly postTopHtml$ = this.http
    .get(environment.proxyUrl + this.customizationPath + "token-enrollment.wizard.post.top.html", {
      responseType: "text"
    })
    .pipe(
      map((raw) => ({
        hasContent: !!raw && raw.trim().length > 0,
        sanitized: this.sanitizer.sanitize(SecurityContext.HTML, StringUtils.replaceWithTags(raw, this.tagData()))
      }))
    );
  readonly postBottomHtml$ = this.http
    .get(environment.proxyUrl + this.customizationPath + "token-enrollment.wizard.post.bottom.html", {
      responseType: "text"
    })
    .pipe(
      map((raw) => this.sanitizer.sanitize(SecurityContext.HTML, StringUtils.replaceWithTags(raw, this.tagData())))
    );

  constructor() {
    super();
  }

  protected readonly RouterLink = RouterLink;
  protected readonly ROUTE_PATHS = ROUTE_PATHS;

  onAction(value: "create_container" | "logout"): void {
    switch (value) {
      case "create_container":
        this.createContainer();
        break;
      case "logout":
        this.logout();
        break;
    }
  }

  private createContainer(): void {
    this.dialogRef.close();
    this.router.navigate([ROUTE_PATHS.TOKENS_CONTAINERS_WIZARD]);
  }

  logout(): void {
    this.authService.logout();
  }
}
