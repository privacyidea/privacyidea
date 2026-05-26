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
  effect,
  ElementRef,
  inject,
  OnDestroy,
  Renderer2,
  signal,
  untracked,
  ViewChild
} from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { disabled, form, FormField, pattern, required } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatProgressSpinnerModule } from "@angular/material/progress-spinner";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import {
  PrivacyideaServer,
  PrivacyideaServerService,
  PrivacyideaServerServiceInterface
} from "@services/privacyidea-server/privacyidea-server.service";

interface PrivacyideaFormModel {
  identifier: string;
  url: string;
  tls: boolean;
  description: string;
  username: string;
  password: string;
}

const EMPTY_PRIVACYIDEA_FORM: PrivacyideaFormModel = {
  identifier: "",
  url: "",
  tls: true,
  description: "",
  username: "",
  password: ""
};

@Component({
  selector: "app-privacyidea-edit-dialog",
  standalone: true,
  imports: [
    FormField,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    ClearableInputComponent,
    ScrollToTopDirective
  ],
  templateUrl: "./new-privacyidea-server.component.html",
  styleUrl: "./new-privacyidea-server.component.scss"
})
export class NewPrivacyideaServerComponent implements AfterViewInit, OnDestroy {
  protected readonly privacyideaServerService: PrivacyideaServerServiceInterface = inject(PrivacyideaServerService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly renderer: Renderer2 = inject(Renderer2);

  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;
  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;

  private observer!: IntersectionObserver;

  isEditMode = signal(false);
  isTesting = signal(false);
  private editIdentifier: string | null = null;

  privacyideaModel = signal<PrivacyideaFormModel>({ ...EMPTY_PRIVACYIDEA_FORM });

  privacyideaForm = form(this.privacyideaModel, (f) => {
    required(f.identifier);
    pattern(f.identifier, /^[a-zA-Z0-9._-]*$/);
    required(f.url);
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
        const server = this.privacyideaServerService.remoteServerOptions().find((s) => s.identifier === identifier);
        this.loadData(server ?? null);
      } else {
        this.isEditMode.set(false);
        this.editIdentifier = null;
        this.loadData(null);
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const servers = this.privacyideaServerService.remoteServerOptions();
      if (this.isEditMode() && this.editIdentifier && untracked(() => !this.privacyideaForm().dirty())) {
        const found = servers.find((s) => s.identifier === this.editIdentifier);
        if (found) {
          this.loadData(found);
        }
      }
    });
  }

  get hasChanges(): boolean {
    return this.privacyideaForm().dirty();
  }

  get canSave(): boolean {
    return this.authService.actionAllowed("privacyideaserver_write") && this.privacyideaForm().valid();
  }

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) return;

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
    this.pendingChangesService.clearAllRegistrations();
    this.observer?.disconnect();
  }

  private loadData(server: PrivacyideaServer | null): void {
    this.privacyideaModel.set({
      identifier: server?.identifier || "",
      url: server?.url || "",
      tls: server?.tls ?? true,
      description: server?.description || "",
      username: server?.username || "",
      password: server?.password || ""
    });
    this.privacyideaForm().reset();
  }

  async save(): Promise<boolean> {
    if (!this.privacyideaForm().valid()) {
      return false;
    }

    const server = this.privacyideaModel() as unknown as PrivacyideaServer;
    try {
      await this.privacyideaServerService.postPrivacyideaServer(server);
      this.pendingChangesService.clearAllRegistrations();
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA);
      return true;
    } catch (error) {
      return false;
    }
  }

  test(): void {
    if (this.privacyideaForm().valid()) {
      this.isTesting.set(true);
      const params = this.privacyideaModel() as unknown as PrivacyideaServer;
      this.privacyideaServerService.testPrivacyideaServer(params).then(() => {
        this.isTesting.set(false);
      });
    }
  }

  onCancel(): void {
    if (!this.hasChanges) {
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA);
      return;
    }
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
          this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA);
        } else if (result == "save-exit") {
          if (!this.canSave) return;
          Promise.resolve(this.pendingChangesService.save()).then((success) => {
            if (success) {
              this.pendingChangesService.clearAllRegistrations();
              this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA);
            }
          });
        }
      });
  }
}
