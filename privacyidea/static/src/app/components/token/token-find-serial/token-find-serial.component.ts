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
import { HttpParams } from "@angular/common/http";
import { Component, computed, effect, inject, linkedSignal, signal, WritableSignal } from "@angular/core";
import { disabled, form, FormField, min, required } from "@angular/forms/signals";
import { MatButton } from "@angular/material/button";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatProgressBarModule } from "@angular/material/progress-bar";
import { MatOption, MatSelect } from "@angular/material/select";
import { Router } from "@angular/router";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { FindSerialResultDialogComponent } from "@components/token/token-find-serial/find-serial-result-dialog/find-serial-result-dialog.component";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TokenService, TokenServiceInterface, TokenType } from "@services/token/token.service";
import { ERR, requiredNonBlank } from "@utils/form-rules.utils";
import { hasError, touchAll } from "@utils/form-state.utils";
import { Subscription } from "rxjs";
import { SearchTokenDialogComponent } from "./search-token-dialog/search-token-dialog";

interface FindSerialModel {
  otpValue: string;
  tokenType: string;
  assignmentState: string;
  serialSubstring: string;
  countWindow: number | null;
}

@Component({
  selector: "app-token-get-serial",
  imports: [
    FormField,
    MatProgressBarModule,
    MatFormField,
    MatInput,
    MatSelect,
    MatIcon,
    MatButton,
    MatHint,
    MatOption,
    MatError,
    MatLabel,
    ScrollToTopDirective
  ],
  templateUrl: "./token-find-serial.component.html",
  styleUrl: "./token-find-serial.component.scss"
})
export class TokenFindSerialComponent {
  protected readonly ERR = ERR;
  protected readonly hasError = hasError;
  currentStep = signal("init");
  searchModel = signal<FindSerialModel>({
    otpValue: "",
    tokenType: "",
    assignmentState: "",
    serialSubstring: "",
    countWindow: 10
  });
  searchForm = form(this.searchModel, (f) => {
    requiredNonBlank(f.otpValue);
    disabled(f.otpValue, () => this.currentStep() !== "init");
    required(f.countWindow);
    min(f.countWindow, 1);
  });
  // The button doubles as Stop while a search runs, so only the steps that start a search depend on validity.
  runSearchDisabled = computed(
    () => ["init", "found", "error"].includes(this.currentStep()) && !this.searchForm().valid()
  );
  foundSerial = signal<string>("");
  tokenCount = signal<string>("");
  serialSubscription: Subscription | null = null;
  assignmentStates = [
    { key: "assigned", info: $localize`:@@token.tokenAssigned:The token is assigned to a user` },
    { key: "unassigned", info: $localize`:@@token.tokenNotAssigned:The token is not assigned to a user` },
    {
      key: "don't care",
      info: $localize`:@@token.doesNotMatter:It does not matter, if the token is assigned or not`
    }
  ];
  tokenWithOTP = ["hotp", "totp", "spass", "motp", "sshkey", "yubikey", "remote", "yubico", "radius", "sms"];
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  tokenSerial = this.tokenService.tokenSerial;
  tokenTypesWithOTP: WritableSignal<TokenType[]> = linkedSignal({
    source: this.tokenService.tokenTypeOptions,
    computation: (tokenTypeOptions: TokenType[]) =>
      tokenTypeOptions.filter((type) => this.tokenWithOTP.includes(type.key))
  });
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private router = inject(Router);

  constructor() {
    effect(() => {
      this.searchForm.otpValue().value();
      this.searchForm.assignmentState().value();
      this.searchForm.tokenType().value();
      this.searchForm.serialSubstring().value();
      this.resetSteps();
    });
  }

  onClickRunSearch(): void {
    switch (this.currentStep()) {
      case "init":
      case "found":
      case "error":
        this.countTokens();
        break;
      case "countDone":
      case "counting":
      case "searching":
        this.resetSteps();
        break;
    }
  }

  getParams(): HttpParams {
    const { countWindow, assignmentState, tokenType, serialSubstring } = this.searchModel();
    let params = new HttpParams();
    if (countWindow !== null) {
      params = params.set("window", countWindow);
    }
    if (assignmentState === "assigned") {
      params = params.set("assigned", "1");
    }
    if (assignmentState === "unassigned") {
      params = params.set("unassigned", "1");
    }
    if (tokenType !== "") {
      params = params.set("type", tokenType);
    }
    if (serialSubstring !== "") {
      params = params.set("serial", serialSubstring);
    }

    return params;
  }

  countTokens(): void {
    if (this.currentStep() !== "init" && this.currentStep() !== "found") {
      this.notificationService.warning($localize`:@@token.invalidAction:Invalid action.`);
      return;
    }
    if (!this.searchForm().valid()) {
      void touchAll(this.searchForm);
      return;
    }
    let params = this.getParams();
    params = params.set("count", "1");
    this.currentStep.set("counting");
    this.tokenService.getSerial(this.searchModel().otpValue, params).subscribe({
      next: (response) => {
        this.tokenCount.set(response?.result?.value?.count !== undefined ? String(response.result?.value.count) : "");
        this.currentStep.set("countDone");
        if (this.countIsLarge()) {
          this.dialogService
            .openDialog({
              component: SearchTokenDialogComponent,
              data: this.tokenCount()
            })
            .afterClosed()
            .subscribe({
              next: (result) => {
                if (result) {
                  this.findSerial();
                } else {
                  this.resetSteps();
                }
              }
            });
        } else {
          this.findSerial();
        }
      },
      error: () => {
        this.currentStep.set("error");
      }
    });
  }

  findSerial(): void {
    if (this.currentStep() !== "countDone") {
      this.notificationService.warning($localize`:@@token.invalidAction:Invalid action.`);
      return;
    }
    let params = this.getParams();
    params = params.delete("count");
    this.currentStep.set("searching");
    this.serialSubscription = this.tokenService.getSerial(this.searchModel().otpValue, params).subscribe({
      next: (response) => {
        const serial = response.result?.value?.serial ?? "";
        const afterClosed = this.dialogService
          .openDialog({
            component: FindSerialResultDialogComponent,
            data: {
              foundSerial: serial,
              otpValue: this.searchModel().otpValue
            }
          })
          .afterClosed();
        afterClosed.subscribe({
          next: (result) => {
            if (result === "reset") {
              this.resetSteps();
            }
          }
        });
        this.foundSerial.set(serial);
        this.currentStep.set("found");
      }
    });
  }

  resetSteps(): void {
    this.serialSubscription?.unsubscribe();
    this.serialSubscription = null;
    this.currentStep.set("init");
    this.foundSerial.set("");
    this.tokenCount.set("");
  }

  countIsLarge(): boolean {
    return parseInt(this.tokenCount()) > 99;
  }
}
