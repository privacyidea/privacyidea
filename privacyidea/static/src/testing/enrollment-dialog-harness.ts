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
import { Provider } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { EnrollmentFlow, EnrollmentFlowOptions } from "@components/token/token-enrollment/enrollment-flow";
import { EnrollmentStep } from "@components/token/token-enrollment/enrollment-step";
import { TokenEnrollmentDialogComponent } from "@components/token/token-enrollment/token-enrollment-dialog/token-enrollment-dialog.component";
import { TokenEnrollmentLastStepDialogComponent } from "@components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
import { DialogService } from "@services/dialog/dialog.service";
import { EnrollTokenArguments, TokenEnrollmentDialogData } from "@services/token/token.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";

/**
 * Runs an enrollment flow with the real enrollment dialog in a fixture. Add `providers` to the testing module,
 * which also needs a MockDialogService, then call open().
 */
export class EnrollmentDialogHarness {
  flow!: EnrollmentFlow;
  dialogRef = new MockMatDialogRef<unknown>();
  fixture!: ComponentFixture<TokenEnrollmentDialogComponent>;

  readonly providers: Provider[] = [
    { provide: MAT_DIALOG_DATA, useFactory: () => ({ flow: this.flow }) },
    { provide: MatDialogRef, useFactory: () => this.dialogRef }
  ];

  /**
   * Starts an enrollment with the given response and shows the dialog for it.
   *
   * @param response The response that decides the first step.
   * @param data Overrides of the enrollment data.
   * @param options Overrides of the flow options.
   */
  open(
    response: EnrollmentResponse,
    data: Partial<TokenEnrollmentDialogData> = {},
    options: Partial<EnrollmentFlowOptions> = {}
  ): void {
    const dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    dialogService.openDialog.mockReturnValueOnce(this.dialogRef);
    this.flow = TestBed.runInInjectionContext(
      () => new EnrollmentFlow({ successStep: () => TokenEnrollmentLastStepDialogComponent, ...options })
    );
    this.flow.start({
      response,
      enrollParameters: { data: {} } as EnrollTokenArguments,
      tokenType: "hotp",
      ...data
    });
    this.flow.continue(response);
    this.fixture = TestBed.createComponent(TokenEnrollmentDialogComponent);
    this.fixture.detectChanges();
  }

  step<T extends EnrollmentStep>(): T {
    return this.fixture.componentInstance["step"]() as T;
  }

  get element(): HTMLElement {
    return this.fixture.nativeElement;
  }

  footerButtons(): HTMLButtonElement[] {
    return Array.from(this.element.querySelectorAll(".pi-dialog-footer button"));
  }

  footerButton(label: string): HTMLButtonElement | undefined {
    return this.footerButtons().find((button) => button.textContent?.trim() === label);
  }
}
