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

import { HttpErrorResponse } from "@angular/common/http";
import { Component, computed, effect, inject, OnDestroy, signal, viewChild } from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { form, FormField, pattern, required } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatCardModule } from "@angular/material/card";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect, MatSelectModule } from "@angular/material/select";
import { ActivatedRoute, Router } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { ResolverData, ResolverService, ResolverType } from "@services/resolver/resolver.service";
import { finalize } from "rxjs";
import { EntraidResolverComponent } from "./entraid-resolver/entraid-resolver.component";
import { HttpResolverComponent } from "./http-resolver/http-resolver.component";
import { KeycloakResolverComponent } from "./keycloak-resolver/keycloak-resolver.component";
import { LdapResolverComponent } from "./ldap-resolver/ldap-resolver.component";
import { PasswdResolverComponent } from "./passwd-resolver/passwd-resolver.component";
import { ScimResolverComponent } from "./scim-resolver/scim-resolver.component";
import { SqlResolverComponent } from "./sql-resolver/sql-resolver.component";

interface ResolverNameModel {
  resolverName: string;
}

@Component({
  selector: "app-user-new-resolver",
  standalone: true,
  imports: [
    FormField,
    MatFormField,
    MatLabel,
    MatError,
    MatInput,
    MatSelectModule,
    MatSelect,
    MatOption,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    PasswdResolverComponent,
    ScrollToTopDirective,
    StickyHeaderDirective,
    LdapResolverComponent,
    SqlResolverComponent,
    ScimResolverComponent,
    HttpResolverComponent,
    EntraidResolverComponent,
    KeycloakResolverComponent,
    ClearableInputComponent
  ],
  templateUrl: "./user-new-resolver.component.html",
  styleUrl: "./user-new-resolver.component.scss"
})
export class UserNewResolverComponent implements OnDestroy {
  private readonly _resolverService = inject(ResolverService);
  private readonly _notificationService = inject(NotificationService);
  private readonly _router = inject(Router);
  private readonly _route = inject(ActivatedRoute);
  private readonly _dialogService: DialogServiceInterface = inject(DialogService);
  private readonly _pendingChangesService = inject(PendingChangesService);

  private _editInitialized = false;

  ldapResolver = viewChild(LdapResolverComponent);
  sqlResolver = viewChild(SqlResolverComponent);
  passwdResolver = viewChild(PasswdResolverComponent);
  scimResolver = viewChild(ScimResolverComponent);
  httpResolver = viewChild(HttpResolverComponent);
  entraidResolver = viewChild(EntraidResolverComponent);
  keycloakResolver = viewChild(KeycloakResolverComponent);

  resolverType = signal<ResolverType>("passwdresolver");
  formData: ResolverData = { fileName: "/etc/passwd" };
  testUsername = signal<string>("");
  testUserId = signal<string>("");

  isSaving = signal(false);
  isTesting = signal(false);
  isEditMode = signal(false);

  // Resolver name form
  resolverNameModel = signal<ResolverNameModel>({ resolverName: "" });
  resolverNameForm = form(this.resolverNameModel, (f) => {
    required(f.resolverName);
    pattern(f.resolverName, /^[a-zA-Z0-9._-]*$/);
  });

  get resolverName(): string {
    return this.resolverNameModel().resolverName;
  }

  private _activeResolver = computed(() => {
    return (
      this.ldapResolver() ||
      this.sqlResolver() ||
      this.passwdResolver() ||
      this.scimResolver() ||
      this.entraidResolver() ||
      this.keycloakResolver() ||
      this.httpResolver()
    );
  });

  constructor() {
    this._route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      this._resolverService.selectedResolverName.set(params.get("name") || "");
    });

    this._pendingChangesService.registerHasChanges(() => this.hasChanges);
    this._pendingChangesService.registerSave(() => this.onSave());
    this._pendingChangesService.registerValidChanges(() => this.canSave);

    effect(() => {
      const selectedName = this._resolverService.selectedResolverName();
      const resourceRef = this._resolverService.selectedResolverResource;

      this.isEditMode.set(!!selectedName);

      if (!selectedName) {
        if (this._editInitialized) {
          this._resetForm();
          this._editInitialized = false;
        }
        return;
      }

      const status = resourceRef.status();
      if (status === "loading" || status === "reloading" || !resourceRef.hasValue()) {
        if (status === "reloading") {
          this._editInitialized = false;
        }
        return;
      }

      const resource = resourceRef.value();
      if (resource?.result?.value && !this._editInitialized) {
        const resolver = resource.result.value[selectedName];
        if (resolver) {
          this.resolverNameModel.set({ resolverName: resolver.resolvername || selectedName });
          this.resolverType.set(resolver.type);
          this.formData = { ...(resolver.data || {}) };
          this._editInitialized = true;
        }
      }
    });
  }

  get isAdditionalFieldsInvalid(): boolean {
    const resolver = this._activeResolver();
    if (!resolver) return false;
    return !resolver.isValid();
  }

  get canSave(): boolean {
    const name = this.resolverNameModel().resolverName;
    const nameValid = name.trim().length > 0 && /^[a-zA-Z0-9._-]*$/.test(name);
    return nameValid && !!this.resolverType() && !this.isAdditionalFieldsInvalid && !this.isSaving();
  }

  get hasChanges(): boolean {
    const resolver = this._activeResolver();
    const resolverDirty = resolver ? resolver.isDirty() : false;
    if (resolverDirty || this.resolverNameForm().dirty()) {
      return true;
    }
    if (this.isEditMode()) {
      return this.testUsername() !== "" || this.testUserId() !== "";
    }
    return (
      this.resolverNameModel().resolverName !== "" ||
      this.resolverType() !== "passwdresolver" ||
      this.testUsername() !== "" ||
      this.testUserId() !== ""
    );
  }

  ngOnDestroy(): void {
    this._resolverService.selectedResolverName.set("");
    this._pendingChangesService.clearAllRegistrations();
  }

  onTypeChange(type: ResolverType): void {
    if (this.isEditMode()) {
      return;
    }

    this.resolverType.set(type);

    if (type === "passwdresolver") {
      this.formData = { fileName: "/etc/passwd" };
    } else if (type === "ldapresolver") {
      this.formData = {
        TLS_VERSION: "TLSv1_3",
        TLS_VERIFY: true,
        SCOPE: "SUBTREE",
        AUTHTYPE: "Simple",
        TIMEOUT: 5,
        CACHE_TIMEOUT: 120,
        SIZELIMIT: 500,
        SERVERPOOL_ROUNDS: 2,
        SERVERPOOL_SKIP: 30,
        UIDTYPE: "DN"
      };
    } else {
      this.formData = {};
    }
  }

  async onSave(): Promise<boolean> {
    const name = this.resolverNameModel().resolverName.trim();
    if (!name) {
      this._notificationService.warning($localize`Please enter a resolver name.`);
      return false;
    }
    if (!this.resolverType()) {
      this._notificationService.warning($localize`Please select a resolver type.`);
      return false;
    }
    if (this.isAdditionalFieldsInvalid) {
      this._notificationService.warning($localize`Please fill in all required fields.`);
      return false;
    }

    this.isSaving.set(true);
    const payload = {
      type: this.resolverType(),
      ...this.formData,
      ...this._getAdditionalData()
    };

    return new Promise<boolean>((resolve) => {
      this._resolverService
        .postResolver(name, payload)
        .pipe(finalize(() => setTimeout(() => this.isSaving.set(false))))
        .subscribe({
          next: (res) => {
            if (res.result?.status === true && (res.result.value ?? 0) >= 0) {
              this._notificationService.success(
                this.isEditMode() ? $localize`Resolver "${name}" updated.` : $localize`Resolver "${name}" created.`
              );
              this._resolverService.resolversResource.reload?.();
              this._closeOrReset();
              resolve(true);
            } else {
              this._notifyError($localize`Failed to save resolver.`, res);
              resolve(false);
            }
          },
          error: (err) => {
            this._notifyError($localize`Failed to save resolver.`, err);
            resolve(false);
          },
          complete: () => setTimeout(() => this.isSaving.set(false))
        });
    });
  }

  onTest(): void {
    this._runTest(false);
  }

  onQuickTest(): void {
    this._runTest(true);
  }

  onCancel(): void {
    if (this.hasChanges) {
      this._dialogService
        .openDialog({
          component: SaveAndExitDialogComponent,
          data: {
            title: $localize`Discard changes`,
            allowSaveExit: this.canSave,
            saveExitDisabled: !this.canSave
          }
        })
        .afterClosed()
        .subscribe((result) => {
          if (result === "save-exit") {
            if (!this.canSave) return;
            Promise.resolve(this._pendingChangesService.save()).then((success) => {
              if (success) {
                this._closeCurrent();
              }
            });
          } else if (result === "discard") {
            this._closeCurrent();
          }
        });
    } else {
      this._closeCurrent();
    }
  }

  private _getAdditionalData(): ResolverData {
    const resolver = this._activeResolver();
    if (!resolver) return {};
    return resolver.getValue() as unknown as ResolverData;
  }

  private _runTest(quick: boolean): void {
    if (!this.resolverType()) {
      this._notificationService.warning($localize`Please select a resolver type.`);
      return;
    }

    if (this.isAdditionalFieldsInvalid) {
      this._notificationService.warning($localize`Please fill in all required fields.`);
      return;
    }

    this.isTesting.set(true);

    const payload: ResolverData = {
      type: this.resolverType(),
      ...this.formData,
      test_username: this.testUsername(),
      test_userid: this.testUserId(),
      ...this._getAdditionalData()
    };

    if (quick) {
      payload["SIZELIMIT"] = 1;
    }

    if (this.isEditMode()) {
      payload["resolver"] = this.resolverNameModel().resolverName;
    }

    this._resolverService
      .postResolverTest(payload)
      .pipe(finalize(() => setTimeout(() => this.isTesting.set(false))))
      .subscribe({
        next: (res) => {
          if (res.result?.status === true && res.result.value === true) {
            const detail = res.detail?.description || "";
            this._notificationService.success($localize`Resolver test executed: ${detail}`, { duration: 20000 });
          } else {
            this._notifyError($localize`Failed to test resolver.`, res, "Connection test failed.");
          }
        },
        error: (err) => this._notifyError($localize`Failed to test resolver.`, err, "Network error")
      });
  }

  private _notifyError(
    prefix: string,
    errorSource: HttpErrorResponse | PiResponse<unknown>,
    testFallback?: string
  ): void {
    const source = errorSource as Partial<HttpErrorResponse> &
      Partial<PiResponse<unknown, { description?: string } | undefined>>;
    const detail =
      source.error?.result?.error?.message ||
      source.error?.message ||
      source.message ||
      source.detail?.description ||
      source.result?.error?.message ||
      $localize`Unknown server error.`;

    if (detail.includes("Detailed error")) {
      this._notificationService.error(detail);
    } else if (testFallback && detail.includes(testFallback)) {
      this._notificationService.error(detail);
    } else if (testFallback && detail === $localize`Unknown server error.`) {
      this._notificationService.error(`${prefix} ${testFallback}`);
    } else {
      this._notificationService.error(`${prefix} ${detail}`);
    }
  }

  private _resetForm(): void {
    this.resolverNameModel.set({ resolverName: "" });
    this.resolverType.set("passwdresolver");
    this.formData = { fileName: "/etc/passwd" };
    this.testUsername.set("");
    this.testUserId.set("");
  }

  private _closeOrReset(): void {
    if (!this.isEditMode()) {
      this._resetForm();
    }
    this._closeCurrent();
  }

  private _closeCurrent(): void {
    this._pendingChangesService.clearAllRegistrations();
    this._router.navigateByUrl(ROUTE_PATHS.USERS_RESOLVERS);
  }
}
