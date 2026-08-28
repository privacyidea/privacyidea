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
import { provideHttpClient } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { signal } from "@angular/core";
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogState } from "@angular/material/dialog";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { ENROLLMENT_CANCELLED } from "@components/token/token-enrollment/token-enrollment.constants";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { TokenService } from "@services/token/token.service";
import { MockContentService, MockTokenService } from "@testing/mock-services";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { of, throwError } from "rxjs";
import {
  TokenEnrollmentFirstStepDialogComponent,
  TokenEnrollmentFirstStepDialogData
} from "./token-enrollment-first-step-dialog.component";

describe("TokenEnrollmentFirstStepDialogComponent", () => {
  let component: TokenEnrollmentFirstStepDialogComponent;
  let fixture: ComponentFixture<TokenEnrollmentFirstStepDialogComponent>;
  let tokenService: MockTokenService;
  let dialogService: MockDialogService;
  let dialogRefMock: jest.Mocked<MatDialogRef<TokenEnrollmentFirstStepDialogComponent>>;

  const enrollmentResponse = {
    detail: {
      rollout_state: "clientwait",
      serial: "PIPU0001",
      pushurl: {
        description: "Push URL",
        img: "push.png",
        value: "https://example.com/push",
        value_b32: "B32VALUE"
      }
    }
  } as unknown as EnrollmentResponse;

  const setup = async (data: Partial<TokenEnrollmentFirstStepDialogData> = {}) => {
    TestBed.resetTestingModule();
    dialogRefMock = {
      close: jest.fn(),
      getState: jest.fn().mockReturnValue(MatDialogState.OPEN)
    } as unknown as jest.Mocked<MatDialogRef<TokenEnrollmentFirstStepDialogComponent>>;

    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: { enrollmentResponse, ...data } },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        { provide: DialogService, useClass: MockDialogService }
      ],
      imports: [TokenEnrollmentFirstStepDialogComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentFirstStepDialogComponent);
    component = fixture.componentInstance;
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    fixture.detectChanges();
  };

  const footerButtons = (): HTMLButtonElement[] =>
    Array.from(fixture.nativeElement.querySelectorAll(".pi-dialog-footer button"));

  const buttonLabels = (): string[] => footerButtons().map((button) => button.textContent?.trim() ?? "");

  const clickButton = (label: string) => {
    const button = footerButtons().find((candidate) => candidate.textContent?.trim() === label);
    expect(button).toBeTruthy();
    button!.click();
    fixture.detectChanges();
  };

  it("should create", async () => {
    await setup();
    expect(component).toBeTruthy();
  });

  describe("button visibility", () => {
    it("shows only the close button when the caller offers nothing else", async () => {
      await setup();
      expect(buttonLabels()).toEqual(["Close"]);
    });

    it("shows the cancel button when the caller allows cancelling", async () => {
      await setup({ showCancelButton: true });
      expect(buttonLabels()).toEqual(["Close", "Cancel"]);
    });

    it("hides the close button when the caller replaces it with cancel", async () => {
      await setup({ showCancelButton: true, showCloseButton: false });
      expect(buttonLabels()).toEqual(["Cancel"]);
    });

    it("offers retry only once an attempt has failed", async () => {
      const registrationFailed = signal(false);
      await setup({ showCancelButton: true, showCloseButton: false, registrationFailed, onRetry: jest.fn() });
      expect(buttonLabels()).toEqual(["Cancel"]);

      registrationFailed.set(true);
      fixture.detectChanges();
      expect(buttonLabels()).toEqual(["Cancel", "Retry"]);
    });

    it("does not offer retry without a retry handler", async () => {
      await setup({ showCancelButton: true, registrationFailed: signal(true) });
      expect(buttonLabels()).not.toContain("Retry");
    });
  });

  describe("cancelling the enrollment", () => {
    it("deletes the incomplete token and reports the cancellation", async () => {
      await setup({ showCancelButton: true });

      clickButton("Cancel");

      expect(tokenService.cancelEnrollment).toHaveBeenCalledWith("PIPU0001");
      expect(dialogRefMock.close).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
    });

    it("keeps the dialog open when the deletion fails", async () => {
      await setup({ showCancelButton: true });
      tokenService.cancelEnrollment.mockReturnValue(throwError(() => new Error("denied")));

      clickButton("Cancel");

      expect(dialogRefMock.close).not.toHaveBeenCalled();
    });

    it("asks for confirmation first when the caller provides a message", async () => {
      await setup({ showCancelButton: true, cancelConfirmationMessage: "Scanned codes stop working." });
      const confirmationRef = new MockMatDialogRef();
      confirmationRef.afterClosed.mockReturnValue(of(true));
      dialogService.openDialog.mockReturnValue(confirmationRef);

      clickButton("Cancel");

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({ message: "Scanned codes stop working." })
        })
      );
      expect(tokenService.cancelEnrollment).toHaveBeenCalledWith("PIPU0001");
      expect(dialogRefMock.close).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
    });

    it("keeps the token when the confirmation is declined", async () => {
      await setup({ showCancelButton: true, cancelConfirmationMessage: "Scanned codes stop working." });
      const confirmationRef = new MockMatDialogRef();
      confirmationRef.afterClosed.mockReturnValue(of(false));
      dialogService.openDialog.mockReturnValue(confirmationRef);

      clickButton("Cancel");

      expect(tokenService.cancelEnrollment).not.toHaveBeenCalled();
      expect(dialogRefMock.close).not.toHaveBeenCalled();
    });

    it("deletes the token even when the rollout finished while the confirmation was open", async () => {
      await setup({ showCancelButton: true, cancelConfirmationMessage: "Scanned codes stop working." });
      const confirmationRef = new MockMatDialogRef();
      confirmationRef.afterClosed.mockReturnValue(of(true));
      dialogService.openDialog.mockReturnValue(confirmationRef);
      dialogRefMock.getState.mockReturnValue(MatDialogState.CLOSED);

      clickButton("Cancel");

      expect(tokenService.cancelEnrollment).toHaveBeenCalledWith("PIPU0001");
    });
  });

  it("delegates retry to the caller", async () => {
    const onRetry = jest.fn();
    await setup({ registrationFailed: signal(true), onRetry });

    clickButton("Retry");

    expect(onRetry).toHaveBeenCalled();
    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });
});
