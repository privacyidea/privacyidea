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
import { Component, effect, inject, OnDestroy, OnInit, ViewChild } from "@angular/core";
import { FormsModule, NgForm } from "@angular/forms";
import { MatButton } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatDialog } from "@angular/material/dialog";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { AuthService } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { SmtpService, SmtpServiceInterface } from "@services/smtp/smtp.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { isChecked } from "@utils/parse-boolean-value";
import { SystemDocumentationDialogComponent } from "./system-documentation-dialog/system-documentation-dialog.component";

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
export class SystemConfigComponent implements OnInit, OnDestroy {
  private readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly authService: AuthService = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly dialog = inject(MatDialog);
  private readonly smtpService: SmtpServiceInterface = inject(SmtpService);
  private readonly pendingChangesService = inject(PendingChangesService);
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
        booleanKeys.forEach((key) => {
          if (this.params[key] !== undefined) {
            this.params[key] = isChecked(this.params[key]);
          }
        });
      }
    });

    // Keep SMTP identifiers in sync with the SMTP servers service
    effect(() => {
      const servers = this.smtpService.smtpServers();
      this.smtpIdentifiers = servers.map((s) => s.identifier);
    });
  }

  ngOnInit(): void {
    this.loadSystemConfig();
    this.smtpService.smtpServerResource.reload();
    this.pendingChangesService.registerHasChanges(() => this.systemConfigForm?.dirty ?? false);
    this.pendingChangesService.registerValidChanges(
      () => this.hasConfigWritePermission() && (this.systemConfigForm?.valid ?? false),
    );
    this.pendingChangesService.registerSave(() => this._saveAndReturn());
  }

  loadSystemConfig(): void {
    this.systemService.systemConfigResource.reload();
  }

  saveSystemConfig(): void {
    const body = { ...this.params };

    this.systemService.saveSystemConfig(body).subscribe({
      next: (response: any) => {
        if (response.result.status) {
          this.notificationService.success("System configuration saved successfully.");
        } else {
          this.notificationService.error("Failed to save system configuration.");
        }
      },
      error: (error: any) => {
        console.error("Error saving system configuration:", error);
        this.notificationService.error("Error saving system configuration.");
      }
    });
  }

  private _saveAndReturn(): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      this.systemService.saveSystemConfig({ ...this.params }).subscribe({
        next: (response: any) => {
          if (response.result.status) {
            this.notificationService.success("System configuration saved successfully.");
            resolve(true);
          } else {
            this.notificationService.error("Failed to save system configuration.");
            resolve(false);
          }
        },
        error: () => {
          this.notificationService.error("Error saving system configuration.");
          resolve(false);
        }
      });
    });
  }

  deleteUserCache(): void {
    this.systemService.deleteUserCache().subscribe({
      next: (response: any) => {
        if (response.result.status) {
          this.notificationService.success("User cache deleted successfully.");
        } else {
          this.notificationService.error("Failed to delete user cache.");
        }
      },
      error: (error: any) => {
        console.error("Error deleting user cache:", error);
        this.notificationService.error("Error deleting user cache.");
      }
    });
  }

  hasConfigWritePermission(): boolean {
    return this.authService.actionAllowed("configwrite");
  }

  protected readonly ROUTE_PATHS = ROUTE_PATHS;

  protected openDocumentationDialog() {
    this.systemService.getDocumentation().subscribe({
      next: (documentation) => {
        this.dialog.open(SystemDocumentationDialogComponent, {
          data: { documentation }
        });
      },
      error: (error: any) => {
        console.error("Error loading system documentation:", error);
        this.notificationService.error("Error loading system documentation.");
      }
    });
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }
}
