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
import { FormsModule } from "@angular/forms";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatDialog } from "@angular/material/dialog";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
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

@Component({
  selector: "app-container-create-wizard",
  imports: [
    MatButton,
    MatFormField,
    MatHint,
    MatIcon,
    MatOption,
    MatSelect,
    FormsModule,
    MatInput,
    MatLabel,
    MatCheckbox,
    MatIconButton,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelTitle,
    MatExpansionPanelHeader,
    AsyncPipe,
    ScrollToTopDirective
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

  readonly preTopHtml$ = this.http
    .get("/customize/container-create.wizard.pre.top.html", {
      responseType: "text"
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  readonly preBottomHtml$ = this.http
    .get("/customize/container-create.wizard.pre.bottom.html", {
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
