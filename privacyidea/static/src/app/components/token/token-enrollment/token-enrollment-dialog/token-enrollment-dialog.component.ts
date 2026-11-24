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
import { NgComponentOutlet } from "@angular/common";
import {
  afterNextRender,
  Component,
  computed,
  ElementRef,
  forwardRef,
  inject,
  Injector,
  signal,
  viewChild
} from "@angular/core";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import type { EnrollmentFlow } from "@components/token/token-enrollment/enrollment-flow";
import {
  ENROLLMENT_STEP_HOST,
  EnrollmentStep,
  EnrollmentStepHost
} from "@components/token/token-enrollment/enrollment-step";
import { EnrollmentCustomizationFrameComponent } from "@components/token/token-enrollment/enrollment-customization-frame/enrollment-customization-frame.component";
import { leaveIncompleteEnrollment } from "@components/token/token-enrollment/leave-incomplete-enrollment";
import {
  EnrolledTextLink,
  TokenEnrolledTextComponent
} from "@components/token/token-enrollment/token-enrolled-text/token-enrolled-text.component";
import { ENROLLMENT_CANCELLED } from "@components/token/token-enrollment/token-enrollment.constants";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { tokenTypes } from "@utils/token.utils";
import { map, Observable, of, tap } from "rxjs";

export interface EnrollmentDialogData {
  flow: EnrollmentFlow;
}

/**
 * The one dialog of an enrollment after its first response. It keeps its size, title area, header and
 * way out while the flow switches the step inside it.
 */
@Component({
  selector: "app-token-enrollment-dialog",
  imports: [
    DialogWrapperComponent,
    EnrollmentCustomizationFrameComponent,
    NgComponentOutlet,
    TokenEnrolledTextComponent
  ],
  providers: [{ provide: ENROLLMENT_STEP_HOST, useExisting: forwardRef(() => TokenEnrollmentDialogComponent) }],
  templateUrl: "./token-enrollment-dialog.component.html",
  styleUrl: "./token-enrollment-dialog.component.scss",
  host: {
    "[class.enrollment-dialog-fixed]": "flow.fixedSize()",
    "[style.--enrolled-card-count]": "header()?.cardCount() ?? 0"
  }
})
export class TokenEnrollmentDialogComponent
  extends AbstractDialogComponent<EnrollmentDialogData, void>
  implements EnrollmentStepHost
{
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly elementRef: ElementRef<HTMLElement> = inject(ElementRef);
  private readonly injector = inject(Injector);

  readonly flow = this.data.flow;
  protected readonly step = signal<EnrollmentStep | null>(null);
  protected readonly header = viewChild(TokenEnrolledTextComponent);
  protected readonly enrollment = computed(() => this.flow.dialogData());
  protected readonly detail = computed(() => this.enrollment()?.response?.detail);
  protected readonly request = computed(() => this.enrollment()?.enrollParameters?.data);
  // The container the server added the token to, else the one asked for.
  protected readonly containerSerial = computed(
    () => (this.detail()?.["container_serial"] as string | undefined) || this.request()?.containerSerial
  );
  protected readonly wizard = computed(() => this.enrollment()?.wizard ?? false);
  protected readonly finished = computed(() => this.step()?.headerState === "done");
  // Only a user who may delete has a choice when leaving an unfinished enrollment. A rollover never
  // deletes, the token existed before.
  protected readonly canDelete = computed(
    () => !this.enrollment()?.rollover && this.authService.actionAllowed("delete")
  );
  // The rule of the rollover button in the token details: the only way to finish a token whose step cannot be resumed.
  protected readonly canRollOver = computed(() => {
    const type = this.enrollment()?.tokenType ?? "";
    return (
      this.authService.actionAllowed("token_rollover") &&
      this.authService.tokenRollover().includes(type) &&
      !!tokenTypes.find((candidate) => candidate.key === type)?.rollover
    );
  });

  constructor() {
    super();
    this.dialogRef.disableClose = true;
    this.dialogRef.backdropClick().subscribe(() => this.attemptClose());
    this.dialogRef.keydownEvents().subscribe((event) => {
      if (event.key === "Escape") {
        this.attemptClose();
      }
    });
    this.dialogRef.afterClosed().subscribe(() => this.tokenService.stopPolling());
  }

  register(step: EnrollmentStep): void {
    this.step.set(step);
    afterNextRender(() => this.focusStep(), { injector: this.injector });
  }

  protected attemptClose(): void {
    if (this.step()?.closable === false) {
      return;
    }
    this.confirmLeave().subscribe();
  }

  /**
   * Asks what leaving means for the token, as far as there is a choice, and closes the dialog on a yes.
   * Close, Escape, backdrop clicks and the links in the header all leave this way.
   *
   * @param link The header link that leaves, if any.
   * @returns Whether the dialog is left. A deleted token's own link is not followed.
   */
  protected readonly confirmLeave = (link?: EnrolledTextLink): Observable<boolean> => {
    const step = this.step();
    if (this.finished()) {
      return (step ? step.confirmClose() : of(true)).pipe(
        tap((confirmed) => {
          if (confirmed) {
            this.flow.close();
          }
        })
      );
    }
    const serial = this.detail()?.serial;
    if (!this.canDelete() || !serial) {
      this.flow.close();
      return of(true);
    }
    return leaveIncompleteEnrollment(
      this.dialogService,
      () => this.flow.deleteToken(this.tokenService.cancelEnrollment(serial)),
      this.flow.stepFinished,
      step?.deleteWarning
    ).pipe(
      map((result) => {
        if (result === "stay") {
          return false;
        }
        if (result === "keep") {
          this.flow.close();
          return true;
        }
        this.flow.finishStep(ENROLLMENT_CANCELLED);
        return link !== "token";
      })
    );
  };

  protected onAction(value: string): void {
    this.step()?.onAction?.(value);
  }

  // A step with an input starts there, any other step at its title, so a screen reader reads the new step.
  private focusStep(): void {
    const host = this.elementRef.nativeElement;
    const input = host.querySelector<HTMLElement>(".pi-dialog-body input:not([disabled])");
    if (input) {
      input.focus();
      return;
    }
    const title = host.querySelector<HTMLElement>(".pi-dialog-header h3");
    if (title) {
      title.tabIndex = -1;
      title.focus();
    }
  }
}
