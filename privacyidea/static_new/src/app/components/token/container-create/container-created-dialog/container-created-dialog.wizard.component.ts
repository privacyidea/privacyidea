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
import { Component, computed, inject, SecurityContext } from "@angular/core";
import { MatButton } from "@angular/material/button";
import { MatDialogActions, MatDialogClose, MatDialogContent } from "@angular/material/dialog";
import { DomSanitizer } from "@angular/platform-browser";
import { catchError, map, of } from "rxjs";
import { environment } from "../../../../../environments/environment";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "../../../../services/container/container.service";
import { StringUtils } from "../../../../utils/string.utils";
import { ContainerCreatedDialogComponent } from "./container-created-dialog.component";

@Component({
  selector: "app-container-created-wizard-dialog",
  imports: [MatDialogContent, MatDialogActions, MatDialogClose, MatButton, AsyncPipe],
  templateUrl: "./container-created-dialog.wizard.component.html",
  styleUrl: "./container-created-dialog.component.scss"
})
export class ContainerCreatedDialogWizardComponent extends ContainerCreatedDialogComponent {
  protected override readonly containerService: ContainerServiceInterface = inject(ContainerService);
  public readonly authService: AuthServiceInterface = inject(AuthService);
  tagData = computed<Record<string, string>>(() => {
    const data = this.data();
    if (!data) {
      const record = {};
      return record;
    }
    return {
      containerSerial: data.containerSerial(),
      containerRegistrationURL: data.response.result?.value?.container_url?.value || "",
      containerRegistrationQR: data.response.result?.value?.container_url?.img || ""
    };
  });

  customizationPath = "/static/public/customize/";

  readonly postTopHtml$ = this.http
    .get(environment.proxyUrl + this.customizationPath + "container-create.wizard.post.top.html", {
      responseType: "text"
    })
    .pipe(
      catchError(() => of("")),
      map((raw) => ({
        hasContent: !!raw && raw.trim().length > 0,
        sanitized: this.sanitizer.sanitize(SecurityContext.HTML, StringUtils.replaceWithTags(raw, this.tagData()))
      }))
    );

  readonly postBottomHtml$ = this.http
    .get(environment.proxyUrl + this.customizationPath + "container-create.wizard.post.bottom.html", {
      responseType: "text"
    })
    .pipe(
      catchError(() => of("")),
      map((raw) => this.sanitizer.sanitize(SecurityContext.HTML, StringUtils.replaceWithTags(raw, this.tagData())))
    );

  constructor(
    private http: HttpClient,
    private sanitizer: DomSanitizer
  ) {
    super();
  }
}
