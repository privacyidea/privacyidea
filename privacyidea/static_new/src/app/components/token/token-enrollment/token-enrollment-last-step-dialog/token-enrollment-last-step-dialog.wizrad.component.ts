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
import { Component, inject } from "@angular/core";
import { MatButton, MatIconButton } from "@angular/material/button";
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle
} from "@angular/material/dialog";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatIcon } from "@angular/material/icon";
import { DomSanitizer } from "@angular/platform-browser";
import { map } from "rxjs";
import { EnrollmentResponse } from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { UserData } from "../../../../services/user/user.service";
import { TokenEnrollmentLastStepDialogComponent } from "./token-enrollment-last-step-dialog.component";

export type TokenEnrollmentLastStepDialogData = {
  response: EnrollmentResponse;
  enrollToken: () => void;
  user: UserData | null;
  userRealm: string;
  onlyAddToRealm: boolean;
};

@Component({
  selector: "app-token-enrollment-last-step-dialog-wizard",
  imports: [
    MatButton,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatDialogTitle,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatIcon,
    MatIconButton,
    AsyncPipe
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

  readonly postTopHtml$ = this.http
    .get("/customize/token-enrollment.wizard.post.top.html", {
      responseType: "text"
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  readonly postBottomHtml$ = this.http
    .get("/customize/token-enrollment.wizard.post.bottom.html", {
      responseType: "text"
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  constructor() {
    super();
  }
}
