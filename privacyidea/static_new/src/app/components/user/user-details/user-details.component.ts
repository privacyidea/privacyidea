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
import { NgClass } from "@angular/common";
import {
  Component,
  computed,
  effect,
  inject,
  linkedSignal,
  OnDestroy,
  OnInit,
  Renderer2,
  signal,
  WritableSignal
} from "@angular/core";
import { MatAutocomplete, MatAutocompleteTrigger, MatOption } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatTableDataSource } from "@angular/material/table";
import { MatTooltip } from "@angular/material/tooltip";
import { Router, RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import {
  SaveAndExitDialogComponent,
  SaveAndExitDialogResult
} from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { UserDetailsEditComponent } from "@components/user/user-details-edit/user-details-edit.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { AuditService, AuditServiceInterface } from "@services/audit/audit.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { TokenDetails, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { EditUserData, UserService, UserServiceInterface } from "@services/user/user.service";
import { filter, firstValueFrom } from "rxjs";
import { UserDetailsContainerTableComponent } from "./user-details-container-table/user-details-container-table.component";
import { UserDetailsPinDialogComponent } from "./user-details-pin-dialog/user-details-pin-dialog.component";
import { UserDetailsTokenTableComponent } from "./user-details-token-table/user-details-token-table.component";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";

@Component({
  selector: "app-user-details",
  imports: [
    ScrollToTopDirective,
    MatButtonModule,
    UserDetailsTokenTableComponent,
    ClearableInputComponent,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatFormField,
    MatIcon,
    MatInput,
    MatLabel,
    MatOption,
    MatFormField,
    NgClass,
    UserDetailsContainerTableComponent,
    MatSelectModule,
    MatTooltip,
    RouterLink,
    CopyableComponent,
    UserDetailsEditComponent,
    StickyHeaderDirective
  ],
  templateUrl: "./user-details.component.html",
  styleUrl: "./user-details.component.scss"
})
export class UserDetailsComponent implements OnInit, OnDestroy {
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly auditService: AuditServiceInterface = inject(AuditService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private router = inject(Router);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly renderer = inject(Renderer2);

  readonly labels: Record<string, string> = {
    username: $localize`Username`,
    givenname: $localize`Given name`,
    surname: $localize`Surname`,
    email: $localize`Email`,
    phone: $localize`Phone`,
    mobile: $localize`Mobile`,
    description: $localize`Description`,
    userid: $localize`User ID`,
    resolver: $localize`Resolver`
  };
  readonly excludedKeys = new Set(["editable"]);

  userData = this.userService.user;
  tokenResource = this.tokenService.tokenResource;

  tokenDataSource: WritableSignal<MatTableDataSource<TokenDetails>> = linkedSignal({
    source: this.tokenService.tokenResourceValue,
    computation: (tokenResourceValue, previous) => {
      if (tokenResourceValue) {
        return new MatTableDataSource(tokenResourceValue.tokens);
      }
      return previous?.value ?? new MatTableDataSource();
    }
  });

  attributeSetMap = this.userService.attributeSetMap;
  deletableAttributes = this.userService.deletableAttributes;
  keyOptions = this.userService.keyOptions;
  hasWildcardKey = this.userService.hasWildcardKey;
  expandedKeys = signal<Set<string>>(new Set<string>());
  addKeyInput = signal<string>("");
  addValueInput = signal<string>("");
  selectedKey = signal<string | null>(null);
  selectedValue = signal<string | null>(null);
  keyMode = signal<"select" | "input">("select");
  valueOptions = computed<string[]>(() => {
    const map = this.attributeSetMap();
    const mode = this.keyMode();
    const key = mode === "input" ? this.addKeyInput().trim() : (this.selectedKey() ?? "");
    if (key && map[key]) return map[key];
    if (map["*"]) return map["*"];
    return [];
  });
  isValueInput = computed<boolean>(() => {
    const opts = this.valueOptions();
    if (opts.includes("*")) return true;
    return opts.length === 0;
  });
  canAddAttribute = computed<boolean>(() => {
    const key = this.keyMode() === "input" ? this.addKeyInput().trim() : (this.selectedKey() ?? "").trim();
    const value = this.isValueInput() ? this.addValueInput().trim() : (this.selectedValue() ?? "").trim();
    return key.length > 0 && value.length > 0;
  });

  constructor() {
    effect(() => {
      const hasWildcard = this.hasWildcardKey();
      const hasFixedKeys = this.keyOptions().length > 0;
      if (hasWildcard && !hasFixedKeys) {
        this.keyMode.set("input");
      } else {
        this.keyMode.set("select");
      }
    });
  }

  detailsEntries = computed(() =>
    Object.entries(this.userData() ?? {})
      .filter(([key]) => !this.excludedKeys.has(key))
      .map(([key, value]) => ({
        key,
        label: this.labels[key] ?? key,
        value: value ?? "-"
      }))
  );

  ngOnInit(): void {
    this.pendingChangesService.registerHasChanges(
      () =>
        this.editIsDirty() ||
        !!this.addKeyInput() ||
        !!this.addValueInput() ||
        !!this.selectedKey() ||
        !!this.selectedValue()
    );
    this.pendingChangesService.registerValidChanges(() => {
      if (this.editMode()) return true;
      const key = this.keyMode() === "input" ? this.addKeyInput().trim() : (this.selectedKey() ?? "").trim();
      const value = this.isValueInput() ? this.addValueInput().trim() : (this.selectedValue() ?? "").trim();
      return !!key && !!value;
    });
    this.pendingChangesService.registerSave(() => {
      if (this.editMode()) return this.saveEditAsync();
      return this.addCustomAttribute();
    });
  }

  private async saveEditAsync(): Promise<boolean> {
    const data = { ...this.editedUserData(), username: this.userData().username };
    try {
      const success = await firstValueFrom(this.userService.editUser(this.userData().resolver, data));
      if (success) {
        this.userService.userResource.reload();
        this.editMode.set(false);
      }
      return !!success;
    } catch (error) {
      console.error("Failed to save user edits", error);
      const message = error instanceof Error ? error.message : String(error);
      this.notificationService.error("Failed to save user edits. " + message);
      return false;
    }
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  isExpanded(key: string): boolean {
    return this.expandedKeys().has(key);
  }

  toggleExpanded(key: string): void {
    const next = new Set(this.expandedKeys());
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    this.expandedKeys.set(next);
  }

  switchToCustomKey() {
    this.keyMode.set("input");
    this.selectedKey.set(null);
  }

  switchToSelectKey() {
    this.keyMode.set("select");
    this.addKeyInput.set("");
  }

  async addCustomAttribute(): Promise<boolean> {
    const key = this.keyMode() === "input" ? this.addKeyInput().trim() : (this.selectedKey() ?? "").trim();
    const value = this.isValueInput() ? this.addValueInput().trim() : (this.selectedValue() ?? "").trim();

    if (!key || !value) return false;

    try {
      await firstValueFrom(this.userService.setUserAttribute(key, value));
      this.userService.userAttributesResource.reload();
      this.userService.userResource.reload();
      this.addKeyInput.set("");
      this.addValueInput.set("");
      this.selectedKey.set(null);
      this.selectedValue.set(null);
      return true;
    } catch {
      return false;
    }
  }

  deleteCustomAttribute(key: string) {
    this.userService.deleteUserAttribute(key).subscribe({
      next: () => {
        this.userService.userAttributesResource.reload();
        this.userService.userResource.reload();
      }
    });
  }

  assignUserToToken(option: TokenDetails) {
    this.dialogService
      .openDialog({ component: UserDetailsPinDialogComponent })
      .afterClosed()
      .pipe(filter((pin): pin is string => pin != null))
      .subscribe((pin: string) => {
        this.tokenService
          .assignUser({
            tokenSerial: option["serial"],
            username: this.userService.detailsUser().username,
            realm: this.userService.selectedUserRealm(),
            pin: pin
          })
          .subscribe({
            next: () => {
              this.tokenService.userTokenResource.reload();
              this.tokenService.tokenResource.reload();
            }
          });
      });
  }

  enrollNewToken() {
    this.userService.selectedUserRealm.set(this.userService.detailsUser().realm);
    this.userService.selectionFilter.set(this.userService.detailsUser().username);
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_ENROLLMENT).then();
  }

  createNewContainer() {
    this.userService.selectedUserRealm.set(this.userService.detailsUser().realm);
    this.userService.selectionFilter.set(this.userService.detailsUser().username);
    this.router.navigateByUrl(ROUTE_PATHS.CONTAINERS_CREATE).then();
  }

  showUserAuditLog() {
    this.auditService.auditFilter.set(new FilterValue({ value: `user: ${this.userService.detailsUser().username}` }));
  }

  editMode = signal(false);
  editedUserData: WritableSignal<EditUserData> = signal({ username: "" });

  editIsDirty = computed(() => {
    if (!this.editMode()) return false;
    const original: Record<string, unknown> = this.userData() ?? {};
    return Object.entries(this.editedUserData()).some(([key, value]) => (value ?? "") !== (original[key] ?? ""));
  });

  editUser() {
    this.editedUserData.set({ ...this.userData() });
    this.editMode.set(true);
  }

  cancelEdit() {
    if (!this.editIsDirty()) {
      this.editMode.set(false);
      return;
    }
    this.dialogService
      .openDialog({
        component: SaveAndExitDialogComponent,
        data: {
          allowSaveExit: true,
          saveExitDisabled: false
        }
      })
      .afterClosed()
      .subscribe((result: SaveAndExitDialogResult | undefined) => {
        if (result === "discard") {
          this.editMode.set(false);
        } else if (result === "save-exit") {
          this.saveEdit();
        }
      });
  }

  onUpdateEditedUser(newData: EditUserData) {
    this.editedUserData.set(newData);
  }

  saveEdit() {
    void this.saveEditAsync();
  }

  deleteUser() {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`Delete User`,
          items: [this.userData().username],
          itemType: "user",
          confirmAction: { label: $localize`Delete`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.userService.deleteUser(this.userData().resolver, this.userData().username).subscribe({
              next: (success) => {
                if (success) {
                  this.router.navigateByUrl(ROUTE_PATHS.USERS).then();
                  this.userService.usersResource.reload();
                }
              }
            });
          }
        }
      });
  }

  protected readonly Array = Array;
}
