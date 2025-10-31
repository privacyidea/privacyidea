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
import { Component, computed, inject, Signal, WritableSignal } from "@angular/core";
import { MAT_DIALOG_DATA, MatDialogContent } from "@angular/material/dialog";
import { DomSanitizer } from "@angular/platform-browser";
import { map } from "rxjs";
import { ContainerService, ContainerServiceInterface } from "../../../../services/container/container.service";
import { ContainerRegistrationDialogComponent } from "./container-registration-dialog.component";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { StringUtils } from "../../../../utils/string.utils";
import { environment } from "../../../../../environments/environment";

@Component({
  selector: "app-container-registration-dialog",
  imports: [MatDialogContent, AsyncPipe],
  templateUrl: "./container-registration-dialog.wizard.component.html",
  styleUrl: "./container-registration-dialog.component.scss"
})
export class ContainerRegistrationDialogWizardComponent extends ContainerRegistrationDialogComponent {
  protected override readonly containerService: ContainerServiceInterface = inject(ContainerService);
  public override readonly data: {
    registerContainer: WritableSignal<string>;
    response: any;
    containerSerial: WritableSignal<string>;
  } = inject(MAT_DIALOG_DATA);
  public readonly authService: AuthServiceInterface = inject(AuthService);
  tagData: Signal<Record<string, string>> = computed(() => ({
    containerSerial: this.data.containerSerial(),
    containerRegistrationURL: this.data.response.result?.value?.container_url?.value || "",
    containerRegistrationQR: this.data.response.result?.value?.container_url?.img || ""
  }));

  // TODO: Get custom path from pi.cfg
  customizationPath = "/static/public/customize/";

  readonly postTopHtml$ = this.http
    .get(environment.proxyUrl + this.customizationPath + "container-create.wizard.post.top.html", {
      responseType: "text"
    })
    .pipe(map((raw) => ({
        hasContent: !!raw && raw.trim().length > 0,
        sanitized: this.sanitizer.bypassSecurityTrustHtml(StringUtils.replaceWithTags(raw, this.tagData()))
      }))
    );

  readonly postBottomHtml$ = this.http
    .get(environment.proxyUrl + this.customizationPath + "container-create.wizard.post.bottom.html", {
      responseType: "text"
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(
      StringUtils.replaceWithTags(raw, this.tagData()))
    ));

  constructor(
    private http: HttpClient,
    private sanitizer: DomSanitizer
  ) {
    super();
  }
}
