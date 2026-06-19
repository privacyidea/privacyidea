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
import { Component, effect, inject, OnDestroy, signal, untracked } from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { disabled, form, FormField, pattern, required } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatTooltip } from "@angular/material/tooltip";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import {
  RadiusServer,
  RadiusServerService,
  RadiusServerServiceInterface
} from "@services/radius-server/radius-server.service";

interface RadiusFormModel {
  identifier: string;
  server: string;
  port: number;
  timeout: number;
  retries: number;
  secret: string;
  message_authenticator: boolean;
  dictionary: string;
  description: string;
  username: string;
  password: string;
}

const EMPTY_RADIUS_FORM: RadiusFormModel = {
  identifier: "",
  server: "",
  port: 1812,
  timeout: 5,
  retries: 3,
  secret: "",
  message_authenticator: true,
  dictionary: "",
  description: "",
  username: "",
  password: ""
};

@Component({
  selector: "app-new-radius-server",
  standalone: true,
  imports: [
    FormField,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatButtonModule,
    MatIconModule,
    MatTooltip,
    ClearableInputComponent,
    ScrollToTopDirective,
    StickyHeaderDirective
  ],
  templateUrl: "./new-radius-server.component.html",
  styleUrl: "./new-radius-server.component.scss"
})
export class NewRadiusServerComponent implements OnDestroy {
  protected readonly radiusService: RadiusServerServiceInterface = inject(RadiusServerService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly authService: AuthServiceInterface = inject(AuthService);

  isEditMode = signal(false);
  isTesting = signal(false);
  private editIdentifier: string | null = null;

  radiusModel = signal<RadiusFormModel>({ ...EMPTY_RADIUS_FORM });

  radiusForm = form(this.radiusModel, (f) => {
    required(f.identifier);
    pattern(f.identifier, /^[a-zA-Z0-9._-]*$/);
    required(f.server);
    required(f.secret);
    disabled(f.identifier, () => this.isEditMode());
  });

  constructor() {
    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.save());
    this.pendingChangesService.registerValidChanges(() => this.canSave);

    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const identifier = params.get("identifier");
      if (identifier) {
        this.isEditMode.set(true);
        this.editIdentifier = identifier;
        const server = this.radiusService.radiusServers().find((s) => s.identifier === identifier);
        this.loadData(server ?? null);
      } else {
        this.isEditMode.set(false);
        this.editIdentifier = null;
        this.loadData(null);
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const servers = this.radiusService.radiusServers();
      if (this.isEditMode() && this.editIdentifier && untracked(() => !this.radiusForm().dirty())) {
        const found = servers.find((s) => s.identifier === this.editIdentifier);
        if (found) {
          this.loadData(found);
        }
      }
    });
  }

  get hasChanges(): boolean {
    return this.radiusForm().dirty();
  }

  get canSave(): boolean {
    return this.authService.actionAllowed("radiusserver_write") && this.radiusForm().valid();
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  private loadData(data: RadiusServer | null): void {
    this.radiusModel.set({
      identifier: data?.identifier || "",
      server: data?.server || "",
      port: data?.port || 1812,
      timeout: data?.timeout || 5,
      retries: data?.retries || 3,
      secret: data?.secret || "",
      message_authenticator: data?.options?.message_authenticator ?? true,
      dictionary: data?.dictionary || "",
      description: data?.description || "",
      username: "",
      password: ""
    });
    this.radiusForm().reset();
  }

  async save(): Promise<boolean> {
    if (!this.radiusForm().valid()) {
      return false;
    }
    const model = this.radiusModel();
    const server: RadiusServer = {
      identifier: model.identifier,
      server: model.server,
      port: model.port,
      timeout: model.timeout,
      retries: model.retries,
      secret: model.secret,
      dictionary: model.dictionary,
      description: model.description,
      options: {
        message_authenticator: model.message_authenticator
      }
    };
    try {
      await this.radiusService.postRadiusServer(server);
      this.pendingChangesService.clearAllRegistrations();
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS);
      return true;
    } catch {
      return false;
    }
  }

  test(): void {
    if (this.radiusForm().valid()) {
      this.isTesting.set(true);
      const model = this.radiusModel();
      const params = {
        ...model,
        options: {
          message_authenticator: model.message_authenticator
        }
      };
      this.radiusService.testRadiusServer(params).then(() => {
        this.isTesting.set(false);
      });
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
        .subscribe((result) => {
          if (result === "discard") {
            this.pendingChangesService.clearAllRegistrations();
            this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS);
          } else if (result === "save-exit") {
            if (!this.canSave) return;
            Promise.resolve(this.pendingChangesService.save()).then((success) => {
              if (!success) return;
              this.pendingChangesService.clearAllRegistrations();
              this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS);
            });
          }
        });
    } else {
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS);
    }
  }
}
