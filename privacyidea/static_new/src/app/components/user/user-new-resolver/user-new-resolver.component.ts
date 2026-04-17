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
import {
  Component,
  AfterViewInit,
  OnDestroy,
  inject,
  Renderer2,
  DestroyRef,
  ViewChild,
  ElementRef,
  viewChild,
  signal,
  computed,
  effect,
  ResourceStatus
} from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { FormsModule, AbstractControl } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatCardModule } from "@angular/material/card";
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from "@angular/material/dialog";
import { MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatFormField, MatLabel, MatError } from "@angular/material/form-field";
import { MatSelectModule, MatSelect, MatOption } from "@angular/material/select";
import { Router, ActivatedRoute } from "@angular/router";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { NAVIGATION_ACCESSIBLE_DIALOG_CLASS } from "src/app/constants/global.constants";
import { ROUTE_PATHS } from "src/app/route_paths";
import { ContentService } from "src/app/services/content/content.service";
import { DialogServiceInterface, DialogService } from "src/app/services/dialog/dialog.service";
import { NotificationService } from "src/app/services/notification/notification.service";
import { PendingChangesService } from "src/app/services/pending-changes/pending-changes.service";
import { ResolverService, ResolverType } from "src/app/services/resolver/resolver.service";
import { EntraidResolverComponent } from "./entraid-resolver/entraid-resolver.component";
import { HttpResolverComponent } from "./http-resolver/http-resolver.component";
import { KeycloakResolverComponent } from "./keycloak-resolver/keycloak-resolver.component";
import { LdapResolverComponent } from "./ldap-resolver/ldap-resolver.component";
import { PasswdResolverComponent } from "./passwd-resolver/passwd-resolver.component";
import { ScimResolverComponent } from "./scim-resolver/scim-resolver.component";
import { SqlResolverComponent } from "./sql-resolver/sql-resolver.component";
import { finalize } from "rxjs";

@Component({
  selector: "app-user-new-resolver",
  standalone: true,
  host: {
    class: NAVIGATION_ACCESSIBLE_DIALOG_CLASS
  },
  imports: [
    FormsModule,
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
    LdapResolverComponent,
    SqlResolverComponent,
    ScimResolverComponent,
    HttpResolverComponent,
    EntraidResolverComponent,
    KeycloakResolverComponent,
    MatDialogModule,
    ClearableInputComponent
  ],
  templateUrl: "./user-new-resolver.component.html",
  styleUrl: "./user-new-resolver.component.scss"
})
export class UserNewResolverComponent implements AfterViewInit, OnDestroy {
  private readonly _resolverService = inject(ResolverService);
  private readonly _notificationService = inject(NotificationService);
  private readonly _router = inject(Router);
  private readonly _route = inject(ActivatedRoute);
  private readonly _contentService = inject(ContentService);
  private readonly _dialogService: DialogServiceInterface = inject(DialogService);
  private readonly _pendingChangesService = inject(PendingChangesService);
  private readonly _destroyRef = inject(DestroyRef);
  protected readonly _renderer: Renderer2 = inject(Renderer2);

  public readonly dialogRef = inject(MatDialogRef<UserNewResolverComponent>, { optional: true });
  public readonly data = inject(MAT_DIALOG_DATA, { optional: true });

  private _observer!: IntersectionObserver;
  private _editInitialized = false;
  private _initialRoute = this._contentService.routeUrl();

  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;
  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;

  ldapResolver = viewChild(LdapResolverComponent);
  sqlResolver = viewChild(SqlResolverComponent);
  passwdResolver = viewChild(PasswdResolverComponent);
  scimResolver = viewChild(ScimResolverComponent);
  httpResolver = viewChild(HttpResolverComponent);
  entraidResolver = viewChild(EntraidResolverComponent);
  keycloakResolver = viewChild(KeycloakResolverComponent);

  resolverName = "";
  resolverType: ResolverType = "passwdresolver";
  formData: Record<string, any> = { fileName: "/etc/passwd" };
  testUsername = "";
  testUserId = "";

  isSaving = signal(false);
  isTesting = signal(false);

  additionalFormFields = computed<Record<string, AbstractControl>>(() => {
    const resolver =
      this.ldapResolver() ||
      this.sqlResolver() ||
      this.passwdResolver() ||
      this.scimResolver() ||
      this.entraidResolver() ||
      this.keycloakResolver() ||
      this.httpResolver();

    return resolver ? resolver.controls() : {};
  });

  constructor() {
    const dialogResolver = this.data?.resolver;
    if (dialogResolver) {
      this.resolverName = dialogResolver.resolvername;
      this.resolverType = dialogResolver.type;
      this.formData = { ...(dialogResolver.data || {}) };
      this._editInitialized = true;
      this._resolverService.selectedResolverName.set(dialogResolver.resolvername);
    } else {
      this._route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
        this._resolverService.selectedResolverName.set(params.get("name") || "");
      });
    }

    if (this.dialogRef) {
      this.dialogRef.disableClose = true;
      this.dialogRef
        .backdropClick()
        .pipe(takeUntilDestroyed(this._destroyRef))
        .subscribe(() => {
          this.onCancel();
        });
      this.dialogRef
        .keydownEvents()
        .pipe(takeUntilDestroyed(this._destroyRef))
        .subscribe((event) => {
          if (event.key === "Escape") {
            this.onCancel();
          }
        });
    }

    this._pendingChangesService.registerHasChanges(() => this.hasChanges);
    this._pendingChangesService.registerSave(() => this.onSave());
    this._pendingChangesService.registerValidChanges(() => this.canSave);

    effect(() => {
      if (this._contentService.routeUrl() !== this._initialRoute) {
        this.dialogRef?.close(true);
      }
    });

    effect(() => {
      const selectedName = this._resolverService.selectedResolverName();
      const resourceRef = this._resolverService.selectedResolverResource;

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
          this.resolverName = resolver.resolvername || selectedName;
          this.resolverType = resolver.type;
          this.formData = { ...(resolver.data || {}) };
          this._editInitialized = true;
        }
      }
    });

    effect(() => {
      if (!this._contentService.routeUrl().startsWith(ROUTE_PATHS.USERS)) {
        this.dialogRef?.close(true);
      }
    });
  }

  get isEditMode(): boolean {
    return !!this._resolverService.selectedResolverName();
  }

  get isAdditionalFieldsInvalid(): boolean {
    const fields = Object.values(this.additionalFormFields());
    return fields.length > 0 && fields.some((control) => control.invalid);
  }

  get canSave(): boolean {
    const nameValid = this.resolverName.trim().length > 0;
    return nameValid && !!this.resolverType && !this.isAdditionalFieldsInvalid && !this.isSaving();
  }

  get hasChanges(): boolean {
    const fieldsDirty = Object.values(this.additionalFormFields()).some((control) => control.dirty);
    if (fieldsDirty) {
      return true;
    }
    if (this.isEditMode) {
      return this.testUsername !== "" || this.testUserId !== "";
    }
    return (
      this.resolverName !== "" ||
      this.resolverType !== "passwdresolver" ||
      this.testUsername !== "" ||
      this.testUserId !== ""
    );
  }

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) {
      return;
    }
    this._observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.rootBounds) {
          return;
        }
        const shouldFloat = entry.boundingClientRect.top < entry.rootBounds.top;
        if (shouldFloat) {
          this._renderer.addClass(this.stickyHeader.nativeElement, "is-sticky");
        } else {
          this._renderer.removeClass(this.stickyHeader.nativeElement, "is-sticky");
        }
      },
      { root: this.scrollContainer.nativeElement, threshold: [0, 1] }
    );
    this._observer.observe(this.stickySentinel.nativeElement);
  }

  ngOnDestroy(): void {
    this._resolverService.selectedResolverName.set("");
    this._pendingChangesService.clearAllRegistrations();
    this._observer?.disconnect();
  }

  onTypeChange(type: ResolverType): void {
    if (this.isEditMode) {
      return;
    }

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
    const name = this.resolverName.trim();
    if (!name) {
      this._notificationService.openSnackBar($localize`Please enter a resolver name.`);
      return false;
    }
    if (!this.resolverType) {
      this._notificationService.openSnackBar($localize`Please select a resolver type.`);
      return false;
    }
    if (this.isAdditionalFieldsInvalid) {
      this._notificationService.openSnackBar($localize`Please fill in all required fields.`);
      return false;
    }

    this.isSaving.set(true);
    const payload = {
      type: this.resolverType,
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
              this._notificationService.openSnackBar(
                this.isEditMode ? $localize`Resolver "${name}" updated.` : $localize`Resolver "${name}" created.`
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

  private _getAdditionalData(): Record<string, any> {
    return Object.entries(this.additionalFormFields()).reduce(
      (acc, [key, ctrl]) => {
        if (ctrl) {
          acc[key] = ctrl.value;
        }
        return acc;
      },
      {} as Record<string, any>
    );
  }

  private _runTest(quick: boolean): void {
    if (!this.resolverType) {
      this._notificationService.openSnackBar($localize`Please select a resolver type.`);
      return;
    }

    if (this.isAdditionalFieldsInvalid) {
      this._notificationService.openSnackBar($localize`Please fill in all required fields.`);
      return;
    }

    this.isTesting.set(true);

    const payload: any = {
      type: this.resolverType,
      ...this.formData,
      test_username: this.testUsername,
      test_userid: this.testUserId,
      ...this._getAdditionalData()
    };

    if (quick) {
      payload.SIZELIMIT = 1;
    }

    if (this.isEditMode) {
      payload.resolver = this.resolverName;
    }

    this._resolverService
      .postResolverTest(payload)
      .pipe(finalize(() => setTimeout(() => this.isTesting.set(false))))
      .subscribe({
        next: (res) => {
          if (res.result?.status === true && (res.result.value ?? 0) >= 0) {
            const detail = res.detail?.description || "";
            this._notificationService.openSnackBar($localize`Resolver test executed: ${detail}`, 20000);
          } else {
            this._notifyError($localize`Failed to test resolver.`, res, "Connection test failed.");
          }
        },
        error: (err) => this._notifyError($localize`Failed to test resolver.`, err, "Network error")
      });
  }

  private _notifyError(prefix: string, errorSource: any, testFallback?: string): void {
    const detail =
      errorSource.error?.result?.error?.message ||
      errorSource.error?.message ||
      errorSource.message ||
      errorSource.detail?.description ||
      errorSource.result?.error?.message ||
      $localize`Unknown server error.`;

    if (detail.includes("Detailed error")) {
      this._notificationService.openSnackBar(detail);
    } else if (testFallback && detail.includes(testFallback)) {
      this._notificationService.openSnackBar(detail);
    } else if (testFallback && detail === $localize`Unknown server error.`) {
      this._notificationService.openSnackBar(`${prefix} ${testFallback}`);
    } else {
      this._notificationService.openSnackBar(`${prefix} ${detail}`);
    }
  }

  private _resetForm(): void {
    this.resolverName = "";
    this.resolverType = "passwdresolver";
    this.formData = { fileName: "/etc/passwd" };
    this.testUsername = "";
    this.testUserId = "";
  }

  private _closeOrReset(): void {
    if (this.dialogRef) {
      this.dialogRef.close(true);
    } else if (!this.isEditMode) {
      this._resetForm();
      this._router.navigateByUrl(ROUTE_PATHS.USERS_RESOLVERS);
    }
  }

  private _closeCurrent(): void {
    this._pendingChangesService.clearAllRegistrations();
    if (this.dialogRef) {
      this.dialogRef.close();
    } else {
      this._router.navigateByUrl(ROUTE_PATHS.USERS_RESOLVERS);
    }
  }
}
