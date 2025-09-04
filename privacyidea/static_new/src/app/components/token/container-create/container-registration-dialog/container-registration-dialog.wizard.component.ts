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
import { Component, inject, WritableSignal } from "@angular/core";
import { MAT_DIALOG_DATA, MatDialogContent, MatDialogRef, MatDialogTitle } from "@angular/material/dialog";
import { DomSanitizer } from "@angular/platform-browser";
import { map } from "rxjs";
import { ContainerService, ContainerServiceInterface } from "../../../../services/container/container.service";
import { LostTokenComponent } from "../../token-card/token-tab/lost-token/lost-token.component";
import { ContainerRegistrationDialogComponent } from "./container-registration-dialog.component";

@Component({
  selector: "app-container-registration-dialog",
  imports: [MatDialogContent, MatDialogTitle, AsyncPipe],
  templateUrl: "./container-registration-dialog.wizard.component.html",
  styleUrl: "./container-registration-dialog.component.scss"
})
export class ContainerRegistrationDialogWizardComponent extends ContainerRegistrationDialogComponent {
  protected override readonly containerService: ContainerServiceInterface = inject(ContainerService);
  public override readonly data: {
    response: any;
    containerSerial: WritableSignal<string>;
  } = inject(MAT_DIALOG_DATA);

  readonly postTopHtml$ = this.http
    .get("/customize/container-create.wizard.post.top.html", {
      responseType: "text"
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  readonly postBottomHtml$ = this.http
    .get("/customize/container-create.wizard.post.bottom.html", {
      responseType: "text"
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  constructor(
    private http: HttpClient,
    private sanitizer: DomSanitizer,
    dialogRef: MatDialogRef<LostTokenComponent>
  ) {
    super(dialogRef);
  }
}
