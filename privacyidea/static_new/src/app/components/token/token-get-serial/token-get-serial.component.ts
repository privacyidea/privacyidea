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
import { CommonModule } from "@angular/common";
import { HttpParams } from "@angular/common/http";
import { Component, effect, inject, linkedSignal, signal, WritableSignal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButton } from "@angular/material/button";
import { MatDialog } from "@angular/material/dialog";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatProgressBarModule } from "@angular/material/progress-bar";
import { MatOption, MatSelect } from "@angular/material/select";
import { Router } from "@angular/router";
import { Subscription } from "rxjs";
import { ROUTE_PATHS } from "../../../route_paths";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import { TokenService, TokenServiceInterface, TokenType } from "../../../services/token/token.service";
import { ConfirmationDialogComponent } from "../../shared/confirmation-dialog/confirmation-dialog.component";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { GetSerialResultDialogComponent } from "./get-serial-result-dialog/get-serial-result-dialog.component";

@Component({
  selector: "app-token-get-serial",
  imports: [
    FormsModule,
    MatProgressBarModule,
    MatFormField,
    MatInput,
    MatSelect,
    CommonModule,
    MatIcon,
    MatButton,
    MatHint,
    MatOption,
    MatError,
    MatLabel,
    ScrollToTopDirective
  ],
  templateUrl: "./token-get-serial.component.html",
  styleUrl: "./token-get-serial.component.scss"
})
export class TokenGetSerialComponent {
  otpValue = signal<string>("");
  tokenType = signal<string>("");
  assignmentState = signal<string>("");
  serialSubstring = signal<string>("");
  countWindow = signal<number>(10);
  currentStep = signal("init");
  foundSerial = signal<string>("");
  tokenCount = signal<string>("");
  serialSubscription: Subscription | null = null;
  assignmentStates = [
    { key: "assigned", info: "The token is assigned to a user" },
    { key: "unassigned", info: "The token is not assigned to a user" },
    {
      key: "don't care",
      info: "It does not matter, if the token is assigned or not"
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
  private readonly dialog: MatDialog = inject(MatDialog);
  private router = inject(Router);

  constructor() {

    effect(() => {
      this.otpValue();
      this.assignmentState();
      this.tokenType();
      this.serialSubstring();
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
    let params = new HttpParams();
    params = params.set("window", this.countWindow());

    if (this.assignmentState() === "assigned") {
      params = params.set("assigned", "1");
    }
    if (this.assignmentState() === "unassigned") {
      params = params.set("unassigned", "1");
    }
    if (this.tokenType() !== "") {
      params = params.set("type", this.tokenType());
    }
    if (this.serialSubstring() !== "") {
      params = params.set("serial", this.serialSubstring());
    }

    return params;
  }

  countTokens(): void {
    if (this.currentStep() !== "init" && this.currentStep() !== "found") {
      this.notificationService.openSnackBar("Invalid action.");
      return;
    }
    let params = this.getParams();
    params = params.set("count", "1");
    this.currentStep.set("counting");
    this.tokenService.getSerial(this.otpValue(), params).subscribe({
      next: (response) => {
        this.tokenCount.set(response?.result?.value?.count !== undefined ? String(response.result?.value.count) : "");
        this.currentStep.set("countDone");
        if (this.countIsLarge()) {
          this.dialog
            .open(ConfirmationDialogComponent, {
              data: {
                title: "Search Serial",
                action: "search",
                numberOfTokens: this.tokenCount()
              }
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
      this.notificationService.openSnackBar("Invalid action.");
      return;
    }
    let params = this.getParams();
    params = params.delete("count");
    this.currentStep.set("searching");
    this.serialSubscription = this.tokenService.getSerial(this.otpValue(), params).subscribe({
      next: (response) => {
        const serial = response.result?.value?.serial ?? "";
        this.dialog.open(GetSerialResultDialogComponent, {
          data: {
            foundSerial: serial,
            otpValue: this.otpValue(),
            onClickSerial: () => {
              this.tokenSerial.set(serial);
              this.router.navigateByUrl(ROUTE_PATHS.TOKENS_DETAILS + serial);
              this.dialog.closeAll();
            },
            reset: () => {
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
