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
import {
  AfterViewInit,
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  OnDestroy,
  Renderer2,
  ResourceStatus,
  signal,
  ViewChild,
  viewChild
} from "@angular/core";
import { AbstractControl, FormsModule } from "@angular/forms";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { MatOption } from "@angular/material/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatCardModule } from "@angular/material/card";
import { HttpErrorResponse } from "@angular/common/http";
import { PiResponse } from "../../../app.component";

import { ResolverService, ResolverType } from "../../../services/resolver/resolver.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { PasswdResolverComponent } from "./passwd-resolver/passwd-resolver.component";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { LdapResolverComponent } from "./ldap-resolver/ldap-resolver.component";
import { SqlResolverComponent } from "./sql-resolver/sql-resolver.component";
import { ScimResolverComponent } from "./scim-resolver/scim-resolver.component";
import { HttpResolverComponent } from "./http-resolver/http-resolver.component";
import { EntraidResolverComponent } from "./entraid-resolver/entraid-resolver.component";
import { KeycloakResolverComponent } from "./keycloak-resolver/keycloak-resolver.component";
import { ActivatedRoute, Router } from "@angular/router";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import { ROUTE_PATHS } from "../../../route_paths";
import { ContentService } from "../../../services/content/content.service";
import { PendingChangesService } from "../../../services/pending-changes/pending-changes.service";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { DialogService, DialogServiceInterface } from "../../../services/dialog/dialog.service";
import { SaveAndExitDialogComponent } from "../../shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";

@Component({
  selector: "app-user-new-resolver",
  standalone: true,
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
  private readonly resolverService = inject(ResolverService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly contentService = inject(ContentService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly pendingChangesService = inject(PendingChangesService);
  protected readonly renderer: Renderer2 = inject(Renderer2);
  public readonly dialogRef = inject(MatDialogRef<UserNewResolverComponent>, { optional: true });
  public readonly data = inject(MAT_DIALOG_DATA, { optional: true });

  private observer!: IntersectionObserver;
  private editInitialized = false;

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

  resolverName = "";
  resolverType: ResolverType = "passwdresolver";
  formData: Record<string, any> = {
    fileName: "/etc/passwd"
  };
  isSaving = signal(false);
  isTesting = signal(false);
  testUsername = "";
  testUserId = "";

  constructor() {
    const dialogResolver = this.data?.resolver;
    const dialogResolverName = this.data?.resolverName || dialogResolver?.resolvername;

    if (dialogResolver) {
      this.resolverName = dialogResolver.resolvername;
      this.resolverType = dialogResolver.type;
      this.formData = { ...(dialogResolver.data || {}) };
      this.editInitialized = true;
      this.resolverService.selectedResolverName.set(dialogResolver.resolvername);
    } else if (dialogResolverName) {
      this.resolverService.selectedResolverName.set(dialogResolverName);
    } else {
      this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
        this.resolverService.selectedResolverName.set(params.get("name") || "");
      });
    }

    if (this.dialogRef) {
      this.dialogRef.disableClose = true;
      this.dialogRef.backdropClick().subscribe(() => {
        this.onCancel();
      });
      this.dialogRef.keydownEvents().subscribe((event) => {
        if (event.key === "Escape") {
          this.onCancel();
        }
      });
    }

    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.onSave());

    effect(() => {
      if (!this.contentService.routeUrl().startsWith(ROUTE_PATHS.USERS)) {
        this.dialogRef?.close(true);
      }
    });

    effect(() => {
      const selectedName = this.resolverService.selectedResolverName();

      if (!selectedName) {
        if (this.editInitialized) {
          this.resolverName = "";
          this.resolverType = "passwdresolver";
          this.formData = {
            fileName: "/etc/passwd"
          };
          this.editInitialized = false;
        }
        return;
      }

      const resourceRef = this.resolverService.selectedResolverResource;

      if (resourceRef.status() === ResourceStatus.Loading || resourceRef.status() === ResourceStatus.Reloading) {
        if (resourceRef.status() === ResourceStatus.Reloading) {
          this.editInitialized = false;
        }
        return;
      }

      const resource = resourceRef.value();

      if (!resource?.result?.value) {
        return;
      }

      if (this.editInitialized) {
        return;
      }

      const resolverData = resource.result.value;
      const resolver = resolverData[selectedName];

      if (resolver) {
        this.resolverName = resolver.resolvername || selectedName;
        this.resolverType = resolver.type;
        this.formData = { ...(resolver.data || {}) };
        this.editInitialized = true;
      }
    });
  }

  get isEditMode(): boolean {
    return !!this.resolverService.selectedResolverName();
  }

  get isAdditionalFieldsValid(): boolean {
    const fields = Object.values(this.additionalFormFields());
    if (fields.length === 0) {
      return false;
    }
    return fields.every((control) => control.valid);
  }

  get canSave(): boolean {
    const nameOk = this.resolverName.trim().length > 0;
    const typeOk = !!this.resolverType;
    return nameOk && typeOk && this.isAdditionalFieldsValid && !this.isSaving();
  }

  get hasChanges(): boolean {
    if (Object.values(this.additionalFormFields()).some((control) => control.dirty)) {
      return true;
    }

    if (this.isEditMode) {
      return this.testUsername !== "" || this.testUserId !== "";
    } else {
      return (
        this.resolverName !== "" ||
        this.resolverType !== "passwdresolver" ||
        this.testUsername !== "" ||
        this.testUserId !== ""
      );
    }
  }

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel || !this.leftColumn) {
      return;
    }

    const options: IntersectionObserverInit = {
      root: this.scrollContainer.nativeElement,
      threshold: [0, 1]
    };

    this.observer = new IntersectionObserver(([entry]) => {
      if (!entry.rootBounds) return;

      const shouldFloat = entry.boundingClientRect.top < entry.rootBounds.top;

      if (shouldFloat) {
        this.renderer.addClass(this.stickyHeader.nativeElement, "is-sticky");
      } else {
        this.renderer.removeClass(this.stickyHeader.nativeElement, "is-sticky");
      }
    }, options);

    this.observer.observe(this.stickySentinel.nativeElement);
  }

  ngOnDestroy(): void {
    this.resolverService.selectedResolverName.set("");
    this.pendingChangesService.unregisterHasChanges();
    if (this.observer) {
      this.observer.disconnect();
    }
  }

  onTypeChange(type: ResolverType): void {
    if (!this.isEditMode) {
      this.formData = {};

      if (type === "passwdresolver") {
        this.formData = {
          fileName: "/etc/passwd"
        };
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
      } else if (type === "sqlresolver") {
        this.formData = {};
      } else if (type === "scimresolver") {
        this.formData = {};
      }
    }
  }

  onSave(): Promise<void> | void {
    const name = this.resolverName.trim();
    if (!name) {
      this.notificationService.openSnackBar($localize`Please enter a resolver name.`);
      return;
    }
    if (!this.resolverType) {
      this.notificationService.openSnackBar($localize`Please select a resolver type.`);
      return;
    }
    if (!this.isAdditionalFieldsValid) {
      this.notificationService.openSnackBar($localize`Please fill in all required fields.`);
      return;
    }

    const payload: any = {
      type: this.resolverType,
      ...this.formData
    };

    for (const [key, control] of Object.entries(this.additionalFormFields())) {
      if (!control) continue;
      payload[key] = control.value;
    }

    this.isSaving.set(true);

    return new Promise<void>((resolve) => {
      this.resolverService
        .postResolver(name, payload)
        .subscribe({
          next: (res: PiResponse<any, any>) => {
            if (res.result?.status === true && (res.result.value ?? 0) >= 0) {
              this.notificationService.openSnackBar(
                this.isEditMode ? $localize`Resolver "${name}" updated.` : $localize`Resolver "${name}" created.`
              );
              this.resolverService.resolversResource.reload?.();

              if (this.dialogRef) {
                this.dialogRef.close(true);
              } else if (!this.isEditMode) {
                this.resolverName = "";
                this.formData = {};
                this.router.navigateByUrl(ROUTE_PATHS.USERS_RESOLVERS);
              }
            } else {
              const message =
                res.detail?.description || res.result?.error?.message || $localize`Unknown error occurred.`;
              this.notificationService.openSnackBar($localize`Failed to save resolver. ${message}`);
            }
          },
          error: (err: HttpErrorResponse) => {
            const message = err.error?.result?.error?.message || err.message;
            this.notificationService.openSnackBar($localize`Failed to save resolver. ${message}`);
          }
        })
        .add(() => {
          setTimeout(() => this.isSaving.set(false));
          resolve();
        });
    });
  }

  onTest(): void {
    this.executeTest();
  }

  onQuickTest() {
    this.executeTest(true);
  }

  onCancel(): void {
    if (this.hasChanges) {
      this.dialogService
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
            Promise.resolve(this.pendingChangesService.save()).then(() => {
              this.pendingChangesService.unregisterHasChanges();
              this.closeCurrent();
            });
          } else if (result === "discard") {
            this.pendingChangesService.unregisterHasChanges();
            this.closeCurrent();
          }
        });
    } else {
      this.closeCurrent();
    }
  }

  private closeCurrent(): void {
    if (this.dialogRef) {
      this.dialogRef.close();
    } else {
      this.router.navigateByUrl(ROUTE_PATHS.USERS_RESOLVERS);
    }
  }

  private executeTest(quickTest = false): void {
    if (!this.resolverType) {
      this.notificationService.openSnackBar($localize`Please select a resolver type.`);
      return;
    }

    if (!this.isAdditionalFieldsValid) {
      this.notificationService.openSnackBar($localize`Please fill in all required fields.`);
      return;
    }

    this.isTesting.set(true);

    const payload: any = {
      type: this.resolverType,
      ...this.formData,
      test_username: this.testUsername,
      test_userid: this.testUserId
    };

    if (quickTest) {
      payload["SIZELIMIT"] = 1;
    }

    if (this.isEditMode) {
      payload["resolver"] = this.resolverName;
    }

    for (const [key, control] of Object.entries(this.additionalFormFields())) {
      if (!control) continue;
      payload[key] = control.value;
    }

    this.resolverService
      .postResolverTest(payload)
      .subscribe({
        next: (res: PiResponse<any, any>) => {
          if (res.result?.status === true && (res.result.value ?? 0) >= 0) {
            this.notificationService.openSnackBar($localize`Resolver test executed: ${res.detail.description}`, 20000);
          } else {
            const message = res.detail?.description || res.result?.error?.message || $localize`Unknown error occurred.`;
            this.notificationService.openSnackBar($localize`Failed to test resolver. ${message}`);
          }
        },
        error: (err: HttpErrorResponse) => {
          const message = err.error?.result?.error?.message || err.message;
          this.notificationService.openSnackBar($localize`Failed to test resolver. ${message}`);
        }
      })
      .add(() => setTimeout(() => this.isTesting.set(false)));
  }
}
