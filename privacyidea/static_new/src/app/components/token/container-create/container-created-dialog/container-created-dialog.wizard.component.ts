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
import { Component, computed, inject, SecurityContext, Signal } from "@angular/core";
import { MatDialogContent, MatDialogRef } from "@angular/material/dialog";
import { DomSanitizer } from "@angular/platform-browser";
import { map } from "rxjs";
import { ContainerService, ContainerServiceInterface } from "../../../../services/container/container.service";
import { ContainerCreatedDialogComponent } from "./container-created-dialog.component";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { StringUtils } from "../../../../utils/string.utils";
import { environment } from "../../../../../environments/environment";

@Component({
  selector: "app-container-created-wizard-dialog",
  imports: [MatDialogContent, AsyncPipe],
  templateUrl: "./container-created-dialog.wizard.component.html",
  styleUrl: "./container-created-dialog.component.scss"
})
export class ContainerCreatedDialogWizardComponent extends ContainerCreatedDialogComponent {
  protected override readonly containerService: ContainerServiceInterface = inject(ContainerService);
  public readonly authService: AuthServiceInterface = inject(AuthService);
  protected override readonly dialogRef: MatDialogRef<ContainerCreatedDialogWizardComponent> = inject(MatDialogRef);
  tagData: Signal<Record<string, string>> = computed(() => ({
    containerSerial: this.data().containerSerial(),
    containerRegistrationURL: this.data().response.result?.value?.container_url?.value || "",
    containerRegistrationQR: this.data().response.result?.value?.container_url?.img || ""
  }));

  // TODO: Get custom path from pi.cfg
  customizationPath = "/static/public/customize/";

  readonly postTopHtml$ = this.http
    .get(environment.proxyUrl + this.customizationPath + "container-create.wizard.post.top.html", {
      responseType: "text"
    })
    .pipe(map((raw) => ({
        hasContent: !!raw && raw.trim().length > 0,
        sanitized: this.sanitizer.sanitize(SecurityContext.HTML, StringUtils.replaceWithTags(raw, this.tagData()))
      }))
    );

  readonly postBottomHtml$ = this.http
    .get(environment.proxyUrl + this.customizationPath + "container-create.wizard.post.bottom.html", {
      responseType: "text"
    })
    .pipe(map((raw) => this.sanitizer.sanitize(SecurityContext.HTML,
      StringUtils.replaceWithTags(raw, this.tagData()))
    ));

  constructor(
    private http: HttpClient,
    private sanitizer: DomSanitizer
  ) {
    super();
  }
}
