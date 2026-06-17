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

import {
  Component,
  computed,
  inject,
  linkedSignal,
  OnDestroy,
  OnInit,
  signal,
  Signal,
  WritableSignal
} from "@angular/core";
import { form, FormField, required } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { UserDetailsEditComponent } from "@components/user/user-details-edit/user-details-edit.component";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { RealmService } from "@services/realm/realm.service";
import { ResolverService } from "@services/resolver/resolver.service";
import { EditUserData, UserService } from "@services/user/user.service";

@Component({
  selector: "app-user-create",
  standalone: true,
  imports: [
    UserDetailsEditComponent,
    MatFormField,
    MatLabel,
    MatOption,
    MatSelect,
    MatHint,
    MatError,
    MatInput,
    FormField,
    MatButtonModule,
    MatIconModule,
    ScrollToTopDirective
  ],
  templateUrl: "./user-create.component.html",
  styleUrl: "./user-create.component.scss"
})
export class UserCreateComponent implements OnInit, OnDestroy {
  protected readonly userService = inject(UserService);
  protected readonly resolverService = inject(ResolverService);
  protected readonly realmService = inject(RealmService);
  protected readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);

  realm = linkedSignal(() => this.userService.selectedUserRealm() || "");

  username = signal<string>("");
  resolver = signal<string>("");

  usernameForm = form(this.username, (f) => {
    required(f);
  });
  resolverForm = form(this.resolver, (f) => {
    required(f);
  });

  canSave = computed(() => this.usernameForm().valid() && this.resolverForm().valid());
  isDirty = computed(() => this.usernameForm().dirty() || this.resolverForm().dirty() || !this.editUserDataIsEmpty());

  constructor() {
    const realm = this.realm();
    if (realm) {
      const realmConfig = this.realmService.realms()[realm];
      const firstResolver = realmConfig?.resolver[0]?.name;
      if (firstResolver) this.resolver.set(firstResolver);
    }
  }

  ngOnInit(): void {
    this.pendingChangesService.registerHasChanges(() => this.isDirty());
    this.pendingChangesService.registerValidChanges(() => this.canSave());
    this.pendingChangesService.registerSave(() => this.onSave());
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  editedUserData: WritableSignal<EditUserData> = linkedSignal(() => ({ username: "" }));

  editUserDataIsEmpty = computed(() =>
    Object.values(this.editedUserData()).every((value) => value === "" || value === undefined)
  );

  correspondingRealms: Signal<string[]> = computed(() => {
    const realms = this.realmService.realms();
    const result: string[] = [];
    for (const [realmName, realmObj] of Object.entries(realms)) {
      if (realmObj.resolver.some((r) => r.name === this.resolver())) {
        result.push(realmName);
      }
    }
    return result;
  });

  async onSave(): Promise<boolean> {
    if (!this.canSave()) {
      this.usernameForm().markAsTouched();
      this.resolverForm().markAsTouched();
      this.notificationService.warning($localize`Please fill in all required fields.`);
      return false;
    }
    this.editedUserData().username = this.username();
    return new Promise((resolve) => {
      this.userService.createUser(this.resolver(), this.editedUserData()).subscribe({
        next: (success) => {
          if (success) {
            this.userService.usersResource.reload();
            this._navigateBack();
            resolve(true);
          } else {
            resolve(false);
          }
        },
        error: () => resolve(false)
      });
    });
  }

  onCancel(): void {
    if (!this.isDirty()) {
      this._navigateBack();
      return;
    }
    this.dialogService
      .openDialog({
        component: SaveAndExitDialogComponent,
        data: {
          title: $localize`Discard changes`,
          allowSaveExit: this.canSave(),
          saveExitDisabled: !this.canSave()
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result === "save-exit") {
          if (!this.canSave()) return;
          Promise.resolve(this.pendingChangesService.save());
        } else if (result === "discard") {
          this._navigateBack();
        }
      });
  }

  private _navigateBack(): void {
    this.pendingChangesService.clearAllRegistrations();
    this.router.navigateByUrl(ROUTE_PATHS.USERS);
  }
}
