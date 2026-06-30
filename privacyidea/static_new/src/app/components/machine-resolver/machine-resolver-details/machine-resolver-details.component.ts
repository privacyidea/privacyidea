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

import { Component, computed, effect, inject, OnDestroy, OnInit, signal } from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { MachineResolverHostsTabComponent } from "@components/machine-resolver/machine-resolver-hosts-tab/machine-resolver-hosts-tab.component";
import { MachineResolverLdapTabComponent } from "@components/machine-resolver/machine-resolver-ldap-tab/machine-resolver-ldap-tab.component";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import {
  MachineResolver,
  MachineResolverData,
  MachineResolverService,
  MachineResolverServiceInterface
} from "@services/machine-resolver/machine-resolver.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { deepCopy } from "@utils/deep-copy.utils";
import { lastValueFrom } from "rxjs";

@Component({
  selector: "app-machine-resolver-details",
  templateUrl: "./machine-resolver-details.component.html",
  styleUrls: ["./machine-resolver-details.component.scss"],
  standalone: true,
  imports: [
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    ClearableInputComponent,
    ScrollToTopDirective,
    MachineResolverHostsTabComponent,
    MachineResolverLdapTabComponent
  ]
})
export class MachineResolverDetailsComponent implements OnInit, OnDestroy {
  readonly machineResolverService: MachineResolverServiceInterface = inject(MachineResolverService);
  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  private static readonly machineResolverDefault: MachineResolver = {
    resolvername: "",
    type: "hosts",
    data: { resolver: "", type: "hosts" }
  };

  private _loadedName: string | null = null;

  readonly machineResolverTypes = this.machineResolverService.allMachineResolverTypes;
  readonly dataValidatorSignal = signal<(data: MachineResolverData) => boolean>(() => true);

  readonly selectedName = signal<string>("");
  readonly isEditMode = computed(() => this.selectedName() !== "");
  readonly isEditing = signal(false);
  readonly fieldsEditable = computed(() => !this.isEditMode() || this.isEditing());

  readonly originalMachineResolver = signal<MachineResolver>(
    deepCopy(MachineResolverDetailsComponent.machineResolverDefault)
  );
  readonly currentMachineResolver = signal<MachineResolver>(
    deepCopy(MachineResolverDetailsComponent.machineResolverDefault)
  );

  readonly canEditTab = computed(() => this.isEditMode() && this.authService.actionAllowed("mresolverwrite"));
  readonly tabCanSave = computed(() => this.canSaveMachineResolver() && this.isEdited());

  readonly isEdited = computed(
    () => JSON.stringify(this.currentMachineResolver()) !== JSON.stringify(this.originalMachineResolver())
  );

  readonly nameHasPatternError = computed(() => {
    const name = this.currentMachineResolver().resolvername;
    return name.length > 0 && !/^[a-zA-Z0-9._-]*$/.test(name);
  });

  readonly canSaveMachineResolver = computed(() => {
    const current = this.currentMachineResolver();
    if (!current.resolvername.trim() || !/^[a-zA-Z0-9._-]*$/.test(current.resolvername)) return false;
    return this.dataValidatorSignal()(current.data);
  });

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      this.selectedName.set(params.get("name") ?? "");
    });

    effect(() => {
      const name = this.selectedName();
      if (!name) {
        this._loadedName = null;
        return;
      }
      if (this.isEditing()) {
        return;
      }
      const resource = this.machineResolverService.machineResolverResource;
      const status = resource.status();
      if (status === "loading" || status === "reloading" || !resource.hasValue()) {
        return;
      }
      const resolver = this.machineResolverService.machineResolvers().find((r) => r.resolvername === name);
      if (resolver) {
        this.originalMachineResolver.set(deepCopy(resolver));
        this.currentMachineResolver.set(deepCopy(resolver));
        this.isEditing.set(false);
        this._loadedName = name;
      } else {
        this.notificationService.error($localize`Machine resolver "${name}" not found.`);
        this.navigateBack();
      }
    });
  }

  ngOnInit(): void {
    this.pendingChangesService.registerHasChanges(() => this.isEdited());
    this.pendingChangesService.registerValidChanges(() => this.canSaveMachineResolver());
    this.pendingChangesService.registerSave(() => this.saveMachineResolver());
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  startEditing(): void {
    this.isEditing.set(true);
  }

  onResolvernameChange(newName: string) {
    const current = this.currentMachineResolver();
    this.currentMachineResolver.set({
      ...current,
      resolvername: newName,
      data: { ...current.data, resolver: newName }
    });
  }

  onMachineResolverTypeChange(newType: string) {
    const current = this.currentMachineResolver();
    this.currentMachineResolver.set({
      ...current,
      type: newType,
      data: { resolver: current.resolvername, type: newType }
    });
  }

  onNewData(newData: MachineResolverData) {
    this.currentMachineResolver.set({ ...this.currentMachineResolver(), data: newData });
  }

  onNewValidator(newValidator: (data: MachineResolverData) => boolean) {
    this.dataValidatorSignal.set(newValidator);
  }

  async saveMachineResolver(): Promise<boolean> {
    const current = this.currentMachineResolver();
    try {
      await this.machineResolverService.postTestMachineResolver(current);
    } catch (error) {
      if ((error as Error).message === "post-failed") {
        const result = await lastValueFrom(
          this.dialogService
            .openDialog({
              component: SimpleConfirmationDialogComponent,
              data: {
                title: $localize`Save machine resolver despite test failure?`,
                confirmAction: { label: $localize`Proceed`, value: true, type: "destruct" },
                items: [current.resolvername || $localize`New Machine Resolver`],
                itemType: "machine resolver"
              }
            })
            .afterClosed()
        );
        if (!result) return false;
      } else {
        return false;
      }
    }
    try {
      await this.machineResolverService.postMachineResolver(current);
    } catch {
      return false;
    }
    this.originalMachineResolver.set(deepCopy(current));
    if (this.isEditMode()) {
      this.isEditing.set(false);
    } else {
      this.navigateBack();
    }
    return true;
  }

  async onCancel(): Promise<void> {
    if (!this.isEdited()) {
      this.exitEditOrNavigate();
      return;
    }
    try {
      const result = await lastValueFrom(
        this.dialogService
          .openDialog({
            component: SaveAndExitDialogComponent,
            data: {
              title: $localize`Discard changes`,
              allowSaveExit: this.canSaveMachineResolver(),
              saveExitDisabled: !this.canSaveMachineResolver()
            }
          })
          .afterClosed()
      );
      if (result === "save-exit") {
        if (!this.canSaveMachineResolver()) return;
        await this.saveMachineResolver();
      } else if (result === "discard") {
        this.exitEditOrNavigate();
      }
    } catch (err) {
      console.error("Error handling unsaved changes dialog:", err);
    }
  }

  private exitEditOrNavigate(): void {
    if (this.isEditMode()) {
      this.currentMachineResolver.set(deepCopy(this.originalMachineResolver()));
      this.isEditing.set(false);
    } else {
      this.navigateBack();
    }
  }

  private navigateBack(): void {
    this.pendingChangesService.clearAllRegistrations();
    this.router.navigateByUrl(ROUTE_PATHS.MACHINE_RESOLVER);
  }
}
