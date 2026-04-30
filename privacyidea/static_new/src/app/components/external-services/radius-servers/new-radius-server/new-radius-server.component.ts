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
  ViewChild
} from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from "@angular/forms";
import {
  RadiusServer,
  RadiusServerService,
  RadiusServerServiceInterface
} from "../../../../services/radius-server/radius-server.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";
import { ROUTE_PATHS } from "../../../../route_paths";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { SaveAndExitDialogComponent } from "../../../shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { DialogService, DialogServiceInterface } from "../../../../services/dialog/dialog.service";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";
import { ScrollToTopDirective } from "../../../shared/directives/app-scroll-to-top.directive";

@Component({
  selector: "app-new-radius-server",
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatButtonModule,
    MatIconModule,
    MatTooltip,
    ClearableInputComponent,
    ScrollToTopDirective
  ],
  templateUrl: "./new-radius-server.component.html",
  styleUrl: "./new-radius-server.component.scss"
})
export class NewRadiusServerComponent implements AfterViewInit, OnDestroy {
  private readonly formBuilder = inject(FormBuilder);
  protected readonly radiusService: RadiusServerServiceInterface = inject(RadiusServerService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly renderer: Renderer2 = inject(Renderer2);

  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;
  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;

  private observer!: IntersectionObserver;

  radiusForm!: FormGroup;
  isEditMode = false;
  isTesting = signal(false);
  private editIdentifier: string | null = null;

  constructor() {
    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.save());
    this.pendingChangesService.registerValidChanges(() => this.canSave);

    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const identifier = params.get("identifier");
      if (identifier) {
        this.isEditMode = true;
        this.editIdentifier = identifier;
        const server = this.radiusService.radiusServers().find((s) => s.identifier === identifier);
        this.initForm(server ?? null);
      } else {
        this.isEditMode = false;
        this.editIdentifier = null;
        this.initForm(null);
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const servers = this.radiusService.radiusServers();
      if (this.isEditMode && this.editIdentifier && this.radiusForm?.pristine) {
        const found = servers.find((s) => s.identifier === this.editIdentifier);
        if (found) {
          this.initForm(found);
        }
      }
    });
  }

  get hasChanges(): boolean {
    return !this.radiusForm.pristine;
  }

  get canSave(): boolean {
    return this.authService.actionAllowed("radiusserver_write") && this.radiusForm.valid;
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

  private initForm(data: RadiusServer | null): void {
    this.radiusForm = this.formBuilder.group({
      identifier: [data?.identifier || "", [Validators.required]],
      server: [data?.server || "", [Validators.required]],
      port: [data?.port || 1812],
      timeout: [data?.timeout || 5],
      retries: [data?.retries || 3],
      secret: [data?.secret || "", [Validators.required]],
      message_authenticator: [data?.options?.message_authenticator ?? true],
      dictionary: [data?.dictionary || ""],
      description: [data?.description || ""],
      username: [""],
      password: [""]
    });

    if (this.isEditMode) {
      this.radiusForm.get("identifier")?.disable();
    }
  }

  async save(): Promise<boolean> {
    if (this.radiusForm.invalid) {
      return false;
    }
    const formValue = this.radiusForm.getRawValue();
    const server: RadiusServer = {
      identifier: formValue.identifier,
      server: formValue.server,
      port: formValue.port,
      timeout: formValue.timeout,
      retries: formValue.retries,
      secret: formValue.secret,
      dictionary: formValue.dictionary,
      description: formValue.description,
      options: {
        message_authenticator: formValue.message_authenticator
      }
    };
    try {
      await this.radiusService.postRadiusServer(server);
      this.pendingChangesService.clearAllRegistrations();
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS);
      return true;
    } catch (error) {
      return false;
    }
  }

  test(): void {
    if (this.radiusForm.valid) {
      this.isTesting.set(true);
      const formValue = this.radiusForm.getRawValue();
      const params = {
        ...formValue,
        options: {
          message_authenticator: formValue.message_authenticator
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
