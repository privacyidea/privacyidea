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

import { Component, computed, inject, Signal } from "@angular/core";
import { MatDialogActions, MatDialogClose, MatDialogContent } from "@angular/material/dialog";
import { MatButton } from "@angular/material/button";
import { ContainerRegistrationCompletedDialogComponent } from "./container-registration-completed-dialog.component";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { map } from "rxjs";
import { StringUtils } from "../../../../utils/string.utils";
import { HttpClient } from "@angular/common/http";
import { DomSanitizer } from "@angular/platform-browser";
import { AsyncPipe } from "@angular/common";

@Component({
  selector: "app-container-registration-completed-dialog-wizard",
  templateUrl: "./container-registration-completed-dialog.wizard.component.html",
  styleUrls: ["./container-registration-completed-dialog.component.scss"],
  imports: [
    MatDialogContent,
    MatDialogActions,
    MatButton,
    MatDialogClose,
    AsyncPipe
  ]
})
export class ContainerRegistrationCompletedDialogWizardComponent extends ContainerRegistrationCompletedDialogComponent {
  public readonly authService: AuthServiceInterface = inject(AuthService);

  tagData: Signal<Record<string, string>> = computed(() => ({
    containerSerial: this.data.containerSerial
  }));

  readonly registeredHtml$ = this.http
    .get("/static/public/customize/container-create.wizard.registered.html", {
      responseType: "text"
    })
    .pipe(map((raw) => ({
        hasContent: !!raw && raw.trim().length > 0,
        sanitized: this.sanitizer.bypassSecurityTrustHtml(StringUtils.replaceWithTags(raw, this.tagData()))
      }))
    );

  constructor(
    private http: HttpClient,
    private sanitizer: DomSanitizer
  ) {
    super();
  }
}