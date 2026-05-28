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

import { AfterViewInit, Component, computed, inject, OnDestroy, OnInit, signal } from "@angular/core";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatOption } from "@angular/material/core";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatError, MatFormField, MatHint, MatLabel, MatSelect } from "@angular/material/select";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";

@Component({
  selector: "app-token-import",
  templateUrl: "./token-import.component.html",
  styleUrl: "./token-import.component.scss",
  imports: [
    MatFormField,
    MatSelect,
    MatOption,
    ScrollToTopDirective,
    StickyHeaderDirective,
    MatLabel,
    MatButton,
    MatInput,
    MatHint,
    MatIcon,
    MatIconButton,
    MatError
  ]
})
export class TokenImportComponent implements OnDestroy, OnInit, AfterViewInit {
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  ngAfterViewInit(): void {
    throw new Error("Method not implemented.");
  }
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly pendingChangesService = inject(PendingChangesService);
  protected readonly Object = Object;
  fileTypes: Record<string, string> = {
    "OATH CSV": "CSV File for OATH Tokens",
    "Yubikey CSV": "CSV File for Yubikey Tokens",
    pskc: "PSKC File",
    "aladdin-xml": "XML File from Aladdin or SafeNet"
  };
  fileType = signal<string>("OATH CSV");
  fileName = signal("");
  file = signal<string | File>("");
  preSharedKey = signal("");
  pskPassword = signal("");
  pskValidationOptions: Record<string, string> = {
    no_check: "Do not verify the authenticity",
    check_fail_soft: "Skip tokens that can not be verified",
    check_fail_hard: "Abort operation on unverifiable token"
  };
  pskValidation = signal("check_fail_hard");
  selectedRealms = signal<string[]>(this.realmService.defaultRealm() ? [this.realmService.defaultRealm()!] : []);

  readonly preSharedKeyValid = computed(() => [0, 32].includes(this.preSharedKey().length));
  readonly formValid = computed(() => !!this.file() && this.preSharedKeyValid());

  ngOnInit(): void {
    this.pendingChangesService.registerHasChanges(
      () =>
        this.fileName() !== "" ||
        this.pskPassword() !== "" ||
        this.fileType() !== "OATH CSV" ||
        this.pskValidation() !== "check_fail_hard"
    );
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.file.set(input.files[0]);
      this.fileName.set(input.files[0].name);
    } else {
      this.fileName.set("");
    }
  }

  importTokens() {
    if (this.formValid()) {
      const formData = new FormData();
      formData.append("file", this.file() as File);
      formData.append("type", this.fileType());
      if (this.selectedRealms()) {
        formData.append("tokenrealms", this.selectedRealms().join(","));
      }
      if (this.fileType() === "pskc") {
        if (this.pskPassword()) {
          formData.append("password", this.pskPassword());
        }
        if (this.preSharedKey()) {
          formData.append("psk", this.preSharedKey());
        }
        formData.append("pskcValidateMAC", this.pskValidation());
      }

      this.tokenService.importTokens(this.fileName(), formData).subscribe({
        next: (result) => {
          // Handle successful import, e.g., show a notification
          const success = result.result?.value?.n_imported || 0;
          const failed = result.result?.value?.n_not_imported || 0;
          const total = success + failed;
          this.notificationService.success(success + "/" + total + " tokens imported successfully.");
        },
        error: () => {
          // error handled in the token service
        }
      });
    }
  }

  clearFileSelection() {
    this.file.set("");
    this.fileName.set("");
  }
}
