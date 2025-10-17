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
import { AsyncPipe } from "@angular/common";
import { HttpClient } from "@angular/common/http";
import { Component, computed, inject, Signal } from "@angular/core";
import { MatButton } from "@angular/material/button";
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef
} from "@angular/material/dialog";
import { DomSanitizer } from "@angular/platform-browser";
import { map } from "rxjs";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import {
  TokenEnrollmentLastStepDialogComponent,
  TokenEnrollmentLastStepDialogData
} from "./token-enrollment-last-step-dialog.component";
import { OtpKeyComponent } from "./otp-key/otp-key.component";
import { TiqrEnrollUrlComponent } from "./tiqr-enroll-url/tiqr-enroll-url.component";
import { RegistrationCodeComponent } from "./registration-code/registration-code.component";
import { OtpValuesComponent } from "./otp-values/otp-values.component";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { Router, RouterLink } from "@angular/router";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import { ROUTE_PATHS } from "../../../../route_paths";
import { QrCodeTextComponent } from "./qr-code-text/qr-code-text.component";
import { StringUtils } from "../../../../utils/string.utils";

@Component({
  selector: "app-token-enrollment-last-step-dialog-wizard",
  imports: [
    MatButton,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    AsyncPipe,
    OtpKeyComponent,
    TiqrEnrollUrlComponent,
    RegistrationCodeComponent,
    OtpValuesComponent,
    RouterLink,
    QrCodeTextComponent
  ],
  templateUrl: "./token-enrollment-last-step-dialog.wizard.component.html",
  styleUrl: "./token-enrollment-last-step-dialog.component.scss"
})
export class TokenEnrollmentSecondStepDialogWizardComponent extends TokenEnrollmentLastStepDialogComponent {
  protected override readonly Object = Object;

  private readonly http: HttpClient = inject(HttpClient);
  private readonly sanitizer: DomSanitizer = inject(DomSanitizer);

  protected override readonly dialogRef: MatDialogRef<TokenEnrollmentLastStepDialogComponent> = inject(MatDialogRef);
  public override readonly data: TokenEnrollmentLastStepDialogData = inject(MAT_DIALOG_DATA);
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

  readonly postTopHtml$ = this.http
    .get("/static/public/customize/token-enrollment.wizard.post.top.html", {
      responseType: "text"
    })
    .pipe(map((raw) => ({
        hasContent: !!raw && raw.trim().length > 0,
        sanitized: this.sanitizer.bypassSecurityTrustHtml(StringUtils.replaceWithTags(raw, this.tagData()))
      }))
    );

  readonly postBottomHtml$ = this.http
    .get("/static/public/customize/token-enrollment.wizard.post.bottom.html", {
      responseType: "text"
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(
        StringUtils.replaceWithTags(raw, this.tagData()))
      )
    );

  logout(): void {
    this.authService.logout();
  }

  constructor() {
    super();
  }

  protected readonly RouterLink = RouterLink;
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
}
