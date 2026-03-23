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
import { MatError, MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatOption, MatSelect, MatSelectModule } from "@angular/material/select";
import { Router, ActivatedRoute } from "@angular/router";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { PiResponse } from "src/app/app.component";
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

@Component({
  selector: "app-user-new-resolver",
  standalone: true,
  imports: [
    ClearableInputComponent,
    EntraidResolverComponent,
    FormsModule,
    HttpResolverComponent,
    KeycloakResolverComponent,
    LdapResolverComponent,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatError,
    MatFormField,
    MatIconModule,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    MatSelectModule,
    PasswdResolverComponent,
    ScrollToTopDirective,
    ScimResolverComponent,
    SqlResolverComponent
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

  protected readonly renderer: Renderer2 = inject(Renderer2);
  public readonly dialogRef = inject(MatDialogRef<UserNewResolverComponent>, { optional: true });
  public readonly data = inject(MAT_DIALOG_DATA, { optional: true });

  private _observer!: IntersectionObserver;
  private _editInitialized = false;

  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;
  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;
  @ViewChild("leftColumn") leftColumn!: ElementRef<HTMLElement>;

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
    return resolver?.controls() ?? {};
  });

  constructor() {
    const dialogResolver = this.data?.resolver;
    const dialogResolverName = this.data?.resolverName || dialogResolver?.resolvername;

    if (dialogResolver) {
      this.resolverName = dialogResolver.resolvername;
      this.resolverType = dialogResolver.type;
      this.formData = { ...(dialogResolver.data || {}) };
      this._editInitialized = true;
      this._resolverService.selectedResolverName.set(dialogResolver.resolvername);
    } else if (dialogResolverName) {
      this._resolverService.selectedResolverName.set(dialogResolverName);
    } else {
      this._route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
        this._resolverService.selectedResolverName.set(params.get("name") || "");
      });
    }

    if (this.dialogRef) {
      this.dialogRef.disableClose = true;
      this.dialogRef.backdropClick().subscribe(() => this.onCancel());
      this.dialogRef.keydownEvents().subscribe((event) => {
        if (event.key === "Escape") this.onCancel();
      });
    }

    this._pendingChangesService.registerHasChanges(() => this.hasChanges);
    this._pendingChangesService.registerSave(() => this.onSave());

    effect(() => {
      if (!this._contentService.routeUrl().startsWith(ROUTE_PATHS.USERS)) {
        this.dialogRef?.close(true);
      }
    });

    effect(() => {
      const selectedName = this._resolverService.selectedResolverName();

      if (!selectedName) {
        if (this._editInitialized) {
          this.resolverName = "";
          this.resolverType = "passwdresolver";
          this.formData = { fileName: "/etc/passwd" };
          this._editInitialized = false;
        }
        return;
      }

      const resourceRef = this._resolverService.selectedResolverResource;
      const status = resourceRef.status();

      if (status === ResourceStatus.Loading || status === ResourceStatus.Reloading) {
        if (status === ResourceStatus.Reloading) this._editInitialized = false;
        return;
      }

      const resource = resourceRef.value();
      if (!resource?.result?.value || this._editInitialized) return;

      const resolver = resource.result.value[selectedName];
      if (resolver) {
        this.resolverName = resolver.resolvername || selectedName;
        this.resolverType = resolver.type;
        this.formData = { ...(resolver.data || {}) };
        this._editInitialized = true;
      }
    });
  }

  get isEditMode(): boolean {
    return !!this._resolverService.selectedResolverName();
  }

  get isAdditionalFieldsValid(): boolean {
    const fields = Object.values(this.additionalFormFields());
    return fields.length > 0 && fields.every((control) => control.valid);
  }

  get canSave(): boolean {
    return (
      this.resolverName.trim().length > 0 && !!this.resolverType && this.isAdditionalFieldsValid && !this.isSaving()
    );
  }

  get hasChanges(): boolean {
    const fieldsDirty = Object.values(this.additionalFormFields()).some((control) => control.dirty);
    if (fieldsDirty) return true;

    const testDirty = this.testUsername !== "" || this.testUserId !== "";
    if (this.isEditMode) return testDirty;

    return this.resolverName !== "" || this.resolverType !== "passwdresolver" || testDirty;
  }

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel || !this.leftColumn) return;

    this._observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.rootBounds) return;
        const shouldFloat = entry.boundingClientRect.top < entry.rootBounds.top;
        this.renderer[shouldFloat ? "addClass" : "removeClass"](this.stickyHeader.nativeElement, "is-sticky");
      },
      { root: this.scrollContainer.nativeElement, threshold: [0, 1] }
    );

    this._observer.observe(this.stickySentinel.nativeElement);
  }

  ngOnDestroy(): void {
    this._resolverService.selectedResolverName.set("");
    this._pendingChangesService.unregisterHasChanges();
    this._observer?.disconnect();
  }

  onTypeChange(type: ResolverType): void {
    if (this.isEditMode) return;

    this.formData = {};
    if (type === "passwdresolver") {
      this.formData = { fileName: "/etc/passwd" };
    } else if (type === "ldapresolver") {
      this.formData = {
        TLS_VERSION: "TLSv1_3",
        TLS_VERIFY: true,
        SCOPE: "SUBTREE",
        AUTHTYPE: "simple",
        TIMEOUT: 5,
        CACHE_TIMEOUT: 120,
        SIZELIMIT: 500,
        SERVERPOOL_ROUNDS: 2,
        SERVERPOOL_SKIP: 30,
        UIDTYPE: "DN"
      };
    }
  }

  async onSave(): Promise<void> {
    const name = this.resolverName.trim();
    if (!name || !this.resolverType || !this.isAdditionalFieldsValid) {
      this._notificationService.openSnackBar($localize`Please check the required fields.`);
      return;
    }

    const additionalData = Object.entries(this.additionalFormFields()).reduce(
      (acc, [key, control]) => {
        if (control) acc[key] = control.value;
        return acc;
      },
      {} as Record<string, any>
    );

    const payload = { type: this.resolverType, ...this.formData, ...additionalData };
    this.isSaving.set(true);

    this._resolverService.postResolver(name, payload).subscribe({
      next: (res: PiResponse<any, any>) => {
        if (res.result?.status === true && (res.result.value ?? 0) >= 0) {
          this._handleSaveSuccess(name);
        } else {
          this._handleSaveError(res.detail?.description || res.result?.error?.message || $localize`Unknown error.`);
        }
      },
      error: (err: HttpErrorResponse) => this._handleSaveError(err.error?.result?.error?.message || err.message),
      complete: () => this.isSaving.set(false)
    });
  }

  onTest(): void {
    this._executeTest();
  }

  onQuickTest(): void {
    this._executeTest(true);
  }

  onCancel(): void {
    if (!this.hasChanges) {
      this._closeCurrent();
      return;
    }

    this._dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`Discard changes`,
          confirmAction: { label: "Save and exit", type: "confirm", value: true },
          items: [this.resolverName || "New Resolver"],
          itemType: "resolver"
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result === true) {
          if (!this.canSave) return;
          this._pendingChangesService.save().then(() => {
            this._pendingChangesService.unregisterHasChanges();
            this._closeCurrent();
          });
        } else if (result === false) {
          this._pendingChangesService.unregisterHasChanges();
          this._closeCurrent();
        }
      });
  }

  private _handleSaveSuccess(name: string): void {
    this._notificationService.openSnackBar(
      this.isEditMode ? $localize`Resolver "${name}" updated.` : $localize`Resolver "${name}" created.`
    );
    this._resolverService.resolversResource.reload?.();

    if (this.dialogRef) {
      this.dialogRef.close(true);
    } else if (!this.isEditMode) {
      this._resetForm();
      this._router.navigateByUrl(ROUTE_PATHS.USERS_RESOLVERS);
    }
  }

  private _handleSaveError(message: string): void {
    this._notificationService.openSnackBar($localize`Failed to save resolver. ${message}`);
  }

  private _resetForm(): void {
    this.resolverName = "";
    this.formData = {};
  }

  private _closeCurrent(): void {
    if (this.dialogRef) {
      this.dialogRef.close();
    } else {
      this._router.navigateByUrl(ROUTE_PATHS.USERS_RESOLVERS);
    }
  }

  private _executeTest(quickTest = false): void {
    if (!this.resolverType || !this.isAdditionalFieldsValid) {
      this._notificationService.openSnackBar($localize`Please check required fields.`);
      return;
    }

    this.isTesting.set(true);
    const payload: any = {
      type: this.resolverType,
      ...this.formData,
      test_username: this.testUsername,
      test_userid: this.testUserId,
      ...(quickTest ? { SIZELIMIT: 1 } : {}),
      ...(this.isEditMode ? { resolver: this.resolverName } : {})
    };

    Object.entries(this.additionalFormFields()).forEach(([key, control]) => {
      if (control) payload[key] = control.value;
    });

    this._resolverService.postResolverTest(payload).subscribe({
      next: (res: PiResponse<any, any>) => {
        const success = res.result?.status === true && (res.result.value ?? 0) >= 0;
        const msg = success
          ? $localize`Test executed: ${res.detail.description}`
          : $localize`Test failed. ${res.detail?.description || res.result?.error?.message}`;
        this._notificationService.openSnackBar(msg, success ? 20000 : 5000);
      },
      error: (err: HttpErrorResponse) => this._notificationService.openSnackBar($localize`Error: ${err.message}`),
      complete: () => setTimeout(() => this.isTesting.set(false))
    });
  }
}
