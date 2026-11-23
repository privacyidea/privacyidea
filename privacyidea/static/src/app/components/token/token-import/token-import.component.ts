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

import { Component, computed, inject, OnDestroy, OnInit, signal } from "@angular/core";
import { disabled, form, FormField, validate } from "@angular/forms/signals";
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
import { hasError } from "@utils/form-state.utils";

const DEFAULT_FILE_TYPE = "OATH CSV";
const DEFAULT_PSK_VALIDATION = "check_fail_hard";
const PSK_LENGTH_ERROR = "pskLength";

interface TokenImportModel {
  fileType: string;
  preSharedKey: string;
  pskPassword: string;
  pskValidation: string;
  selectedRealms: string[];
}

@Component({
  selector: "app-token-import",
  templateUrl: "./token-import.component.html",
  styleUrl: "./token-import.component.scss",
  imports: [
    FormField,
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
export class TokenImportComponent implements OnDestroy, OnInit {
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly pendingChangesService = inject(PendingChangesService);
  protected readonly Object = Object;
  protected readonly hasError = hasError;
  protected readonly PSK_LENGTH_ERROR = PSK_LENGTH_ERROR;
  fileTypes: Record<string, string> = {
    "OATH CSV": $localize`:@@token.csvFileOathTokens:CSV File for OATH Tokens`,
    "Yubikey CSV": $localize`:@@token.csvFileYubikey:CSV File for Yubikey Tokens`,
    pskc: $localize`:@@token.pskcFile:PSKC File`,
    "aladdin-xml": $localize`:@@token.xmlFileFromAladdin:XML File from Aladdin or SafeNet`
  };
  fileName = signal("");
  file = signal<string | File>("");
  pskValidationOptions: Record<string, string> = {
    no_check: $localize`:@@token.doNotVerifyAuthenticity:Do not verify the authenticity`,
    check_fail_soft: $localize`:@@token.skipTokensNot:Skip tokens that can not be verified`,
    check_fail_hard: $localize`:@@token.abortOperation:Abort operation on unverifiable token`
  };
  importModel = signal<TokenImportModel>({
    fileType: DEFAULT_FILE_TYPE,
    preSharedKey: "",
    pskPassword: "",
    pskValidation: DEFAULT_PSK_VALIDATION,
    selectedRealms: this.realmService.defaultRealm() ? [this.realmService.defaultRealm()!] : []
  });
  // The pre shared key only applies to PSKC files, so it is exempt from validation for every other file type.
  importForm = form(this.importModel, (f) => {
    disabled(f.preSharedKey, () => this.importModel().fileType !== "pskc");
    validate(f.preSharedKey, (ctx) => ([0, 32].includes(ctx.value().length) ? [] : [{ kind: PSK_LENGTH_ERROR }]));
  });
  readonly canImport = computed(() => !!this.file() && this.importForm().valid());

  ngOnInit(): void {
    this.pendingChangesService.registerHasChanges(() => this.fileName() !== "" || this.importForm().dirty());
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
    if (this.canImport()) {
      const { fileType, preSharedKey, pskPassword, pskValidation, selectedRealms } = this.importModel();
      const formData = new FormData();
      formData.append("file", this.file() as File);
      formData.append("type", fileType);
      formData.append("tokenrealms", selectedRealms.join(","));
      if (fileType === "pskc") {
        if (pskPassword) {
          formData.append("password", pskPassword);
        }
        if (preSharedKey) {
          formData.append("psk", preSharedKey);
        }
        formData.append("pskcValidateMAC", pskValidation);
      }

      this.tokenService.importTokens(this.fileName(), formData).subscribe({
        next: (result) => {
          // Handle successful import, e.g., show a notification
          const success = result.result?.value?.n_imported || 0;
          const failed = result.result?.value?.n_not_imported || 0;
          const total = success + failed;
          this.notificationService.success(
            $localize`:@@token.tokensImported:${success}:SUCCESS:/${total}:TOTAL: tokens imported successfully.`
          );
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
