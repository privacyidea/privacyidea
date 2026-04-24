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
  AfterViewInit,
  Component,
  computed,
  DestroyRef,
  effect,
  ElementRef,
  inject,
  OnDestroy,
  Renderer2,
  signal,
  ViewChild
} from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";

import { ReactiveFormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { ActivatedRoute, Router } from "@angular/router";
import { PolicyDetail, PolicyService, PolicyServiceInterface } from "../../../../services/policies/policies.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { DialogService, DialogServiceInterface } from "../../../../services/dialog/dialog.service";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { PolicyPanelEditComponent } from "./policy-panels/policy-panel-edit/policy-panel-edit.component";
import { ROUTE_PATHS } from "../../../../route_paths";

@Component({
  selector: "app-edit-policy-dialog",
  standalone: true,
  imports: [ReactiveFormsModule, PolicyPanelEditComponent, MatButtonModule, MatIconModule],
  templateUrl: "./edit-policy-dialog.component.html",
  styleUrl: "./edit-policy-dialog.component.scss"
})
export class EditPolicyDialogComponent implements AfterViewInit, OnDestroy {
  private readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly renderer = inject(Renderer2);

  private _observer!: IntersectionObserver;

  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;
  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;

  readonly mode = signal<"create" | "edit">("create");
  readonly policy = signal<PolicyDetail>(this.policyService.getEmptyPolicy());
  readonly policyEdits = signal<Partial<PolicyDetail>>({});
  private editPolicyName: string | null = null;
  readonly editedPolicy = computed(() => ({ ...this.policy(), ...this.policyEdits() }));
  readonly isPolicyEdited = computed(() => Object.keys(this.policyEdits()).length > 0);
  readonly isDirty = this.isPolicyEdited;
  readonly canSave = computed(() => this.isPolicyEdited() && !!this.editedPolicy().name?.trim());
  readonly title = computed(() => this.mode() === "edit" ? $localize`Edit Policy` : $localize`Create Policy`);

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const name = params.get("name");
      if (name) {
        this.mode.set("edit");
        this.editPolicyName = name;
        const policy = this.policyService.allPolicies().find((p) => p.name === name);
        if (policy) this.policy.set(policy);
      } else {
        this.mode.set("create");
        this.editPolicyName = null;
        this.policy.set(this.policyService.getEmptyPolicy());
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const policies = this.policyService.allPolicies();
      if (this.mode() === "edit" && this.editPolicyName && !this.isPolicyEdited()) {
        const found = policies.find((p) => p.name === this.editPolicyName);
        if (found) this.policy.set(found);
      }
    });

    this.pendingChangesService.registerHasChanges(() => this.isDirty());
    this.pendingChangesService.registerValidChanges(() => this.canSave());
    this.pendingChangesService.registerSave(() => this.onSave());
  }

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) {
      return;
    }
    this._observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.rootBounds) return;
        const shouldFloat = entry.boundingClientRect.top < entry.rootBounds.top;
        if (shouldFloat) {
          this.renderer.addClass(this.stickyHeader.nativeElement, "is-sticky");
        } else {
          this.renderer.removeClass(this.stickyHeader.nativeElement, "is-sticky");
        }
      },
      { root: this.scrollContainer.nativeElement, threshold: [0, 1] }
    );
    this._observer.observe(this.stickySentinel.nativeElement);
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
    this._observer?.disconnect();
  }

  addPolicyEdit(edits: Partial<PolicyDetail>): void {
    this.policyEdits.set({ ...this.policyEdits(), ...edits });
  }

  onAction(value: "submit" | null): void {
    if (value !== "submit") return;
    this.onSave();
  }

  async onSave(): Promise<boolean> {
    let success = false;
    if (this.mode() === "create") {
      success = await this.policyService.saveNewPolicy({ ...this.policy(), ...this.policyEdits() });
    } else {
      success = await this.policyService.savePolicyEdits(this.policy().name, {
        ...this.policy(),
        ...this.policyEdits()
      });
    }
    if (success) {
      this._navigateBack();
    }
    return success;
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
          Promise.resolve(this.pendingChangesService.save()).then((success) => {
            if (success) {
              this._navigateBack();
            }
          });
        } else if (result === "discard") {
          this._navigateBack();
        }
      });
  }

  private _navigateBack(): void {
    this.pendingChangesService.clearAllRegistrations();
    this.router.navigateByUrl(ROUTE_PATHS.POLICIES);
  }
}
