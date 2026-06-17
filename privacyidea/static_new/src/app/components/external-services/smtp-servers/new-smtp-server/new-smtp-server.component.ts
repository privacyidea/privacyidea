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

import { Component, computed, effect, inject, OnDestroy, signal, untracked } from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { disabled, email, form, FormField, pattern, required } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { ActivatedRoute, Router } from "@angular/router";
import { SmtpServer, SmtpService, SmtpServiceInterface } from "@services/smtp/smtp.service";

import { MatIconModule } from "@angular/material/icon";
import { MatDivider } from "@angular/material/list";
import { MatTooltip } from "@angular/material/tooltip";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { NAVIGATION_ACCESSIBLE_DIALOG_CLASS } from "@constants/global.constants";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";

interface SmtpFormModel {
  identifier: string;
  server: string;
  port: number;
  timeout: number;
  sender: string;
  username: string;
  password: string;
  description: string;
  tls: boolean;
  enqueue_job: boolean;
  certificate: string;
  private_key: string;
  private_key_password: string;
  smime: boolean;
  dont_send_on_error: boolean;
  recipient: string;
}

const EMPTY_SMTP_FORM: SmtpFormModel = {
  identifier: "",
  server: "",
  port: 25,
  timeout: 10,
  sender: "",
  username: "",
  password: "",
  description: "",
  tls: true,
  enqueue_job: false,
  certificate: "",
  private_key: "",
  private_key_password: "",
  smime: false,
  dont_send_on_error: false,
  recipient: ""
};

@Component({
  selector: "app-smtp-edit-dialog",
  standalone: true,
  host: {
    class: NAVIGATION_ACCESSIBLE_DIALOG_CLASS
  },
  imports: [
    FormField,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatButtonModule,
    MatIconModule,
    MatTooltip,
    ClearableInputComponent,
    MatDivider,
    StickyHeaderDirective
  ],
  templateUrl: "./new-smtp-server.component.html",
  styleUrl: "./new-smtp-server.component.scss"
})
export class NewSmtpServerComponent implements OnDestroy {
  protected readonly smtpService: SmtpServiceInterface = inject(SmtpService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);

  protected data: SmtpServer | null = null;
  isEditMode = signal(false);
  isTesting = signal(false);
  private editIdentifier: string | null = null;
  private initialPrivateKeyPassword = "";

  smtpModel = signal<SmtpFormModel>({ ...EMPTY_SMTP_FORM });

  smtpForm = form(this.smtpModel, (f) => {
    required(f.identifier);
    pattern(f.identifier, /^[a-zA-Z0-9._-]*$/);
    required(f.server);
    required(f.sender);
    email(f.sender);
    disabled(f.identifier, () => this.isEditMode());
  });

  showTLS = computed(() => !this.smtpModel().server?.toLowerCase().startsWith("smtps:"));

  constructor() {
    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.save());
    this.pendingChangesService.registerValidChanges(() => this.canSave);

    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const identifier = params.get("identifier");
      if (identifier) {
        this.isEditMode.set(true);
        this.editIdentifier = identifier;
        this.data = this.smtpService.smtpServers().find((s) => s.identifier === identifier) ?? null;
      } else {
        this.isEditMode.set(false);
        this.editIdentifier = null;
        this.data = null;
      }
      this.loadData(this.data);
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const servers = this.smtpService.smtpServers();
      if (this.isEditMode() && this.editIdentifier && untracked(() => !this.smtpForm().dirty())) {
        const found = servers.find((s) => s.identifier === this.editIdentifier);
        if (found) {
          this.data = found;
          this.loadData(this.data);
        }
      }
    });
  }

  get hasChanges(): boolean {
    return this.smtpForm().dirty();
  }

  get canSave(): boolean {
    return this.smtpForm().valid();
  }

  private loadData(data: SmtpServer | null): void {
    this.smtpModel.set({
      identifier: data?.identifier || "",
      server: data?.server || "",
      port: data?.port || 25,
      timeout: data?.timeout || 10,
      sender: data?.sender || "",
      username: data?.username || "",
      password: data?.password || "",
      description: data?.description || "",
      tls: data?.tls ?? true,
      enqueue_job: data?.enqueue_job ?? false,
      certificate: data?.certificate || "",
      private_key: data?.private_key || "",
      private_key_password: data?.private_key_password || "",
      smime: data?.smime ?? false,
      dont_send_on_error: data?.dont_send_on_error ?? false,
      recipient: ""
    });
    this.smtpForm().reset();
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  async save(): Promise<boolean> {
    if (!this.smtpForm().valid()) {
      return false;
    }
    const model = this.smtpModel();
    const server = Object.fromEntries(Object.entries(model).filter(([k]) => k !== "recipient")) as Omit<
      typeof model,
      "recipient"
    >;

    if (server.private_key_password === this.initialPrivateKeyPassword) {
      delete (server as Partial<SmtpServer>).private_key_password;
    }

    try {
      await this.smtpService.postSmtpServer(server as SmtpServer);
      this.pendingChangesService.clearAllRegistrations();
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP);
      return true;
    } catch {
      return false;
    }
  }

  async test(): Promise<void> {
    if (this.smtpForm().valid()) {
      this.isTesting.set(true);
      const params = this.smtpModel();
      await this.smtpService.testSmtpServer(params);
      this.isTesting.set(false);
    }
  }

  onCancel(): void {
    if (this.hasChanges) {
      this.dialogService
        .openDialog({
          component: SaveAndExitDialogComponent,
          data: {
            allowSaveExit: true,
            saveExitDisabled: !this.canSave
          }
        })
        .afterClosed()
        .subscribe(async (result) => {
          if (result === "discard") {
            this.pendingChangesService.clearAllRegistrations();
            this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP);
          } else if (result === "save-exit") {
            if (!this.canSave) return;
            const success = await this.pendingChangesService.save();
            if (!success) return;
            this.pendingChangesService.clearAllRegistrations();
            this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP);
          }
        });
    } else {
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP);
    }
  }
}
