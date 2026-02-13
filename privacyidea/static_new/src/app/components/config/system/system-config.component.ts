/*
 * (c) NetKnights GmbH 2025, https://netknights.it
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
 * License along with this program. If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Component, effect, inject, OnInit, ViewChild } from "@angular/core";
import { FormsModule, NgForm } from "@angular/forms";
import { SystemService, SystemServiceInterface } from "../../../services/system/system.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import { AuthService } from "../../../services/auth/auth.service";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { RouterLink } from "@angular/router";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { ROUTE_PATHS } from "../../../route_paths";
import { SystemDocumentationDialogComponent } from "./system-documentation-dialog/system-documentation-dialog.component";
import { MatDialog } from "@angular/material/dialog";

@Component({
  selector: "app-system-config",
  templateUrl: "./system-config.component.html",
  imports: [
    MatFormField,
    MatLabel,
    FormsModule,
    MatInput,
    MatSelect,
    MatOption,
    MatHint,
    RouterLink,
    MatCheckbox,
    ScrollToTopDirective,
    MatButton,
    MatIcon
  ],
  styleUrls: ["./system-config.component.scss"]
})
export class SystemConfigComponent implements OnInit {
  private readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly authService: AuthService = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly dialog = inject(MatDialog);
  @ViewChild("scrollContainer", { static: true }) scrollContainer!: ScrollToTopDirective;
  @ViewChild("systemConfigForm", { static: true }) systemConfigForm!: NgForm;

  params: any = {};
  smtpIdentifiers: string[] = [];

  constructor() {
    effect(() => {
      const config = this.systemService.systemConfig();
      if (config && Object.keys(config).length > 0) {
        this.params = { ...config };
        const booleanKeys = [
          "splitAtSign",
          "IncFailCountOnFalsePin",
          "no_auth_counter",
          "PrependPin",
          "ReturnSamlAttributes",
          "ReturnSamlAttributesOnFail",
          "AutoResync",
          "UiLoginDisplayHelpButton",
          "UiLoginDisplayRealmBox"
        ];
        booleanKeys.forEach(key => {
          if (this.params[key] !== undefined) {
            this.params[key] = this.isChecked(this.params[key]);
          }
        });
      }
    });
  }

  ngOnInit(): void {
    this.loadSystemConfig();
    this.loadSmtpIdentifiers();
  }

  loadSystemConfig(): void {
    this.systemService.systemConfigResource.reload();
  }

  loadSmtpIdentifiers(): void {
    this.systemService.loadSmtpIdentifiers().subscribe({
      next: (response: any) => {
        const smtpConfigs = response.result.value;
        this.smtpIdentifiers = Array.isArray(smtpConfigs) ? smtpConfigs : Object.keys(smtpConfigs || {});
      },
      error: (error: any) => {
        console.error("Error loading SMTP configurations:", error);
        this.smtpIdentifiers = [];
      }
    });
  }

  saveSystemConfig(): void {
    const body = { ...this.params };

    this.systemService.saveSystemConfig(body).subscribe({
      next: (response: any) => {
        if (response.result.status) {
          this.notificationService.openSnackBar("System configuration saved successfully.");
        } else {
          this.notificationService.openSnackBar("Failed to save system configuration.");
        }
      },
      error: (error: any) => {
        console.error("Error saving system configuration:", error);
        this.notificationService.openSnackBar("Error saving system configuration.");
      }
    });
  }

  deleteUserCache(): void {
    this.systemService.deleteUserCache().subscribe({
      next: (response: any) => {
        if (response.result.status) {
          this.notificationService.openSnackBar("User cache deleted successfully.");
        } else {
          this.notificationService.openSnackBar("Failed to delete user cache.");
        }
      },
      error: (error: any) => {
        console.error("Error deleting user cache:", error);
        this.notificationService.openSnackBar("Error deleting user cache.");
      }
    });
  }

  isChecked(value: any): boolean {
    return [true, 1, "1", "True", "true", "TRUE"].includes(value);
  }

  hasConfigWritePermission(): boolean {
    return this.authService.actionAllowed("configwrite");
  }

  protected readonly ROUTE_PATHS = ROUTE_PATHS;

  protected openDocumentationDialog() {
    this.systemService.getDocumentation().subscribe({
      next: (documentation) => {
        this.dialog.open(SystemDocumentationDialogComponent, {
          data: { documentation },
        });
      },
      error: (error: any) => {
        console.error("Error loading system documentation:", error);
        this.notificationService.openSnackBar("Error loading system documentation.");
      }
    });
  }
}